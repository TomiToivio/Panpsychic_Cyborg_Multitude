# -*- coding: utf-8 -*-
"""Matrix adapter skeleton — Phase 1 component (NETWORKING_STACK.md §7).

Read-only skeleton for the Matrix transport. Phase 1 scope:

  - ``MatrixEnvelope`` / ``MatrixResponse`` — wire shapes mirroring the
    Telegram package's envelope/response pair.
  - ``MatrixAdapter.handle_message`` — maps an inbound Matrix room
    message onto the shared service layer (same boundary as Telegram).
  - ``MatrixGateway`` — construction + ``poll_once`` skeleton for a
    sync-token-based long-poll loop. **Not wired to any homeserver yet**;
    actual sync requires matrix-nio (optional extra) and credentials that
    must stay outside Git.

The adapter is deliberately inert: without PCM_MATRIX_ENABLED=true and a
configured homeserver it refuses to run. No daemon, bot or CLI invokes it
in Phase 1 — this is the seam the network design will grow through.

Design consequences carried from the spec:
- Federation-friendly: one room = one tribe square; DMs = peer channels.
- E2EE-ready: envelope payloads stay small and JSON-shaped so they can
  ride inside encrypted events once Olm/Megolm is enabled (Phase 3).
- The kernel never learns Matrix: this adapter translates, the service
  layer decides.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


class MatrixConfigError(RuntimeError):
    """Matrix transport is not configured or is disabled."""


@dataclass
class MatrixEnvelope:
    """Inbound Matrix room message reduced to the fields PCM needs."""

    sender: str                      # Matrix user ID (@user:homeserver)
    room_id: str                     # !room:homeserver
    event_id: str                    # $event identifier
    text: str = ""
    ts: Optional[str] = None
    direct_message: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MatrixResponse:
    text: str
    delivered: bool = True
    mutated: bool = False


@dataclass
class MatrixAdapter:
    """Room-message interface over the shared service layer.

    ``member_name`` is the tribe member this adapter speaks as; the
    service layer enforces permissions, exactly as for CLI/Telegram.
    """

    tribe: Any                        # multitude.tribe.Tribe
    member_name: str
    role: str = "knowledge_steward"
    model: Optional[str] = None
    homeserver_url: str = ""
    access_token_env: str = "PCM_MATRIX_ACCESS_TOKEN"

    def _guard(self) -> None:
        import os
        if not os.environ.get("PCM_MATRIX_ENABLED", "").lower() in {"1", "true", "yes", "on"}:
            raise MatrixConfigError(
                "Matrix transport is dormant; set PCM_MATRIX_ENABLED=true to enable it.")
        if not self.homeserver_url:
            raise MatrixConfigError("no homeserver_url configured for the Matrix adapter")

    def handle_message(self, envelope: MatrixEnvelope) -> Optional[MatrixResponse]:
        """Process one room message. Phase 1 handles only plain text.

        Returns a MatrixResponse when the message warrants a reply, None
        when it should be ignored (empty text, ambient noise).
        """
        self._guard()
        text = (envelope.text or "").strip()
        if not text:
            return None
        # The write path is the shared service layer; nothing here touches
        # the store directly.
        entry = self.tribe.say(text, kind="say", meta={
            "interface": "matrix",
            "sender": envelope.sender,
            "room_id": envelope.room_id,
            "event_id": envelope.event_id,
        })
        return MatrixResponse(text=f"recorded: {text[:120]}", mutated=True)

    def latest_context(self, limit: int = 5) -> list[str]:
        """Read-only convenience: recent tribe log lines as text."""
        events = self.tribe.store.replay() if hasattr(self.tribe, "store") else []
        out = []
        for ev in events[-limit:]:
            payload = ev.payload if isinstance(ev.payload, dict) else {}
            message = payload.get("message") or {}
            text = message.get("text") or payload.get("summary") or ""
            if text:
                out.append(f"{ev.ts} {ev.actor}: {text[:160]}")
        return out


@dataclass
class MatrixGateway:
    """Homeserver polling skeleton. Dormant until explicitly enabled."""

    adapter: MatrixAdapter
    since_token: str = ""

    def poll_once(self) -> list[MatrixEnvelope]:
        """Placeholder for the matrix-nio sync loop (Phase 2+).

        Raises MatrixConfigError so an accidental daemon start cannot
        silently do nothing.
        """
        raise MatrixConfigError(
            "MatrixGateway.poll_once is not implemented in Phase 1; "
            "wire matrix-nio sync in Phase 2 with credentials from the environment.")