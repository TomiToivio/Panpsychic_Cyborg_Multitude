"""#88: a report gap must fail loudly, and a same-day carrier must not.

The failure this guards against is not a broken test — it is a broken *chain*: a day where the watch
never ran, no commit exists, every workflow is green, and nobody notices for seven weeks. The check
therefore has to distinguish three states that look similar from the outside:

* a completed report;
* a legitimate same-day carrier, written at 08:00 before the 10:00 watch;
* a placeholder that survived its watch.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_report_completeness as check  # noqa: E402

PLACEHOLDER = """# PCM Daily Report — {day}

## Daily watch

**Placeholder, not a scan.** This report is the morning thoughts' public bearer.

## Priorities

Set by the daily watch's run when it arrives.
"""

FILLED = """# PCM Daily Report — {day}

## Daily watch

### 1. Repository changes and health [established]

The chain holds.
"""


class CompletenessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, day: str, template: str = FILLED):
        (self.dir / f"{day}.md").write_text(template.format(day=day), encoding="utf-8")

    def test_a_complete_chain_reports_nothing(self):
        for day in ("2026-10-08", "2026-10-09", "2026-10-10"):
            self.write(day)
        problems = check.check(self.dir, today=dt.date(2026, 10, 10))
        self.assertEqual(problems, [])

    def test_a_same_day_carrier_is_legitimate_before_the_watch_deadline(self):
        self.write("2026-10-08", PLACEHOLDER)
        problems = check.check(
            self.dir, today=dt.date(2026, 10, 8), now=dt.time(9, 30)
        )
        self.assertEqual(problems, [], "08:00 carrier must not fail before the 10:00 watch")

    def test_a_same_day_placeholder_fails_after_the_watch_deadline(self):
        self.write("2026-10-08", PLACEHOLDER)
        problems = check.check(
            self.dir, today=dt.date(2026, 10, 8), now=dt.time(12, 30)
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("watch deadline", problems[0])

    def test_a_stale_placeholder_fails_on_a_later_day(self):
        self.write("2026-10-08", PLACEHOLDER)
        self.write("2026-10-09")
        problems = check.check(self.dir, today=dt.date(2026, 10, 9))
        self.assertEqual(len(problems), 1)
        self.assertIn("2026-10-08", problems[0])
        self.assertIn("placeholder", problems[0])

    def test_a_missing_past_date_fails(self):
        self.write("2026-10-08")
        self.write("2026-10-10")
        problems = check.check(self.dir, today=dt.date(2026, 10, 10))
        self.assertEqual(len(problems), 1)
        self.assertIn("2026-10-09: no report file", problems[0])

    def test_today_may_be_missing_because_the_carrier_has_not_run_yet(self):
        self.write("2026-10-08")
        problems = check.check(self.dir, today=dt.date(2026, 10, 9))
        self.assertEqual(problems, [])

    def test_a_waived_date_passes_and_keeps_its_reason(self):
        self.write("2026-10-08", PLACEHOLDER)
        self.write("2026-10-09")
        waivers = {"2026-10-08": "no surviving run record"}
        problems = check.check(self.dir, today=dt.date(2026, 10, 9), waivers=waivers)
        self.assertEqual(problems, [])

    def test_a_waiver_without_a_reason_is_rejected(self):
        path = self.dir / "waivers.json"
        path.write_text(json.dumps({"waived": {"2026-10-08": {}}}), encoding="utf-8")
        with self.assertRaises(ValueError):
            check.load_waivers(path)

    def test_a_waiver_is_read_from_the_reports_directory(self):
        path = self.dir / "waivers.json"
        path.write_text(
            json.dumps({"waived": {"2026-10-08": {"reason": "gap with no source"}}}),
            encoding="utf-8",
        )
        self.assertEqual(check.load_waivers(path), {"2026-10-08": "gap with no source"})

    def test_an_empty_directory_is_an_error_not_a_silent_pass(self):
        problems = check.check(self.dir, today=dt.date(2026, 10, 8))
        self.assertEqual(len(problems), 1)
        self.assertIn("no dated reports", problems[0])

    def test_the_check_reads_dates_and_does_not_depend_on_when_it_runs(self):
        """Run at 23:59 on a later day, a filled report still passes: no 'same morning' requirement."""
        self.write("2026-10-08")
        self.write("2026-10-09")
        problems = check.check(
            self.dir, today=dt.date(2026, 10, 9), now=dt.time(23, 59)
        )
        self.assertEqual(problems, [])


class RepositoryTests(unittest.TestCase):
    """The real repository, not a fixture: the chain this ships against must be complete."""

    def test_the_shipped_report_chain_is_complete(self):
        reports = ROOT / "docs" / "reports"
        waivers = check.load_waivers(reports / "waivers.json")
        problems = check.check(reports, today=dt.date(2026, 11, 12), waivers=waivers)
        self.assertEqual(problems, [], f"report chain has gaps: {problems}")

    def test_the_backfilled_dates_are_no_longer_placeholders(self):
        reports = ROOT / "docs" / "reports"
        for day in ("2026-10-08", "2026-10-16", "2026-10-17", "2026-10-18"):
            text = (reports / f"{day}.md").read_text(encoding="utf-8")
            self.assertFalse(
                check.is_placeholder(text), f"{day} still carries an unresolved placeholder"
            )

    def test_backfilled_reports_say_they_are_retrospective(self):
        reports = ROOT / "docs" / "reports"
        for day in ("2026-10-08", "2026-10-16", "2026-10-17", "2026-10-18"):
            text = (reports / f"{day}.md").read_text(encoding="utf-8")
            self.assertIn("Retrospective", text, f"{day} must label itself a reconstruction")
            self.assertIn("2026-11-12", text, f"{day} must date the reconstruction")


if __name__ == "__main__":
    unittest.main()
