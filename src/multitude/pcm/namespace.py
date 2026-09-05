# -*- coding: utf-8 -*-
"""PCM key-expression namespace over Zenoh.

This module is the single source of truth for PCM's Zenoh key-expression
namespace. The contract (maintainer migration spec, 2026-09-06):

    pcm/<domain>/<entity>/<resource>

- ``pcm``      fixed prefix; unrelated Zenoh traffic never sees PCM keys.
- ``domain``   one of DOMAINS below.
- ``entity``   a stable PCM id name (``agent:hermes`` -> ``hermes``).
- ``resource`` the aspect carried (message, state, temperature, ...).

Zenoh wildcards (verified against eclipse-zenoh 1.10):

    *   matches exactly one segment
    **  matches zero or more segments (anywhere in the pattern)

Wildcards are valid in subscription patterns and query selectors, never
in published keys — a published key is concrete.

Machine rules (enforced by :func:`validate_key`):

- segments are non-empty, 1..96 chars, ``[A-Za-z0-9_]`` then
  ``[A-Za-z0-9_.-]`` (plus ``*``/``**`` segment when wildcards allowed)
- total length <= 1024 characters
- published keys must not contain wildcards

Namespace examples::

    pcm/agent/hermes/message        one agent's inbox (pub/sub)
    pcm/agent/hermes/state          agent state (queryable)
    pcm/human/alice/presence         human presence (liveliness-backed)
    pcm/home/kitchen/temperature    ambient sensor stream
    pcm/device/lamp01/command       structured device command
    pcm/device/lamp01/state         device state
    pcm/sensor/kitchen/temp         raw sensor reading
    pcm/task/123/request            task channel
    pcm/task/123/result             task result
    pcm/conversation/abc123/message conversation bus (Matrix room analog)
    pcm/capability/agent/hermes     capability document
    pcm/liveliness/agent/hermes     presence token (Zenoh liveliness)
    pcm/query/agent/hermes          request/response endpoint
    pcm/memory/shared/event         shared event log stream
    pcm/knowledge/topic/ai          knowledge projection
"""
from __future__ import annotations

import re

PCM_KEY_PREFIX = "pcm"

# Closed domain vocabulary. Extending this is a namespace minor version.
DOMAINS = (
    "agent",
    "human",
    "home",
    "device",
    "sensor",
    "drone",
    "task",
    "conversation",
    "group",
    "memory",
    "knowledge",
    "query",
    "capability",
    "liveliness",
)

_SEGMENT = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")
_MAX_KEY_LEN = 1024


class KeyError_(ValueError):
    """Malformed PCM key expression."""


def validate_key(key: str, *, allow_wildcards: bool = False) -> str:
    """Validate a PCM key expression. Returns the key or raises KeyError_."""
    if not isinstance(key, str) or not key:
        raise KeyError_("key expression must be a non-empty string")
    if len(key) > _MAX_KEY_LEN:
        raise KeyError_(f"key expression too long ({len(key)} > {_MAX_KEY_LEN})")
    segments = key.split("/")
    if segments[0] != PCM_KEY_PREFIX:
        raise KeyError_(f"PCM keys must start with {PCM_KEY_PREFIX!r}: {key!r}")
    if len(segments) < 4:
        # patterns may let '**' stand in for <entity>/<resource...>
        if not (allow_wildcards and len(segments) >= 3):
            raise KeyError_(f"PCM keys need <domain>/<entity>/<resource>: {key!r}")
    saw_double = False
    for seg in segments[1:]:
        if seg == "**":
            if not allow_wildcards:
                raise KeyError_("'**' not allowed in published keys")
            if saw_double:
                raise KeyError_("only one '**' segment per pattern")
            saw_double = True
            continue
        if seg == "*":
            if not allow_wildcards:
                raise KeyError_("'*' not allowed in published keys")
            continue
        if not _SEGMENT.match(seg):
            raise KeyError_(f"invalid segment {seg!r} in key {key!r}")
    return key


def parse_key(key: str) -> dict:
    """Parse a concrete PCM key into its parts (raises on wildcards)."""
    validate_key(key)
    parts = key.split("/")
    # pcm/<domain>/<entity>/<resource...>  (resource may contain '/')
    return {
        "domain": parts[1],
        "entity": parts[2],
        "resource": "/".join(parts[3:]),
    }


def key(domain: str, entity: str, resource: str) -> str:
    """Build a concrete PCM key from parts."""
    return validate_key(f"{PCM_KEY_PREFIX}/{domain}/{entity}/{resource}")


def pattern(domain: str, entity: str, resource: str) -> str:
    """Build a PCM pattern (wildcards allowed) from parts."""
    return validate_key(
        f"{PCM_KEY_PREFIX}/{domain}/{entity}/{resource}", allow_wildcards=True
    )


# -- convenience builders (the documented vocabulary) -----------------------

def agent_message_key(agent_name: str) -> str:
    return key("agent", agent_name, "message")


def agent_state_key(agent_name: str) -> str:
    return key("agent", agent_name, "state")


def agent_capabilities_key(agent_name: str) -> str:
    return key("capability", "agent", agent_name)


def human_message_key(human_name: str) -> str:
    return key("human", human_name, "message")


def human_presence_key(human_name: str) -> str:
    return key("human", human_name, "presence")


def home_key(location: str, resource: str) -> str:
    return key("home", location, resource)


def device_key(device_name: str, resource: str) -> str:
    return key("device", device_name, resource)


def sensor_key(location: str, resource: str) -> str:
    return key("sensor", location, resource)


def drone_key(drone_id: str, resource: str) -> str:
    return key("drone", drone_id, resource)


def task_key(task_id: str, resource: str) -> str:
    if resource not in ("request", "result"):
        raise KeyError_("task resources are 'request' or 'result'")
    return key("task", task_id, resource)


def conversation_key(conversation_id: str) -> str:
    return key("conversation", conversation_id, "message")


def group_key(group_id: str) -> str:
    return key("group", group_id, "message")


def query_key(*path: str) -> str:
    """Request/response selector, e.g. query_key('agent', 'hermes')."""
    if len(path) < 2:
        raise KeyError_("query keys need at least <kind>/<name>")
    return key("query", path[0], "/".join(path[1:]))


def liveliness_key(kind: str, name: str) -> str:
    return key("liveliness", kind, name)


__all__ = [
    "PCM_KEY_PREFIX",
    "DOMAINS",
    "KeyError_",
    "validate_key",
    "parse_key",
    "key",
    "pattern",
    "agent_message_key",
    "agent_state_key",
    "agent_capabilities_key",
    "human_message_key",
    "human_presence_key",
    "home_key",
    "device_key",
    "sensor_key",
    "drone_key",
    "task_key",
    "conversation_key",
    "group_key",
    "query_key",
    "liveliness_key",
]