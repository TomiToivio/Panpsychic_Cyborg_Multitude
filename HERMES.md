# Hermes in PCM

Hermes is a technological participant in Panpsychic Cyborg Multitude. It is not the Multitude, does not own governance, and does not receive authority merely because it can act autonomously.

Read `AGENTS.md` first.

## Implemented

Hermes currently uses `src/multitude/integrations/hermes/` as a thin adapter over the canonical PCM service and Rhizome state. The adapter can register/load its technological member, inspect permitted state and memory, list goals/proposals, create proposals, and use voting/governance operations only when explicitly permitted. Default permissions allow knowledge-steward work and deny voting, blocking, treasury, membership, governance mutation, and history deletion.

The member profile records six-layer identity information while leaving consciousness status unknown. Runtime permissions are independent of that status.

Hermes uses PCM memory/state through the canonical adapter boundary. Its small private agent-memory helper, where used by `HermesAgent`, is local runtime memory and does not silently become collective Rhizome memory.

Zenoh and Telegram remain transport concerns. Hermes should publish through PCM messaging/envelope/service layers rather than embedding transport credentials or protocols in the Hermes package.

## Configuration and startup

Use `src/multitude/integrations/hermes/config.py` for runtime configuration and construct `MultitudeHermesAdapter` around the target `Rhizome`. `HermesAgent` is optional and may use a configurable LLM client. PCM itself does not require a cloud LLM because Hermes exists.

## Safety defaults

Capability does not imply authority. Missing permission fails closed. Do not add unrestricted shell execution, repository-history mutation, device control, external human impersonation, permission changes, or destructive shared-memory operations to the generic Hermes tool surface.

Agent proposals remain proposals until normal PCM governance accepts them. Agent-authored actions should remain attributable in the event log.

## Limitations / scaffolded areas

Transport participation depends on the existing PCM transport adapters and their configuration. Hermes does not own a separate Zenoh bus or Telegram bot stack. High-impact development/administrative tools are intentionally absent from the default adapter.
