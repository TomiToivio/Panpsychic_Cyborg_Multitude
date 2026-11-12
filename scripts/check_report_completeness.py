#!/usr/bin/env python3
"""Report-completeness check for the PCM daily reports (issue #88).

Code health and report health are different questions. A green *Tests* workflow proves the code runs;
it says nothing about whether yesterday's daily watch produced a report, and on 2026-10-08 the two
diverged for five weeks: the placeholder in `docs/reports/2026-10-08.md` was visible in every CI run
and nothing looked.

This check answers only the second question, and it answers it date by date:

* **complete** — the date has a report whose `## Daily watch` section is real content;
* **gap** — the date has a report that says, in a machine-readable line, that no watch ran
  (`Report status: gap`). A recorded absence is resolved; a missing file is not;
* **placeholder** — the report exists but still carries the morning carrier's "waiting for the watch"
  text. Legitimate on the day itself until the cutoff hour; a violation afterwards;
* **missing** — no report for a past date. Always a violation unless explicitly waived.

The cutoff is what makes the check honest rather than eager: the watch runs mid-morning, so a same-day
placeholder is not a defect at 08:00 and is a defect at 18:00. Dates listed in `waivers.json` are
reported but not failed — a waiver is a decision someone wrote down, not a silent skip.

Usage:
    python scripts/check_report_completeness.py
    python scripts/check_report_completeness.py --as-of 2026-11-12 --json
    python scripts/check_report_completeness.py --since 2026-09-14 --cutoff-hour 12

Exit codes: 0 all resolved, 1 violations found, 2 bad invocation.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

DEFAULT_FIRST_REPORT = date(2026, 9, 14)
DEFAULT_CUTOFF_HOUR = 12

#: The morning carrier's own words when it creates the file before the watch runs. Kept narrow on
#: purpose: a report that *discusses* an old placeholder must not be classified as one.
PLACEHOLDER_MARKERS = (
    "Placeholder, not a scan.",
    "watch sections pending",
    "Set by the daily watch's run when it arrives.",
)

#: A backfilled or reconstructed watch section is real content, whatever it says about its own limits.
RESOLUTION_MARKERS = ("retrospective reconstruction", "reconstructed 2026-", "gap report")

GAP_MARKER = "Report status: gap"

COMPLETE = "complete"
GAP = "gap"
PLACEHOLDER = "placeholder"
MISSING = "missing"


@dataclass
class ReportState:
    day: date
    status: str
    detail: str = ""
    waived: bool = False

    @property
    def violation(self) -> bool:
        if self.waived:
            return False
        return self.status in {PLACEHOLDER, MISSING}

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.day.isoformat(),
            "status": self.status,
            "detail": self.detail,
            "waived": self.waived,
            "violation": self.violation,
        }


#: A carrier placeholder is short. A real watch section quotes commit messages that may contain the
#: same words ("carrier report, watch sections pending"), so length is the discriminator that keeps a
#: complete report from being flagged by its own prose.
PLACEHOLDER_MAX_CHARS = 900


def watch_section(text: str) -> str:
    """The `## Daily watch` block **including its heading**, or empty when the file has no such heading."""
    marker = "\n## Daily watch"
    index = text.find(marker)
    if index < 0:
        if text.startswith("## Daily watch"):
            index = 0
        else:
            return ""
    rest = text[index + 1 :] if index else text
    next_heading = rest.find("\n## ", 1)
    return rest[: next_heading if next_heading >= 0 else len(rest)]


def _uses_watch_title(text: str) -> bool:
    """September's reports are titled `PCM Daily Watch` and number their sections directly."""
    first = text.lstrip().split("\n", 1)[0]
    return first.startswith("# PCM Daily Watch") or "PCM Daily Watch —" in first


def classify_text(text: str) -> tuple[str, str]:
    """Classify one report body. Returns (status, detail)."""
    if GAP_MARKER.casefold() in text.casefold():
        return (GAP, "recorded gap: no watch ran for this date")
    if _uses_watch_title(text):
        return (COMPLETE, "September watch format")
    body = watch_section(text)
    if not body.strip():
        return (MISSING, "no `## Daily watch` section")
    lowered = body.casefold()
    if "### 1" in lowered or "### 1." in lowered:
        return (COMPLETE, "structured watch sections")
    if any(marker.casefold() in lowered for marker in RESOLUTION_MARKERS):
        return (COMPLETE, "reconstructed or backfilled watch section")
    if len(body) < PLACEHOLDER_MAX_CHARS:
        for marker in PLACEHOLDER_MARKERS:
            if marker.casefold() in lowered:
                return (PLACEHOLDER, "carrier placeholder still in place")
    return (COMPLETE, "")


def load_waivers(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"waivers file is not valid JSON: {path}: {exc}") from exc
    waived = payload.get("waived", payload) if isinstance(payload, dict) else {}
    return {str(key): str(value) for key, value in waived.items()}


def dates_between(first: date, last: date) -> Iterable[date]:
    current = first
    while current <= last:
        yield current
        current += timedelta(days=1)


def check_reports(
    reports_dir: Path,
    *,
    first: date = DEFAULT_FIRST_REPORT,
    as_of: date | None = None,
    now: datetime | None = None,
    cutoff_hour: int = DEFAULT_CUTOFF_HOUR,
    waivers: dict[str, str] | None = None,
) -> list[ReportState]:
    """Check every date from ``first`` to ``as_of`` inclusive (default: today)."""
    today = as_of or (now.date() if now else date.today())
    moment = now or datetime.now()
    waivers = waivers or {}
    states: list[ReportState] = []

    for day in dates_between(first, today):
        key = day.isoformat()
        path = reports_dir / f"{key}.md"
        waived = key in waivers
        detail = waivers.get(key, "")
        if not path.is_file():
            states.append(ReportState(day, MISSING, detail or "no report file", waived))
            continue
        status, reason = classify_text(path.read_text(encoding="utf-8", errors="replace"))
        if status == PLACEHOLDER and day == moment.date() and moment.hour < cutoff_hour:
            # The watch has not run yet today; the carrier's placeholder is the expected state.
            states.append(ReportState(day, PLACEHOLDER, "same-day carrier, before the cutoff", True))
            continue
        states.append(ReportState(day, status, reason or detail, waived))

    return states


def summarise(states: Sequence[ReportState]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for state in states:
        counts[state.status] = counts.get(state.status, 0) + 1
    violations = [state for state in states if state.violation]
    return {
        "schema_version": "pcm.report_completeness/1",
        "dates_checked": len(states),
        "counts": dict(sorted(counts.items())),
        "violations": [state.as_dict() for state in violations],
        "waived": [state.as_dict() for state in states if state.waived],
        "first": states[0].day.isoformat() if states else None,
        "last": states[-1].day.isoformat() if states else None,
    }


def render(states: Sequence[ReportState]) -> str:
    lines = ["PCM daily reports — completeness", ""]
    for state in states:
        flag = "FAIL" if state.violation else ("waived" if state.waived else "ok")
        note = f" — {state.detail}" if state.detail else ""
        lines.append(f"  {state.day.isoformat()}  {state.status:11} {flag:6}{note}")
    report = summarise(states)
    lines += [
        "",
        f"checked {report['dates_checked']} dates {report['first']}..{report['last']}: "
        + ", ".join(f"{name} {count}" for name, count in report["counts"].items()),
        "this is report completeness, not code health: a green test suite says nothing about it",
    ]
    if report["violations"]:
        lines.append(f"{len(report['violations'])} unresolved report gap(s)")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-report-completeness", description=__doc__)
    parser.add_argument(
        "--reports",
        default=str(Path(__file__).resolve().parent.parent / "docs" / "reports"),
        help="report directory (default: docs/reports)",
    )
    parser.add_argument("--since", default=DEFAULT_FIRST_REPORT.isoformat())
    parser.add_argument("--as-of", default=None, help="last date to check (default: today)")
    parser.add_argument("--cutoff-hour", type=int, default=DEFAULT_CUTOFF_HOUR)
    parser.add_argument(
        "--waivers",
        default=None,
        help="JSON mapping date -> reason (default: <reports>/waivers.json when it exists)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(list(argv) if argv is not None else None)

    reports_dir = Path(args.reports)
    if not reports_dir.is_dir():
        print(f"no report directory: {reports_dir}", file=sys.stderr)
        return 2
    first = date.fromisoformat(args.since)
    as_of = date.fromisoformat(args.as_of) if args.as_of else None
    waiver_path = Path(args.waivers) if args.waivers else reports_dir / "waivers.json"
    waivers = load_waivers(waiver_path)

    states = check_reports(
        reports_dir,
        first=first,
        as_of=as_of,
        cutoff_hour=args.cutoff_hour,
        waivers=waivers,
    )
    if args.json:
        print(json.dumps(summarise(states), indent=2, sort_keys=True))
    else:
        print(render(states))
    return 1 if any(state.violation for state in states) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
