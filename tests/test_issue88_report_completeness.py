"""Report completeness is its own health signal (#88).

The defect this file guards is not a crash. `docs/reports/2026-10-08.md` sat with the morning carrier's
"waiting for the watch" placeholder for five weeks while every CI run was green: the *Tests* workflow
proves the code executes, and it cannot see that a report never arrived. Those are two different health
questions, and the second one now has a date-aware check.

The rules the check must hold, in the order they can go wrong:

* a same-day placeholder is legitimate before the watch's cutoff hour and a defect after it;
* a *stale* placeholder — any earlier date — is a defect regardless of when the check runs, so the check
  does not need to run on the morning it describes;
* a report that records its own gap is **resolved**, not missing: "there was no watch" written down is
  different from a file that does not exist;
* a missing past date is a defect unless someone wrote down a waiver, and a waiver is reported rather
  than silently skipped.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_report_completeness.py"
spec = importlib.util.spec_from_file_location("check_report_completeness", SCRIPT)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


COMPLETE = """# PCM Daily Report — {day}

## Daily watch

### 1. Repository changes and health [established]

The newest main commit is `abc1234`, and both workflows are green for it.

## Priorities

1. Something followable.
"""

GAP = """# PCM Daily Report — {day}

## Daily watch — gap report (reconstructed 2026-11-12)

**There is no watch report for this date.** No commits on main, no carrier, no workflow run.

**Report status: gap.** This is not a completed watch.
"""

PLACEHOLDER = """# PCM Daily Report — {day}

## Daily watch

**Placeholder, not a scan.** This report is the morning thoughts' public bearer, created by the
pcm-daily-thoughts job because the daily watch job's run (10:00 EEST) comes later.

## Priorities

Set by the daily watch's run when it arrives.

---

## Daily thoughts — {day} (node reflection)

Some reflection.
"""

SEPTEMBER = """# PCM Daily Watch — {day}

## 1. Repo changes and health

**Established:** main changed today.
"""


def write(reports: Path, day: str, text: str) -> None:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / f"{day}.md").write_text(text.format(day=day), encoding="utf-8")


def test_a_structured_watch_counts_as_complete(tmp_path: Path):
    write(tmp_path, "2026-11-01", COMPLETE)
    states = checker.check_reports(tmp_path, first=date(2026, 11, 1), as_of=date(2026, 11, 1))
    assert states[0].status == checker.COMPLETE
    assert not states[0].violation


def test_a_recorded_gap_is_resolved_rather_than_missing(tmp_path: Path):
    write(tmp_path, "2026-10-16", GAP)
    states = checker.check_reports(tmp_path, first=date(2026, 10, 16), as_of=date(2026, 10, 16))
    assert states[0].status == checker.GAP
    assert not states[0].violation, "an absence written down is not an absence"


def test_a_stale_placeholder_is_a_violation_whatever_day_the_check_runs(tmp_path: Path):
    write(tmp_path, "2026-10-08", PLACEHOLDER)
    states = checker.check_reports(
        tmp_path,
        first=date(2026, 10, 8),
        as_of=date(2026, 10, 8),
        now=datetime(2026, 11, 12, 9, 0),
    )
    assert states[0].status == checker.PLACEHOLDER
    assert states[0].violation


def test_a_same_day_placeholder_before_the_cutoff_is_the_expected_state(tmp_path: Path):
    write(tmp_path, "2026-11-12", PLACEHOLDER)
    states = checker.check_reports(
        tmp_path,
        first=date(2026, 11, 12),
        as_of=date(2026, 11, 12),
        now=datetime(2026, 11, 12, 9, 0),
    )
    assert states[0].status == checker.PLACEHOLDER
    assert not states[0].violation, "the watch runs mid-morning; 09:00 is not a failure"
    assert states[0].waived is True


def test_the_same_placeholder_after_the_cutoff_is_a_violation(tmp_path: Path):
    write(tmp_path, "2026-11-12", PLACEHOLDER)
    states = checker.check_reports(
        tmp_path,
        first=date(2026, 11, 12),
        as_of=date(2026, 11, 12),
        now=datetime(2026, 11, 12, 18, 0),
    )
    assert states[0].violation


def test_a_missing_past_date_is_a_violation(tmp_path: Path):
    states = checker.check_reports(tmp_path, first=date(2026, 11, 10), as_of=date(2026, 11, 11))
    assert [s.status for s in states] == [checker.MISSING, checker.MISSING]
    assert all(s.violation for s in states)


def test_a_waived_date_is_reported_but_not_failed(tmp_path: Path):
    states = checker.check_reports(
        tmp_path,
        first=date(2026, 9, 28),
        as_of=date(2026, 9, 28),
        waivers={"2026-09-28": "carrier-only report from before the watch's report format"},
    )
    assert states[0].status == checker.MISSING
    assert states[0].waived is True
    assert not states[0].violation


def test_a_complete_report_that_quotes_a_placeholder_is_not_flagged(tmp_path: Path):
    """Real reports quote carrier commits ("watch sections pending"); prose must not fake a defect."""
    text = COMPLETE.format(day="2026-10-25") + (
        "\nThe carrier message says 'carrier report, watch sections pending', which this run replaced.\n"
    )
    write(tmp_path, "2026-10-25", text.replace("{day}", "2026-10-25"))
    states = checker.check_reports(tmp_path, first=date(2026, 10, 25), as_of=date(2026, 10, 25))
    assert states[0].status == checker.COMPLETE


def test_the_september_format_is_recognised(tmp_path: Path):
    write(tmp_path, "2026-09-14", SEPTEMBER)
    states = checker.check_reports(tmp_path, first=date(2026, 9, 14), as_of=date(2026, 9, 14))
    assert states[0].status == checker.COMPLETE


def test_the_cli_exit_code_separates_health_from_code_health(tmp_path: Path, capsys):
    write(tmp_path, "2026-11-11", COMPLETE)
    ok = checker.main(["--reports", str(tmp_path), "--since", "2026-11-11", "--as-of", "2026-11-11"])
    assert ok == 0
    capsys.readouterr()

    bad = checker.main(["--reports", str(tmp_path), "--since", "2026-11-10", "--as-of", "2026-11-11"])
    assert bad == 1, "a missing report fails this check and nothing about the code"


def test_the_repository_has_no_unresolved_report_gaps():
    """The real tree, at the newest report that exists — never "today", which the watch may not have reached."""
    reports = ROOT / "docs" / "reports"
    newest = max(
        date.fromisoformat(path.stem)
        for path in reports.glob("*.md")
        if path.stem[:4].isdigit()
    )
    waivers = checker.load_waivers(reports / "waivers.json")
    states = checker.check_reports(
        reports,
        first=date(2026, 9, 14),
        as_of=newest,
        waivers=waivers,
    )
    violations = [state for state in states if state.violation]
    assert not violations, (
        "unresolved report gaps (this is report completeness, not code health): "
        + ", ".join(f"{state.day} {state.status} ({state.detail})" for state in violations)
    )
    # The backfill this issue asked for is present and classified as resolved, not waived.
    backfilled = {state.day.isoformat(): state for state in states}
    assert backfilled["2026-10-08"].status == checker.COMPLETE
    for day in ("2026-10-16", "2026-10-17", "2026-10-18"):
        assert backfilled[day].status == checker.GAP
        assert not backfilled[day].waived


def test_waivers_are_json_with_reasons():
    payload = json.loads((ROOT / "docs" / "reports" / "waivers.json").read_text(encoding="utf-8"))
    waived = payload["waived"]
    assert waived, "the pre-format carrier-only dates are the documented exception"
    for day, reason in waived.items():
        date.fromisoformat(day)
        assert len(reason) > 40, f"waiver for {day} needs a real reason, not a shrug"


def test_the_october_eight_report_no_longer_carries_the_placeholder():
    text = (ROOT / "docs" / "reports" / "2026-10-08.md").read_text(encoding="utf-8")
    assert "Placeholder, not a scan." not in text
    assert "retrospective reconstruction" in text.casefold()
    assert "## Daily thoughts — 2026-10-08" in text, "the reflection is preserved verbatim"


@pytest.mark.parametrize("day", ["2026-10-16", "2026-10-17", "2026-10-18"])
def test_the_gap_reports_do_not_invent_observations(day: str):
    text = (ROOT / "docs" / "reports" / f"{day}.md").read_text(encoding="utf-8")
    assert "Report status: gap" in text
    for forbidden in ("## Priorities", "## Daily thoughts"):
        assert forbidden not in text, "a gap report must not manufacture a day's content"
