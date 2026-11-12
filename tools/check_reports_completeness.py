"""Report-completeness health for the PCM daily series (issue #88).

Two different healths live in this repository and they must not be confused:

* **test health** — does the code pass its suite? `tests.yml` answers this.
* **report-completeness health** — did the daily record actually get written? This answers that.

The distinction matters because the failure they detect is different in kind. A green suite says nothing
about a report that is missing, and a complete series says nothing about a broken kernel. Before this
check, the only signal about the daily series was the absence of a complaint.

The rule the issue asks for has three parts, and the awkward middle one is the reason this is a script
rather than a grep:

1. A **missing past date** is a finding. Yesterday's report should exist.
2. A **same-day placeholder is legitimate** — the morning thoughts job creates the report as its public
   bearer hours before the watch writes into it, so a placeholder on today's date is the design working,
   not a fault.
3. A **placeholder that outlives the watch's expected completion window is stale**, whether or not
   anybody was looking at the moment it went stale. Detection may not depend on the check running on the
   same morning: a three-day outage followed by one check must find all three days, not just the last.

Waivers exist because a gap can be known and accepted. A waived date is still reported — it is evidence,
not an exemption from the record — it simply does not fail the run.

Usage::

    python3 tools/check_reports_completeness.py --reports-dir docs/reports --fail-on-gaps
    python3 tools/check_reports_completeness.py --json --today 2026-11-12 --start 2026-09-14
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

#: The canonical marker the morning carrier writes and the watch replaces. Kept for documentation
#: and for readers of the JSON output; the check itself keys on structure, because carriers phrase the
#: pending note in at least three different ways across the series.
PLACEHOLDER_MARKER = "Placeholder, not a scan"

#: A written watch carries structure. Two shapes exist in the series — numbered subsections
#: (`### 1. Repository changes and health`, the November form) and a retrospective blockquote with
#: prose (the form used when a gap is reconstructed) — so the test is "did anything structured get
#: written", not "does it match one template". Reports that merely *quote* the marker while writing
#: about a gap have structure too, which is why the marker alone cannot be the signal.
STRUCTURE_HINTS = ("###", ">", "Retrospective", "retrospective")

#: The watch runs at 10:00 local; by noon a placeholder that is still there is not "about to be
#: replaced", it is a report the watch did not write.
DEFAULT_COMPLETION_HOUR = 12

REPORT_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")

#: Statuses that fail the run. A waived date keeps its finding but loses this property.
FAILING = frozenset({"missing", "stale_placeholder"})


@dataclass(frozen=True)
class Finding:
    """One date's verdict, with the evidence a reader needs to act on it."""

    day: date
    status: str
    detail: str
    path: str = ""

    @property
    def failing(self) -> bool:
        return self.status in FAILING


def report_dates(reports_dir: Path) -> dict[date, Path]:
    """Map every dated report in the directory. `README.md` and anything undated is ignored."""
    found: dict[date, Path] = {}
    for path in sorted(reports_dir.glob("*.md")):
        match = REPORT_NAME.match(path.name)
        if not match:
            continue
        found[date.fromisoformat(match.group(1))] = path
    return found


def daily_watch_section(text: str) -> str:
    """The body of the `## Daily watch` section, up to the next level-two heading."""
    start = text.find("## Daily watch")
    if start < 0:
        return ""
    remainder = text[start + len("## Daily watch"):]
    end = remainder.find("\n## ")
    return remainder if end < 0 else remainder[:end]


def has_written_watch(text: str) -> bool:
    """True when the watch — or a labelled reconstruction of it — wrote something into the report.

    The test is inverted deliberately: it looks for *structure*, not for the carrier's wording.
    Carriers come in several phrasings ("Placeholder, not a scan", "*[PENDING — the 10:00 watch
    appends its sections here]*", "watch sections pending"), and enumerating them would break on the
    next edit. What no carrier has is structure: a written watch has numbered subsections, and a
    labelled reconstruction has a blockquote. Those are what this looks for.
    """
    if re.search(r"^## 1\. ", text, re.MULTILINE):
        # The September-era series is titled "# PCM Daily Watch" and numbers sections at level two.
        return True
    body = daily_watch_section(text)
    if not body.strip():
        return False
    return any(hint in body for hint in STRUCTURE_HINTS)


def carries_placeholder(path: Path) -> bool:
    """True when the report exists but the watch never wrote into it."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return not has_written_watch(text)


def load_waivers(path: Path | None) -> dict[date, str]:
    """Read a waiver file: JSON object, or `YYYY-MM-DD reason` lines. Missing file means no waivers."""
    if path is None or not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(text or "{}")
        return {date.fromisoformat(day): str(reason) for day, reason in payload.items()}
    waivers: dict[date, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        day, _, reason = line.partition(" ")
        waivers[date.fromisoformat(day)] = reason.strip() or "waived"
    return waivers


def check_reports(
    reports_dir: Path,
    *,
    today: date,
    start: date | None = None,
    end: date | None = None,
    now_hour: int | None = None,
    completion_hour: int = DEFAULT_COMPLETION_HOUR,
    waivers: dict[date, str] | None = None,
    judge_today: bool = True,
) -> dict:
    """Verdict for every expected date in the series.

    Expected dates run from ``start`` (default: the earliest report present) to yesterday. Today is
    included only to judge a placeholder against the completion window, never as a missing report —
    and ``judge_today=False`` drops even that, which is what a historical audit of the series wants.
    """
    reports = report_dates(reports_dir)
    first = start or (min(reports) if reports else today)
    last_expected = min(end, today - timedelta(days=1)) if end else today - timedelta(days=1)
    # The series is dated in local time (EEST), so the completion window is judged on the
    # wall clock that produced it, not on UTC.
    hour = datetime.now().hour if now_hour is None else now_hour  # noqa: DTZ005
    waivers = waivers or {}

    findings: list[Finding] = []
    day = first
    while day <= last_expected:
        path = reports.get(day)
        if path is None:
            findings.append(Finding(day, "missing", "no report file for this date"))
        elif carries_placeholder(path):
            findings.append(Finding(
                day, "stale_placeholder",
                "the morning carrier's placeholder survived the watch's completion window",
                path.name,
            ))
        else:
            findings.append(Finding(day, "complete", "", path.name))
        day += timedelta(days=1)

    today_report = reports.get(today) if judge_today else None
    if today_report is not None and carries_placeholder(today_report):
        status = "same_day_carrier" if hour < completion_hour else "stale_placeholder"
        detail = (
            f"carrier placeholder on today's date, before the {completion_hour}:00 completion window"
            if status == "same_day_carrier"
            else f"carrier placeholder on today's date after the {completion_hour}:00 completion window"
        )
        findings.append(Finding(today, status, detail, today_report.name))

    applied = []
    for finding in findings:
        reason = waivers.get(finding.day)
        if reason is None:
            applied.append(finding)
        else:
            applied.append(Finding(finding.day, f"waived ({finding.status})", reason, finding.path))

    counts: dict[str, int] = {}
    for finding in applied:
        key = finding.status.split(" (")[0]
        counts[key] = counts.get(key, 0) + 1

    return {
        "reports_dir": str(reports_dir),
        "today": today.isoformat(),
        "range": {"start": first.isoformat(), "end": last_expected.isoformat()},
        "completion_hour": completion_hour,
        "checked": len(applied),
        "counts": counts,
        "findings": [
            {"date": f.day.isoformat(), "status": f.status, "detail": f.detail, "file": f.path}
            for f in applied
            if f.status != "complete"
        ],
        "failing": [f.day.isoformat() for f in applied if f.failing],
        "healthy": not any(f.failing for f in applied),
    }


def render(report: dict) -> str:
    """Human-readable summary: the counts first, then only the dates that need attention."""
    lines = [
        f"reports: {report['reports_dir']}",
        f"range:   {report['range']['start']} .. {report['range']['end']}  (checked {report['checked']} dates)",
        f"today:   {report['today']}  (placeholder window closes {report['completion_hour']}:00)",
        "",
    ]
    lines.append("counts: " + ", ".join(f"{k} {v}" for k, v in sorted(report["counts"].items())))
    if report["findings"]:
        lines.append("")
        for finding in report["findings"]:
            lines.append(f"  {finding['date']}  {finding['status']:<30} {finding['detail']}")
    lines.append("")
    lines.append("healthy" if report["healthy"] else "NOT healthy: " + ", ".join(report["failing"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check PCM daily-report completeness (issue #88).")
    parser.add_argument("--reports-dir", default="docs/reports")
    parser.add_argument("--today", help="ISO date to treat as today (default: system date)")
    parser.add_argument("--start", help="first expected date (default: earliest report present)")
    parser.add_argument("--end", help="last expected date (default: yesterday)")
    parser.add_argument("--now-hour", type=int, help="hour to use for the completion window (testing)")
    parser.add_argument("--completion-hour", type=int, default=DEFAULT_COMPLETION_HOUR)
    parser.add_argument("--waivers", help="JSON object or 'YYYY-MM-DD reason' lines")
    parser.add_argument("--json", action="store_true", help="print the machine-readable report")
    parser.add_argument(
        "--fail-on-gaps",
        action="store_true",
        help="exit 1 on any unwaived missing report or stale placeholder (CI mode)",
    )
    args = parser.parse_args(argv)

    today = date.fromisoformat(args.today) if args.today else date.today()  # noqa: DTZ011
    report = check_reports(
        Path(args.reports_dir),
        today=today,
        start=date.fromisoformat(args.start) if args.start else None,
        end=date.fromisoformat(args.end) if args.end else None,
        now_hour=args.now_hour,
        completion_hour=args.completion_hour,
        waivers=load_waivers(Path(args.waivers) if args.waivers else None),
    )
    print(json.dumps(report, indent=2) if args.json else render(report))
    return 1 if (args.fail_on_gaps and not report["healthy"]) else 0


if __name__ == "__main__":
    sys.exit(main())
