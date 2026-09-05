# -*- coding: utf-8 -*-
"""Minimal stdlib JSON API for the shared Multitude service."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from multitude.models import Position, Rule
from multitude.service import MultitudeService
from multitude.tribe import TribeError


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def make_handler(service: MultitudeService):
    class MultitudeApiHandler(BaseHTTPRequestHandler):
        server_version = "MultitudeAPI/0.1"

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _send(self, status: int, payload: Any) -> None:
            data = _json_bytes(payload)
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw.decode("utf-8") or "{}")
            except ValueError as exc:
                raise TribeError(f"invalid JSON body: {exc}") from exc

        def do_GET(self) -> None:  # noqa: N802
            try:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                if parsed.path == "/api/status":
                    self._send(200, service.status())
                    return
                if parsed.path == "/api/agents":
                    self._send(200, {"items": service.list_agents()})
                    return
                if parsed.path == "/api/events":
                    limit = int(params.get("limit", ["20"])[0])
                    days = params.get("days", [None])[0]
                    self._send(
                        200,
                        {"items": service.recent_events(limit=limit, days=int(days) if days else None)},
                    )
                    return
                if parsed.path == "/api/proposals":
                    status = params.get("status", [None])[0]
                    self._send(200, {"items": service.list_proposals(status=status)})
                    return
                if parsed.path.startswith("/api/proposals/"):
                    proposal_id = parsed.path.rsplit("/", 1)[-1]
                    self._send(200, service.get_proposal(proposal_id))
                    return
                if parsed.path == "/api/search":
                    query = params.get("query", [""])[0]
                    self._send(200, {"items": service.search_memory(query)})
                    return
                self._send(404, {"error": "not found"})
            except (TribeError, ValueError) as exc:
                self._send(400, {"error": str(exc)})

        def do_POST(self) -> None:  # noqa: N802
            try:
                payload = self._read_json()
                if self.path == "/api/proposals":
                    result = service.create_proposal(
                        title=payload["title"],
                        text=payload["text"],
                        author=payload["author"],
                        rule=payload.get("rule", Rule.CONSENSUS.value),
                    )
                    self._send(201, result)
                    return
                if self.path == "/api/votes":
                    result = service.vote(
                        proposal_id=payload["proposal_id"],
                        voter=payload["voter"],
                        position=Position(payload["position"]),
                        reason=payload.get("reason"),
                    )
                    self._send(200, result)
                    return
                if self.path == "/api/counsel":
                    result = service.counsel(
                        agent_name=payload["agent_name"],
                        topic=payload.get("topic", ""),
                        model=payload.get("model"),
                    )
                    self._send(200, {"message": result})
                    return
                if self.path == "/api/memory":
                    result = service.remember(
                        title=payload["title"],
                        text=payload["text"],
                        author=payload.get("author", ""),
                        kind=payload.get("kind", "note"),
                        tags=payload.get("tags", []),
                    )
                    self._send(201, result)
                    return
                self._send(404, {"error": "not found"})
            except (KeyError, TribeError, ValueError) as exc:
                self._send(400, {"error": str(exc)})

    return MultitudeApiHandler


def run_api_server(service: MultitudeService, host: str = "127.0.0.1", port: int = 8765) -> int:
    server = ThreadingHTTPServer((host, port), make_handler(service))
    try:
        print(f"Multitude API listening on http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
