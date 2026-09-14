# Claude Code integration

PCM treats Claude Code as an external technological participant. The Python package has no Claude/Anthropic dependency and remains fully usable when Claude Code is absent.

Architecture:

```text
Claude Code
   |
   v
ClaudeTools
   |
   v
ClaudeCodeAdapter
   |
   v
MultitudeHermesAdapter service/permission boundary
   |
   v
PCM service + Rhizome state + canonical transports
```

The inheritance is intentional: Hermes and Claude share the same permission object, fail-closed checks, proposal/vote semantics, service calls, and event provenance rather than duplicating policy in two runtimes.

Default identity: `agent:claude-code`.
Default role: `developer_research_assistant`.
Default authority remains the existing low-privilege knowledge-steward permission set. Voting, blocking, governance mutation, treasury operations, membership changes, and history deletion are denied by default.

`ClaudeTools` exposes only a small PCM-facing surface: inspect status/identity/events, search permitted memory, inspect goals/proposals, and create proposals. Voting/governance methods exist only to exercise the same permission boundary and fail closed unless explicitly granted. There is intentionally no generic unrestricted shell tool.

Claude does not gain a separate memory database, message bus, Zenoh namespace implementation, Telegram bot, or governance system. Where transport participation is enabled, messages must use PCM's canonical envelope/transport path. Telegram remains downstream transport rather than Claude-specific code.

Agent proposals are distinct from accepted collective state. Repository/workspace modification is an external Claude Code capability and must still be explicitly authorized by the surrounding workflow; its technical availability does not create PCM authority.

Consciousness claims do not participate in authorization. The profile deliberately records consciousness as unknown. J-Space/introspection measurements and phenomenological self-report are research observations, not privilege signals.

## Tests

`tests/test_claude_integration.py` is offline and verifies import without Claude installed, stable technological identity, exact sharing of the Hermes permission class, denied voting by default, proposal provenance, absence of default administrative authority, and the consciousness/authority separation.

Existing `tests/test_hermes_integration.py` continues to cover Hermes behavior and compatibility-sensitive identity semantics.
