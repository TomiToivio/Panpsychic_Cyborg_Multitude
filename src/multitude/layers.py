# -*- coding: utf-8 -*-
"""Agent layers: per-node state across the six layers of a human-like agent.

The six-layer model (whitepaper s.4) says every agent - biological,
technological, or mixed - is described along six layers:

* physical    - location in space (GPS or label), environment; also
              relevant for IoT devices and unembodied tech nodes
* biological  - flesh and its needs: sleep, hunger, mood, the ape in
              human agents; later non-human nodes (dogs, chimpanzees)
* social      - the tribe plus wider Castellsian networks and Luhmannian
              systems; designed to be subdivided later
* linguistic  - languages spoken and special vocabularies known
* psychic     - the psyche of conscious agents (Faggin's Quantum
              Information Panpsychism is the working model)
* cybernetic  - connection to the network: interface mode, links, runtime;
              text interfaces today, BCI eventually

Architecture (fits the kernel's event sourcing):

* Current state of a member's layers lives in ``Member.profile``
  (typed ``AgentProfile`` in models.py).
* Every change is an appended ``layer_recorded`` event; replaying the
  log rebuilds the profile. History belongs to the log, never lost.
* Records are self-reported by default; ``reported_by`` records who
  observed. A node's layers may be reported by other members.
* Fields not in the typed vocabularies are rejected, so the layer
  vocabulary stays clean; free text goes in ``data`` (stored as notes).
"""
from __future__ import annotations

from typing import Any

from multitude.models import AgentProfile, Layer, Member, NodeKind, now_iso


class LayerError(Exception):
    """Invalid layer record (unknown layer, unknown field, bad value)."""


# Typed vocabulary per layer (mirrors models.py; "data" is the escape hatch).
VALID_KEYS: dict[Layer, set[str]] = {
    Layer.PHYSICAL: {"location_label", "gps", "environment", "notes"},
    Layer.BIOLOGICAL: {
        "is_biological", "species", "sleep_state", "hunger_state",
        "mood", "needs", "notes",
    },
    Layer.SOCIAL: {"tribe_role", "close_ties", "wider_networks", "systems", "notes"},
    Layer.LINGUISTIC: {"languages", "vocabularies", "preferred_language", "notes"},
    Layer.PSYCHIC: {"is_conscious", "state", "valence", "attention", "notes"},
    Layer.CYBERNETIC: {
        "interface_mode", "network_links", "devices", "model_runtime", "notes",
    },
}

# Friendly aliases accepted in --set key=value pairs.
ALIASES: dict[str, str] = {
    "location": "location_label",
    "sleep": "sleep_state",
    "hunger": "hunger_state",
    "tribe": "tribe_role",
    "interface": "interface_mode",
    "languages": "languages",
    "special_vocabularies": "vocabularies",
}


def normalize_layer_name(name: str) -> Layer:
    low = name.strip().lower()
    if low not in Layer._value2member_map_:
        raise LayerError(
            f"unknown layer '{name}' - valid: {sorted(l.value for l in Layer)}"
        )
    return Layer(low)


def normalize_changes(layer: Layer, changes: dict[str, Any]) -> dict[str, Any]:
    """Map aliases, validate keys and basic value shapes for one layer."""

    def to_list(value: Any) -> list[str]:
        if isinstance(value, str):
            return [value]
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        raise LayerError(f"expected a string or list, got: {value!r}")

    out: dict[str, Any] = {}
    valid = VALID_KEYS[layer]
    for key, val in changes.items():
        k = ALIASES.get(key, key)
        if k == "data":
            k = "notes"
        # coordinate pair -> gps: handled as one unit before the vocabulary
        # check, so lat/lon (and a gps dict) never trip the valid-key test
        if layer == Layer.PHYSICAL and k in ("lat", "lon", "gps"):
            lat = changes.get("lat", (changes.get("gps") or {}).get("lat"))
            lon = changes.get("lon", (changes.get("gps") or {}).get("lon"))
            if lat is None or lon is None:
                raise LayerError("physical records need both lat and lon")
            try:
                lat, lon = float(lat), float(lon)
            except (TypeError, ValueError):
                raise LayerError("lat/lon must be numbers")
            if not (-90.0 <= lat <= 90.0):
                raise LayerError(f"lat out of range: {lat}")
            if not (-180.0 <= lon <= 180.0):
                raise LayerError(f"lon out of range: {lon}")
            out["gps"] = {"lat": lat, "lon": lon}
            continue
        if k not in valid:
            raise LayerError(
                f"unknown field '{key}' for {layer.value} layer - "
                f"valid: {sorted(valid)}"
            )
        if k in ("languages", "vocabularies", "needs", "close_ties",
                 "wider_networks", "systems", "network_links", "devices"):
            out[k] = to_list(val)
        elif layer == Layer.BIOLOGICAL and k == "is_biological":
            out[k] = bool(val)
        elif layer == Layer.PSYCHIC and k == "is_conscious":
            if val is None:
                out[k] = None
            else:
                out[k] = bool(val)
        else:
            out[k] = str(val)
    if not out:
        raise LayerError("empty layer record")
    return out


def default_seeds(member: Member) -> dict[str, dict[str, Any]]:
    """Starter readings a node gets at join time (as layer_recorded events).

    Minimal on purpose. Biological nodes are marked conscious (the ape
    starts awake); technological nodes record that they are distributed
    rather than embodied, and their consciousness is left unknown --
    Faggin's panpsychism permits machine consciousness but does not
    assert it.
    """
    if member.kind == NodeKind.BIOLOGICAL:
        return {
            "psychic": {"is_conscious": True, "state": "awake",
                        "notes": "human biological node - the ape is present"},
        }
    return {
        "physical": {"notes": "distributed: runs on networked hardware, "
                              "no single physical location"},
    }


def apply_to_profile(profile: AgentProfile, layer: Layer, changes: dict[str, Any]) -> None:
    """Merge normalized changes into the member's typed profile."""
    sub = getattr(profile, layer.value)
    data = sub.model_dump()
    for key, val in changes.items():
        if isinstance(val, list) and isinstance(data.get(key), list):
            seen = set(data[key])
            data[key] = data[key] + [v for v in val if v not in seen]
        else:
            data[key] = val
    replacement = type(sub).model_validate(data)
    setattr(profile, layer.value, replacement)


def layer_recorded_payload(
    member: Member,
    layer: Layer,
    changes: dict[str, Any],
    reported_by: str,
    visible: bool = True,
) -> dict[str, Any]:
    """Build payload for a layer_recorded event (and apply to profile)."""
    clean = normalize_changes(layer, changes)
    apply_changes = dict(clean)
    apply_layer_to_profile(member.profile, layer, apply_changes)
    return {
        "member_id": member.id,
        "layer": layer.value,
        "changes": clean,
        "reported_by": reported_by,
        "visible": visible,
    }


def apply_layer_to_profile(
    profile: AgentProfile, layer: Layer, changes: dict[str, Any]
) -> None:
    """Alias kept for clarity in replay paths."""
    apply_to_profile(profile, layer, changes)


def replay_layer_record(
    member: Member, payload: dict[str, Any]
) -> None:
    """Replay a layer_recorded event into member state."""
    try:
        layer = Layer(payload["layer"])
        clean = normalize_changes(layer, payload.get("changes", {}))
        apply_to_profile(member.profile, layer, clean)
    except (LayerError, KeyError):
        return  # future vocabulary: old nodes skip what they cannot parse


def format_member_layers(member: Member) -> str:
    """Readable one-line-per-layer summary for CLI output."""
    lines: list[str] = []
    for layer in Layer:
        sub = getattr(member.profile, layer.value)
        filled = {
            k: v
            for k, v in sub.model_dump().items()
            if v not in (None, [], "", {})
        }
        if not filled:
            continue
        parts: list[str] = []
        for k, v in filled.items():
            if isinstance(v, list):
                parts.append(f"{k}={','.join(map(str, v))}")
            elif k == "notes":
                parts.append(str(v))
            else:
                parts.append(f"{k}={v}")
        lines.append(f"  {layer.value}: {'; '.join(parts)}")
    return "\n".join(lines) if lines else "  (no layer data)"