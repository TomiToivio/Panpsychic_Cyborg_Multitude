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

## Date-aware report health

Run `python scripts/check_report_completeness.py` from the repository root. Coverage starts
on **2026-09-14**. Every earlier date is checked on every run, so missed mornings remain
visible. Today's missing report or morning carrier is permitted until **11:00 Europe/Helsinki**
(an explicit completion window covering the historical 10:00 watch and current 09:00 watch).
At the deadline it becomes a failure. UTC timestamps are converted with DST-aware timezone rules.
Use `--now 2026-11-12T10:00:00+02:00` for reproducible checks; naive timestamps are rejected.
`--start`, `--reports`, `--deadline` and `--waivers` support explicit audit scopes.

New report writers should include one status marker:

- `<!-- pcm-watch-status: pending -->` for a morning carrier;
- `<!-- pcm-watch-status: complete -->` after the watch is written;
- `<!-- pcm-watch-status: retrospective-evidence-gap -->` for a reconstruction that
  documents unrecoverable evidence. This counts as coverage and is separately listed,
  **not** treated as a completed historical scan.

Remove the old pending marker when completing a watch. Known legacy carrier declarations
are also detected. Ordinary prose discussing old placeholders is not itself a carrier.
Legacy reports without markers remain supported: this is a coverage/placeholder check,
not a semantic fact-checker or proof that every report contains a sufficient scan.

The separate **Report completeness** workflow runs after the completion window daily and
on relevant changes. Its status is independent of the application test workflow: green
software tests do not prove report coverage, and good coverage does not validate software.

Historical exceptions must be individual entries in [waivers.json](waivers.json), with
`reason`, `issue` and ISO-date `expires`. Waivers remain visible in the JSON output and
fail after expiry; no implicit exemption applies to past dates. September 26–27's legacy
carriers are temporarily waived through December 12, 2026 while archive recovery remains
outstanding under #88. They are not silently labelled complete.

October 8 and 16–18 were reconstructed on November 12, 2026 with explicit evidence gaps.
October 8's Daily Thoughts and provenance were retained verbatim. No private execution
records or missing reflections were fabricated.
