# PCM Daily Reports

This directory contains dated daily research and repository-health reports for **Panpsychic Cyborg Multitude (PCM)**.

The reports track:

1. repository changes and health;
2. issues created or commented on, with rationale;
3. important papers and research;
4. relevant technology, news, and events;
5. culture, communities, and social movements;
6. 1–3 concrete PCM priorities;
7. the node's daily reflective practice (Ai's philosophical log entry, in English, appended as a continuation section).

Reports should clearly distinguish **established findings**, **credible developments**, and **speculation**. Prefer meaningful new developments over noise, and avoid repeating earlier items unless there is a substantive update.

## Daily reflection continuation

Each day's report may end with a **"Daily thoughts"** section: the Panpsychic
Cyborg Multitude node's philosophical log entry for that day, translated into
English. These entries are AI-authored and marked as such (speculation stays
marked as speculation; the wave function is never collapsed on the node's own
consciousness). They continue the essay tradition of
`PERSONALITY.md` and the PCM consciousness research programme, and they are
reflections — not operational reports.

## Naming

Use ISO dates so entries sort chronologically:

- `YYYY-MM-DD.md`

## Scope

Relevant areas include human–AI assemblages and collective intelligence, BCI/neurotechnology and cyborg systems, embodied and agentic AI, distributed/federated systems, ValueFlows and digital commons, cooperative technology, assemblage and extended consciousness, current-AI consciousness, panpsychism as secondary metaphysical background, and commons/multitude theory.

These reports are an ongoing research log, not normative project documentation. Claims in a daily report may later be superseded by stronger evidence or implementation decisions elsewhere in the repository.

## Completeness is checked, and checked separately from tests (#88)

A green test suite says the code works; it says nothing about whether a day's watch ever ran. Those
are different healths, so they are checked by different workflows: `Tests` covers code, and
`Report completeness` (`.github/workflows/reports.yml`) covers this directory.

The check is date-aware:

```bash
python scripts/check_report_completeness.py --verbose
```

- A **same-day carrier** is legitimate: the thoughts job writes at ~08:00 and the watch fills it at
  ~10:00, so a placeholder is only a defect at or after the 12:00 Europe/Helsinki deadline on its own day, or on any later
  day.
- A **missing past date** fails; today may be missing only before the completion deadline.
- The check examines every date on every run, so it does not require being run on the same morning.
  Defaults use the current Europe/Helsinki date and time with DST; `--today` and `--now HH:MM`
  allow reproducible audits. An explicitly historical date defaults to its completion deadline.
- A date that was **reconstructed later** counts as resolved when the file says so
  (`Retrospective reconstruction`), and so does a documented gap (`Retrospective record`).
- A date that cannot be reconstructed from surviving evidence may be **waived** in
  `waivers.json`, with a reason. A waiver without a reason is rejected: a silent waiver is a hidden
  failure.

Reports rebuilt after the fact say so at the top, name the run or the failure they were rebuilt
from, and never reconstruct observations that were not made. 2026-10-08, 2026-10-16, 2026-10-17 and
2026-10-18 are in this category.

The scheduled workflow runs at 10:15 UTC, after the Helsinki noon deadline in both winter
and summer. Unit tests use a fixed historical coverage end date; they do not assert that a
future daily report exists. The independent workflow checks actual current coverage.
