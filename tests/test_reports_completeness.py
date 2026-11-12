"""Issue #88 — report completeness is a separate health from test health.

The check exists because a green suite says nothing about whether the daily record was written, and
because the failure it detects is quiet: a report that is missing looks exactly like a day nothing
happened.

The cases below pin the parts that are easy to get wrong and expensive to get wrong:

* a same-day placeholder is the design working (the morning carrier runs hours before the watch), so
  flagging it would train everyone to ignore the check;
* a three-day outage followed by one check must find all three days — detection may not depend on
  running on the same morning as the failure;
* a report that *quotes* the placeholder while discussing the gap is healthy. Two real reports do
  exactly that, and a phrase-matching check would have called them broken;
* a waived date stays in the record. A waiver is evidence of a known gap, not an erasure of it.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import check_reports_completeness as checks

TODAY = date(2026, 11, 12)
START = date(2026, 11, 8)

CARRIER = """# PCM Daily Report — {day}

## Daily watch

**Placeholder, not a scan.** This report is the morning thoughts' public bearer.

## Priorities

Set by the daily watch's run when it arrives.
"""

WRITTEN = """# PCM Daily Report — {day}

## Daily watch

### 1. Repository changes and health [established]

The watch ran.
"""

LEGACY = """# PCM Daily Watch — {day}

## 1. Repo changes and health

Established: the September series numbered its sections at level two.
"""

THOUGHTS_ONLY = """## Daily thoughts — {day} (node reflection)

The morning carrier published the reflection and the watch never wrote.
"""

QUOTING = """# PCM Daily Report — {day}

## Daily watch

### 1. Repository changes and health [established]

The 1 October report still carries the morning placeholder ("Placeholder, not a scan") where the watch
sections should be. This report quotes the marker while carrying a complete watch of its own.
"""


class ReportsFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, day: date, body: str) -> None:
        (self.dir / f"{day.isoformat()}.md").write_text(body.format(day=day.isoformat()), encoding="utf-8")

    def fill_past(self, body: str = WRITTEN) -> None:
        """Write a complete past series, so a test can place one anomaly against a healthy baseline."""
        day = START
        while day < TODAY:
            self.write(day, body)
            day = date.fromordinal(day.toordinal() + 1)

    def check(self, **kwargs) -> dict:
        arguments = {"today": TODAY, "now_hour": 9}
        arguments.update(kwargs)
        return checks.check_reports(self.dir, **arguments)


class CompletedReportsAreHealthy(ReportsFixture):
    def test_a_written_watch_passes(self):
        self.fill_past()
        report = self.check()
        self.assertTrue(report["healthy"])
        self.assertEqual(report["counts"]["complete"], 4)

    def test_the_september_format_counts_as_written(self):
        self.fill_past()
        self.write(START, LEGACY)
        self.assertTrue(self.check()["healthy"])

    def test_a_report_quoting_the_marker_while_carrying_a_watch_is_not_stale(self):
        """The regression that matters: two real reports discuss the gap in prose."""
        self.fill_past()
        self.write(START, QUOTING)
        self.assertTrue(self.check(start=START)["healthy"])


class SameDayPlaceholdersAreLegitimate(ReportsFixture):
    def test_today_before_the_completion_window_is_a_carrier_not_a_fault(self):
        self.fill_past()
        self.write(TODAY, CARRIER)
        report = self.check(now_hour=9)
        self.assertTrue(report["healthy"])
        self.assertEqual(report["counts"]["same_day_carrier"], 1)

    def test_today_after_the_completion_window_is_stale(self):
        self.fill_past()
        self.write(TODAY, CARRIER)
        report = self.check(now_hour=13)
        self.assertFalse(report["healthy"])
        self.assertEqual(report["failing"], [TODAY.isoformat()])


class PastGapsAreFindings(ReportsFixture):
    def test_a_past_placeholder_is_stale(self):
        self.write(START, CARRIER)
        report = self.check(start=START)
        self.assertEqual(report["findings"][0]["status"], "stale_placeholder")

    def test_a_thoughts_only_report_is_stale_because_the_watch_never_wrote(self):
        self.write(START, THOUGHTS_ONLY)
        self.assertFalse(self.check(start=START)["healthy"])

    def test_a_missing_date_is_a_finding(self):
        report = self.check(start=START)   # empty directory
        self.assertEqual(report["counts"]["missing"], 4)
        self.assertEqual(len(report["failing"]), 4)

    def test_a_multi_day_outage_is_reported_day_by_day(self):
        """The check must not depend on running on the morning the failure happened."""
        self.write(START, WRITTEN)
        report = self.check(start=START)
        self.assertEqual(
            report["failing"],
            ["2026-11-09", "2026-11-10", "2026-11-11"],
            "every missing day is named, not just the most recent",
        )


class WaiversKeepTheRecord(ReportsFixture):
    def test_a_waived_gap_does_not_fail_the_run_but_stays_visible(self):
        self.fill_past()
        (self.dir / "2026-11-09.md").unlink()
        report = self.check(start=START, waivers={date(2026, 11, 9): "watch job was down for maintenance"})
        self.assertTrue(report["healthy"])
        waived = [f for f in report["findings"] if f["status"].startswith("waived")]
        self.assertEqual(len(waived), 1)
        self.assertIn("maintenance", waived[0]["detail"])

    def test_waivers_load_from_json_and_from_lines(self):
        json_path = self.dir / "waivers.json"
        json_path.write_text('{"2026-11-09": "planned outage"}', encoding="utf-8")
        self.assertEqual(list(checks.load_waivers(json_path)), [date(2026, 11, 9)])

        text_path = self.dir / "waivers.txt"
        text_path.write_text("# comment\n2026-11-10 unrecorded by design\n", encoding="utf-8")
        self.assertEqual(checks.load_waivers(text_path)[date(2026, 11, 10)], "unrecorded by design")

    def test_a_missing_waiver_file_is_not_an_error(self):
        self.assertEqual(checks.load_waivers(self.dir / "absent.txt"), {})


class Boundaries(ReportsFixture):
    def test_future_dates_are_not_expected(self):
        self.fill_past()
        self.write(date(2026, 11, 20), WRITTEN)
        report = self.check(start=START)
        self.assertTrue(report["healthy"])
        self.assertEqual(report["range"]["end"], "2026-11-11")

    def test_the_exit_code_reflects_the_failure_only_in_ci_mode(self):
        self.write(START, CARRIER)
        argv = ["--reports-dir", str(self.dir), "--today", TODAY.isoformat(),
                "--start", START.isoformat(), "--now-hour", "9"]
        self.assertEqual(checks.main(argv), 0, "report-only mode never fails the shell")
        self.assertEqual(checks.main(argv + ["--fail-on-gaps"]), 1)


class TheRepositoryItselfIsComplete(unittest.TestCase):
    """The series must be healthy before the gate can be trusted to mean anything.

    This is the integration guard: if a future report is published with the carrier placeholder and
    never written, or a date is skipped, this test is where it surfaces.
    """

    def test_every_date_in_the_series_is_complete(self):
        root = Path(__file__).resolve().parent.parent
        reports = checks.report_dates(root / "docs" / "reports")
        self.assertTrue(reports, "no dated reports found")
        newest = max(reports)
        report = checks.check_reports(
            root / "docs" / "reports",
            # Judge the series as of its own last entry, and judge only dates *before* it: the newest
            # report may legitimately still be the morning carrier, and that is the runtime job's
            # business rather than a unit test's.
            today=newest,
            end=newest - timedelta(days=1),
            start=min(reports),
            now_hour=23,
            judge_today=False,
        )
        self.assertTrue(report["healthy"], "unhealthy dates: " + ", ".join(report["failing"]))


if __name__ == "__main__":
    unittest.main()
