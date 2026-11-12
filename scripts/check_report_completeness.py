"""Date-aware report health, separate from application test health (stdlib only)."""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
# Match carrier declarations, not completed watches discussing historical gaps.
CARRIER = re.compile(
    r'^\s*(?:\*\*)?Placeholder, not a scan|'
    r'^\s*Set by the daily watch[’\']s run when it arrives\.|'
    r'^\s*(?:[-*] )?(?:Repository changes and health|Issues|Papers and research|'
    r'Tooling and infrastructure)\s*[:—–-]\s*(?:pending|awaiting)',
    re.IGNORECASE | re.MULTILINE,
)
STATUS = re.compile(r'<!--\s*pcm-watch-status:\s*([\w-]+)\s*-->', re.I)
VALID = {'complete', 'retrospective-evidence-gap', 'pending'}


def inspect_reports(directory: Path, start: date, now: datetime,
                    deadline: time = time(11), waivers: dict | None = None) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('now must include a timezone offset')
    local = now.astimezone(ZoneInfo('Europe/Helsinki'))
    waivers = waivers or {}
    # Explicit, bounded waivers only; never exempt an entire historical range.
    for day, waiver in waivers.items():
        date.fromisoformat(day)
        if not waiver.get('reason', '').strip() or not waiver.get('issue', '').strip():
            raise ValueError(f'{day}: waiver needs reason and issue')
        date.fromisoformat(waiver['expires'])
    failures, waived, gaps, pending = [], [], [], []
    day = start
    while day <= local.date():
        path = directory / f'{day}.md'
        due = day < local.date() or local.time() >= deadline
        problem = None
        if not path.exists():
            problem = 'missing'
        else:
            content = path.read_text(encoding='utf-8')
            statuses = [s.lower() for s in STATUS.findall(content)]
            if len(statuses) > 1 or any(s not in VALID for s in statuses):
                problem = 'invalid status'
            elif not content.strip():
                problem = 'empty report'
            elif 'pending' in statuses or CARRIER.search(content):
                problem = 'unresolved placeholder'
            elif 'retrospective-evidence-gap' in statuses:
                gaps.append(str(day))
        if problem:
            item = {'date': str(day), 'problem': problem}
            waiver = waivers.get(str(day))
            if not due:
                pending.append(item)
            elif waiver and local.date() <= date.fromisoformat(waiver['expires']):
                waived.append({**item, **waiver})
            else:
                failures.append(item)
        day += timedelta(days=1)
    return {'as_of': local.isoformat(), 'deadline': deadline.isoformat(),
            'failures': failures, 'waived': waived, 'not_due': pending,
            'retrospective_evidence_gaps': gaps}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, default=ROOT / 'docs/reports')
    parser.add_argument('--start', type=date.fromisoformat, default=date(2026, 9, 14))
    parser.add_argument('--now', type=datetime.fromisoformat,
                        default=datetime.now(ZoneInfo('Europe/Helsinki')))
    parser.add_argument('--deadline', type=time.fromisoformat, default=time(11))
    parser.add_argument('--waivers', type=Path, default=ROOT / 'docs/reports/waivers.json')
    args = parser.parse_args()
    try:
        result = inspect_reports(args.reports, args.start, args.now, args.deadline,
                                 json.loads(args.waivers.read_text(encoding='utf-8')))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 1 if result['failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
