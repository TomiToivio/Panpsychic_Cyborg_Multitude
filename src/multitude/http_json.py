# -*- coding: utf-8 -*-
"""Small JSON-over-HTTP helper with optional requests support.

The CLI should still import cleanly when the user's Python environment
has a broken third-party `requests` / `urllib3` installation. This
helper prefers requests when it imports successfully, then falls back to
the standard library.
"""
from __future__ import annotations

import json
from typing import Any, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


def _load_requests() -> Any | None:
    try:
        import requests  # type: ignore
    except Exception:
        return None
    return requests


def request_json(
    method: str,
    url: str,
    *,
    payload: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
    timeout: float = 30,
) -> tuple[int | None, dict[str, Any] | None]:
    method = method.upper()
    requests = _load_requests()
    if requests is not None:
        try:
            if method == "POST":
                resp = requests.post(url, json=payload, timeout=timeout)
            elif method == "GET":
                resp = requests.get(url, params=params, timeout=timeout)
            else:
                raise ValueError(f"unsupported method '{method}'")
            return resp.status_code, resp.json()
        except (requests.RequestException, ValueError, KeyError):
            return None, None

    if params:
        query = urllib_parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{query}"
    data = None
    headers: dict[str, str] = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib_request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", resp.getcode())
            raw = resp.read()
    except (urllib_error.HTTPError, urllib_error.URLError, ValueError):
        return None, None
    try:
        parsed = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        return status, None
    if not isinstance(parsed, dict):
        return status, None
    return status, parsed
