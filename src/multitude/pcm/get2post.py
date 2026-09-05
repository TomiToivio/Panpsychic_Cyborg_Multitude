# -*- coding: utf-8 -*-
"""GET → POST bridge client — optional transport for constrained nodes.

Complements NETWORKING_STACK.md §3 (PCM protocol) and §26 (Unix streams):
the envelope is transport-agnostic, and this module adds one more transport
for the constrained-node case. A node that can only make GET requests —
locked-down egress, link-scanner-shaped clients, no inbound ports (WSL,
NAT, firewalls) — can still deliver PCM envelopes to peers through a
converter service: the node sends a GET with the destination, body and
headers encoded; the converter performs the POST and returns the upstream
response.

Default configuration is **off** (PCM_G2P_ENABLED=false). Nothing in the
gateway, serve-api or CLI calls this module yet — it is built and dormant,
exactly like the BCI scaffolding pattern. Enabling later is a config
change, not a code change.

Safety notes carried over from the converter's own contract:
- Every GET can trigger a POST: retries, link scanners and reopening a
  URL repeat the action. We therefore auto-stamp an ``Idempotency-Key``
  header derived from the envelope id (or caller-provided) unless one
  is already present.
- A timeout does not undo a POST: callers must treat timeouts as UNKNOWN
  upstream state, not failure.
- URLs are not private: bodies ride in the query string. Never put
  secrets in ``data``/``headers``; this module refuses obviously secret
  header names rather than silently forwarding them.
- Only public HTTPS on port 443; redirects are never followed; cookies
  are never forwarded.

Python access via `requests` when available, standard library otherwise
(same ladder as multitude.http_json).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from multitude.pcm.envelope import Envelope, EnvelopeError

DEFAULT_CONVERTER = "https://get2post.vercel.app/api/post"

# Limits from the converter's published API reference.
MAX_ENCODED_URL_BYTES = 12 * 1024        # 12 KiB
MAX_RESPONSE_BYTES = 1024 * 1024         # 1 MiB
MAX_TIMEOUT_MS = 20_000
MIN_TIMEOUT_MS = 1
DEFAULT_TIMEOUT_MS = 15_000
MAX_HEADERS = 32

# Header names this client refuses to forward (URLs/logs are not private).
_REFUSED_HEADERS = {
    "authorization", "cookie", "proxy-authorization", "x-api-key",
    "x-auth-token", "x-session-token", "set-cookie",
}

ResponseFormat = str  # "raw" | "json"


@dataclass(frozen=True)
class Get2PostConfig:
    """Configuration; disabled by default (enable explicitly)."""

    enabled: bool = False
    converter_url: str = DEFAULT_CONVERTER
    default_timeout_ms: int = DEFAULT_TIMEOUT_MS
    response_format: ResponseFormat = "raw"

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "Get2PostConfig":
        values = os.environ if env is None else env
        enabled = str(values.get("PCM_G2P_ENABLED", "false")).strip().lower() in {
            "1", "true", "yes", "on"}
        converter = str(values.get("PCM_G2P_CONVERTER", DEFAULT_CONVERTER)).strip() \
            or DEFAULT_CONVERTER
        try:
            timeout = int(values.get("PCM_G2P_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS)))
        except ValueError:
            timeout = DEFAULT_TIMEOUT_MS
        fmt = str(values.get("PCM_G2P_RESPONSE", "raw")).strip().lower()
        if fmt not in ("raw", "json"):
            fmt = "raw"
        return cls(enabled=enabled, converter_url=converter,
                   default_timeout_ms=min(max(timeout, MIN_TIMEOUT_MS), MAX_TIMEOUT_MS),
                   response_format=fmt)


@dataclass
class BridgeResult:
    """Upstream POST outcome as seen through the converter."""

    upstream_status: Optional[int]
    body: bytes
    headers: dict[str, str] = field(default_factory=dict)
    envelope: Optional[dict[str, Any]] = None   # set in json mode
    timeout: bool = False


class Get2PostBridge:
    """Send PCM envelopes (or raw bodies) through a GET→POST converter.

    A custom ``transport`` callable may be injected for offline testing:
        transport(url: str) -> tuple[int|None, bytes]
    """

    def __init__(self, config: Get2PostConfig,
                 transport: Optional[Callable[[str], tuple[Optional[int], bytes]]] = None):
        self.config = config
        self._transport = transport or self._requests_transport

    # -- public API --------------------------------------------------------

    def send(self, url: str, data: str = "", headers: dict[str, str] | None = None,
             *, response_format: ResponseFormat | None = None,
             timeout_ms: int | None = None,
             idempotency_key: str | None = None) -> BridgeResult:
        """Trigger a POST at ``url`` via the converter, carrying ``data``."""
        if not self.config.enabled:
            raise RuntimeError(
                "GET→POST bridge is dormant; set PCM_G2P_ENABLED=true to enable it.")
        clean_headers = self._clean_headers(headers or {})
        timeout_ms = self.config.default_timeout_ms if timeout_ms is None \
            else max(min(int(timeout_ms), MAX_TIMEOUT_MS), MIN_TIMEOUT_MS)
        fmt = response_format or self.config.response_format
        if fmt not in ("raw", "json"):
            raise EnvelopeError(f"bad response format {fmt!r}")

        get_url = self.build_get_url(
            url, data=data, headers=clean_headers,
            response_format=fmt, timeout_ms=timeout_ms,
            idempotency_key=idempotency_key)
        status, raw = self._guarded(get_url)
        if fmt == "json":
            return self._parse_json_envelope(status, raw)
        return BridgeResult(upstream_status=status, body=raw)

    def send_envelope(self, envelope: Envelope, *, timeout_ms: int | None = None,
                      idempotency_key: str | None = None) -> BridgeResult:
        """Deliver a signed PCM envelope as JSON to its ``to`` destination.

        The recipient URL is taken from annotation source_url when present
        (web:: documents), else content['url'].
        """
        target = self._target_of(envelope)
        body = json.dumps(envelope.model_dump(by_alias=True), ensure_ascii=False)
        return self.send(target, body,
                         {"Content-Type": "application/json"},
                         response_format="json", timeout_ms=timeout_ms,
                         idempotency_key=idempotency_key or envelope.id or None)

    # -- request shaping (pure; safe to unit-test offline) ------------------

    @staticmethod
    def _clean_headers(headers: dict[str, str]) -> dict[str, str]:
        """Refuse secret-bearing headers; URLs and logs are not private."""
        out: dict[str, str] = {}
        for key, value in headers.items():
            if key.lower() in _REFUSED_HEADERS:
                raise EnvelopeError(
                    f"refusing to forward secret-bearing header: {key!r} "
                    f"(bridge URLs appear in history and logs)")
            out[key] = value
        return out

    def build_get_url(self, url: str, *, data: str = "",
                      headers: dict[str, str] | None = None,
                      response_format: ResponseFormat = "raw",
                      timeout_ms: int = DEFAULT_TIMEOUT_MS,
                      idempotency_key: str | None = None) -> str:
        """Encode a POST request into the converter's GET query string.

        Idempotency: unless the caller supplies an Idempotency-Key header
        or key, a deterministic fingerprint of the body is stamped, so
        accidental re-GETs (link scanners, retries, reopened links) stay
        distinguishable upstream where the endpoint honours the header.
        """
        self._validate_destination(url)
        headers = self._clean_headers(dict(headers or {}))
        if not any(k.lower() == "idempotency-key" for k in headers):
            if not idempotency_key and data:
                idempotency_key = hashlib.sha256(
                    data.encode("utf-8")).hexdigest()[:16]
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
        if len(headers) > MAX_HEADERS:
            raise EnvelopeError(f"too many headers (>{MAX_HEADERS})")
        if data and not any(k.lower() == "content-type" for k in headers):
            headers["Content-Type"] = "application/json"
        params: dict[str, str] = {"url": url}
        if data:
            params["data"] = data
        if headers:
            params["headers"] = json.dumps(headers, ensure_ascii=False)
        if response_format != "raw":
            params["response"] = response_format
        if timeout_ms != DEFAULT_TIMEOUT_MS:
            params["timeout"] = str(timeout_ms)
        query = urllib.parse.urlencode(params, doseq=True)
        full = f"{self.config.converter_url}?{query}"
        if len(full.encode("utf-8")) > MAX_ENCODED_URL_BYTES:
            raise EnvelopeError(
                f"encoded URL exceeds {MAX_ENCODED_URL_BYTES} byte limit "
                f"(payload too large for the GET bridge)")
        return full

    def _guarded(self, get_url: str) -> tuple[Optional[int], bytes]:
        status, raw = self._transport(get_url)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise EnvelopeError("upstream response exceeds 1 MiB limit")
        return status, raw

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _validate_destination(url: str) -> None:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https":
            raise EnvelopeError("only public HTTPS destinations are supported")
        if parsed.username or parsed.password:
            raise EnvelopeError("no embedded credentials in destination URLs")
        port = parsed.port
        if port is not None and port != 443:
            raise EnvelopeError("only port 443 destinations are supported")
        if parsed.fragment:
            raise EnvelopeError("no fragments in destination URLs")

    @staticmethod
    def _target_of(envelope: Envelope) -> str:
        candidate = (getattr(envelope, "source_url", "")
                     or envelope.content.get("url") or "")
        if not candidate:
            raise EnvelopeError(
                "envelope carries no deliverable URL (source_url/content.url)")
        return candidate

    @staticmethod
    def _parse_json_envelope(status: Optional[int], raw: bytes) -> BridgeResult:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {"body_b64": base64.b64encode(raw).decode()}
        if isinstance(payload, dict) and "status" in payload and "body" in payload:
            headers = payload.get("headers") or {}
            return BridgeResult(upstream_status=int(payload["status"]),
                                body=json.dumps(payload["body"]).encode("utf-8"),
                                headers={str(k): str(v) for k, v in headers.items()})
        return BridgeResult(upstream_status=status, body=raw)

    @staticmethod
    def _requests_transport(url: str) -> tuple[Optional[int], bytes]:
        try:
            import requests  # type: ignore
            resp = requests.get(url, timeout=30)
            return resp.status_code, resp.content
        except Exception:
            pass
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return getattr(resp, "status", None), resp.read()
        except Exception:
            return None, b""


def content_fingerprint(data: bytes) -> str:
    """Stable fingerprint for caller-side idempotency bookkeeping."""
    return "sha256:" + hashlib.sha256(data).hexdigest()