# Claude Code in PCM

Claude Code is an external technological participant in Panpsychic Cyborg Multitude, not a privileged controller and not a PCM-native LLM backend.

Read `AGENTS.md` first. For architecture work also read `README.md`, `docs/USER_GUIDE.md`, `docs/NETWORKING_STACK.md`, `src/multitude/service.py`, relevant `src/multitude/pcm/` modules, and existing integration tests.

Canonical path:

`Claude Code -> src/multitude/integrations/claude -> PCM adapter/service -> identity / permissions / memory / governance / messaging / transport`

Use `ClaudeCodeAdapter` and `ClaudeTools`. Do not bypass permissions or mutate Rhizome internals directly when the canonical service path exists. The default participant identity is `agent:claude-code` and is intentionally low privilege.

Do not add Claude or Anthropic SDKs as PCM core dependencies merely to support Claude Code. Core PCM remains usable without Claude installed and preserves its local-first/distributed architecture.

Never commit credentials, private operational configuration, or unrestricted command-execution helpers. Repository changes, destructive operations, external messages, device control, security/identity changes, and governance changes require the relevant authorization outside technical capability alone.

Consciousness is a research question, not an authorization bit. Do not turn self-report, J-Space readings, IIT Phi, relational metrics, or other speculative theory into implementation facts or permission grants.

Run the relevant offline tests before proposing architectural changes. Keep runtime-specific code thin and place generic PCM semantics in the canonical kernel/service layers.
