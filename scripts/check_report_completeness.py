#!/usr/bin/env python3
"""Date-aware completeness check for the PCM daily reports (#88).

CI passing has never meant the report chain is complete: the Tests workflow checks code, and a day
whose watch never ran leaves no code failing anywhere. This check is deliberately separate, and it
answers one question per date — *is there a report that was actually produced?*

Rules
-----
1. Every date between the first report and today has a file.
2. A **same-day** carrier is legitimate: the pcm-daily-thoughts job writes a placeholder at ~08:00,
   and the watch fills it at ~10:00. So a placeholder is only a defect if the date is not today, or
   if today's watch deadline has already passed.
3. The check never requires being run on the same morning: it reads dates, not "now" relative to
   when CI last ran. `--today` is explicit, so a scheduled run and a manual run agree.
4. A date listed in ``docs/reports/waivers.json`` with a reason is reported as waived, not failed —
   for gaps that cannot be reconstructed from surviving evidence.

Exit codes: 0 complete (or only waivers), 1 a real gap, 2 cannot read the reports directory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

#: The watch writes its sections at 10:00 EEST. A carrier still holding a placeholder after 12:00
#: on its own day is unresolved, not "the watch may still arrive".
DEFAULT_WATCH_DEADLINE = dt.time(12, 0)

#: Text only the morning carrier writes. A report that still contains it at the top has not been
#: filled by the watch.
PLACEHOLDER_MARKERS = (
    "Placeholder, not a scan",
    "Set by the daily watch's run when it arrives",
)

#: Evidence that the date was resolved, whatever else the file contains. A report may quote the
#: placeholder it replaced - which is what 2026-10-08 now does, to keep the record - so the test is
#: "was this date resolved?", not "does the string appear?".
RESOLVED_MARKERS = (
    "### 1. Repository changes and health",   # the watch filled its own sections
    "Retrospective reconstruction",           # restored later from a verifiable source
    "Retrospective record",                   # a documented gap with no source to restore
)

REPORT_GLOB = "20*.md"


def report_date(path: Path) -> dt.date | None:
    try:
        return dt.date.fromisoformat(path.stem)
    except ValueError:
        return None


def is_placeholder(text: str) -> bool:
    """True only when the date is still unresolved.

    Three states look alike from a distance: a filled report, a same-day carrier, and a stale
    placeholder. A file that quotes the placeholder it replaced is resolved; a file that carries one
    and nothing else is not.
    """
    if any(marker in text for marker in RESOLVED_MARKERS):
        return False
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


def load_waivers(path: Path) -> dict[str, str]:
    """Return ``{date: reason}``. A waiver without a reason is a hidden failure, so it is rejected."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("waived", {})
    waivers: dict[str, str] = {}
    for day, record in entries.items():
        reason = (record or {}).get("reason", "").strip()
        if not reason:
            raise ValueError(f"waiver for {day} has no reason; a silent waiver is a hidden failure")
        waivers[day] = reason
    return waivers


def check(
    reports_dir: Path,
    *,
    today: dt.date,
    watch_deadline: dt.time = DEFAULT_WATCH_DEADLINE,
    now: dt.time | None = None,
    waivers: dict[str, str] | None = None,
) -> list[str]:
    """Return human-readable problems; an empty list means the chain is complete."""
    waivers = waivers or {}
    now = now or watch_deadline  # a caller that does not say the time is treated as "after the watch"
    problems: list[str] = []

    dated: dict[dt.date, Path] = {}
    for path in sorted(reports_dir.glob(REPORT_GLOB)):
        day_of_file = report_date(path)
        if day_of_file is not None:
            dated[day_of_file] = path
    if not dated:
        return [f"no dated reports found in {reports_dir}"]

    first = min(dated)
    day = first
    while day <= today:
        key = day.isoformat()
        path = dated.get(day)

        if key in waivers:
            day += dt.timedelta(days=1)
            continue

        if path is None:
            # Today's report may legitimately not exist yet: the thoughts carrier writes at 08:00.
            if day != today:
                problems.append(f"{key}: no report file")
            day += dt.timedelta(days=1)
            continue

        if is_placeholder(path.read_text(encoding="utf-8")):
            if day != today:
                problems.append(
                    f"{key}: still a morning placeholder (watch never filled it)"
                )
            elif now > watch_deadline:
                problems.append(
                    f"{key}: placeholder still present after the {watch_deadline.strftime('%H:%M')} "
                    "watch deadline"
                )

        day += dt.timedelta(days=1)

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that every PCM daily report exists and is filled.")
    parser.add_argument("--reports-dir", default="docs/reports", type=Path)
    parser.add_argument("--today", default=None, help="YYYY-MM-DD; defaults to today (UTC)")
    parser.add_argument("--now", default=None, help="HH:MM; defaults to the watch deadline")
    parser.add_argument("--waivers", default=None, type=Path,
                        help="defaults to <reports-dir>/waivers.json")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    now = dt.time.fromisoformat(args.now) if args.now else None
    waivers_path = args.waivers or (args.reports_dir / "waivers.json")

    try:
        waivers = load_waivers(waivers_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"cannot read waivers: {exc}", file=sys.stderr)
        return 2

    if not args.reports_dir.is_dir():
        print(f"no reports directory: {args.reports_dir}", file=sys.stderr)
        return 2

    problems = check(args.reports_dir, today=today, now=now, waivers=waivers)
    for day, reason in sorted(waivers.items()):
        if args.verbose:
            print(f"waived {day}: {reason}")
    if problems:
        print(f"{len(problems)} report gap(s):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"report chain complete through {today.isoformat()} ({len(waivers)} waiver(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
