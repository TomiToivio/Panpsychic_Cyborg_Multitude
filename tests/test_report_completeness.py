from datetime import date, datetime
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location(
    'report_health', Path(__file__).resolve().parents[1] / 'scripts/check_report_completeness.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


def check(tmp_path, now='2026-10-09T12:00:00+03:00', **kwargs):
    return health.inspect_reports(tmp_path, date(2026, 10, 8), datetime.fromisoformat(now), **kwargs)


def write(tmp_path, day, text):
    (tmp_path / f'2026-10-{day}.md').write_text(text, encoding='utf-8')


def test_completed_report_can_discuss_old_placeholders(tmp_path):
    for day in ('08', '09'):
        write(tmp_path, day, '# Report\nThe October 1 placeholder remains a historical gap.')
    assert check(tmp_path)['failures'] == []


def test_same_day_carrier_is_allowed_only_before_deadline(tmp_path):
    write(tmp_path, '08', '**Placeholder, not a scan.**')
    assert not check(tmp_path, '2026-10-08T10:59:59+03:00')['failures']
    assert check(tmp_path, '2026-10-08T11:00:00+03:00')['failures'][0]['problem'] == 'unresolved placeholder'


def test_stale_carrier_detected_next_morning(tmp_path):
    write(tmp_path, '08', '**Placeholder, not a scan.**')
    result = check(tmp_path, '2026-10-09T08:00:00+03:00')
    assert result['failures'] == [{'date': '2026-10-08', 'problem': 'unresolved placeholder'}]
    assert result['not_due'] == [{'date': '2026-10-09', 'problem': 'missing'}]


def test_missing_past_day_detected_days_later(tmp_path):
    result = check(tmp_path, '2026-10-12T08:00:00+03:00')
    assert len(result['failures']) == 4
    assert result['failures'][0] == {'date': '2026-10-08', 'problem': 'missing'}


def test_explicit_waiver_expires_and_is_reported(tmp_path):
    waiver = {'2026-10-08': {'reason': 'Archive recovery', 'issue': '#88', 'expires': '2026-10-09'}}
    result = check(tmp_path, '2026-10-09T08:00:00+03:00', waivers=waiver)
    assert not result['failures'] and len(result['waived']) == 1
    assert check(tmp_path, '2026-10-10T08:00:00+03:00', waivers=waiver)['failures']


def test_unexplained_waiver_rejected(tmp_path):
    with pytest.raises(ValueError):
        check(tmp_path, waivers={'2026-10-08': {'expires': '2026-10-09'}})


def test_retrospective_gap_is_visible_not_claimed_as_scan(tmp_path):
    write(tmp_path, '08', '<!-- pcm-watch-status: retrospective-evidence-gap -->\nEvidence unavailable.')
    result = check(tmp_path, '2026-10-09T08:00:00+03:00')
    assert not result['failures']
    assert result['retrospective_evidence_gaps'] == ['2026-10-08']


def test_explicit_complete_cannot_hide_carrier(tmp_path):
    write(tmp_path, '08', '<!-- pcm-watch-status: complete -->\n**Placeholder, not a scan.**')
    assert check(tmp_path)['failures'][0]['problem'] == 'unresolved placeholder'


@pytest.mark.parametrize('content', ['', '<!-- pcm-watch-status: pending -->',
    '<!-- pcm-watch-status: typo -->',
    '<!-- pcm-watch-status: complete --><!-- pcm-watch-status: pending -->'])
def test_incomplete_or_invalid_status_fails(tmp_path, content):
    write(tmp_path, '08', content)
    assert check(tmp_path)['failures'][0]['date'] == '2026-10-08'


def test_helsinki_deadline_across_dst(tmp_path):
    for now, expected in [('2026-10-08T07:59:00+00:00', False),
                          ('2026-10-08T08:00:00+00:00', True),
                          ('2026-11-08T08:59:00+00:00', False),
                          ('2026-11-08T09:00:00+00:00', True)]:
        instant = datetime.fromisoformat(now)
        result = health.inspect_reports(tmp_path, instant.date(), instant)
        assert bool(result['failures']) is expected


def test_naive_time_rejected(tmp_path):
    with pytest.raises(ValueError):
        check(tmp_path, '2026-10-08T08:00:00')
