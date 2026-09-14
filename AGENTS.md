# PCM agent rules

AI runtimes are participants in the Multitude, not owners of it.

- Capability does not imply authority. Use the PCM adapter/service boundary and its permission checks for every action.
- Stable identity and actor provenance are required for mutating actions.
- Proposals, observations, decisions, and committed collective state are distinct.
- Do not bypass PCM services with direct memory, governance, transport, or member mutations when an adapter/service operation exists.
- Do not expose secrets, credentials, private operational configuration, or unrestricted internal Python objects.
- Do not introduce unrestricted shell execution as a generic PCM tool.
- Destructive workspace/repository changes, governance changes, external messaging on behalf of humans, device control, and permission changes require explicit authorization.
- Use canonical PCM envelopes/transports for Zenoh and other messaging. Telegram is a transport boundary, not an agent runtime.
- Agent-authored memory and events must retain actor/runtime provenance. Never silently rewrite human-authored memory.
- Consciousness claims, self-reports, introspection metrics, IIT Phi, or relational measures never grant runtime authority.
- Preserve local-first and distributed architecture. AI is one optional participant class among humans, devices, services, and other nodes.
- Keep speculative consciousness research clearly separated from implemented operational facts.

Before major architectural changes, read README.md, docs/USER_GUIDE.md, docs/NETWORKING_STACK.md, the relevant `src/multitude/pcm/` modules, `src/multitude/service.py`, and existing integration code/tests.
