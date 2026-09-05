# -*- coding: utf-8 -*-
"""Configuration for the Hermes integration."""
from __future__ import annotations

import os
from pathlib import Path


DEFAULT_AGENT_NAME = os.environ.get("PCM_HERMES_NAME", "Panpsychic Cyborg Multitude")
DEFAULT_AGENT_ROLE = os.environ.get("PCM_HERMES_ROLE", "knowledge_steward")
DEFAULT_LANGUAGES = tuple(
    x.strip() for x in os.environ.get("PCM_HERMES_LANGUAGES", "English,Finnish").split(",")
    if x.strip()
)


def memory_path(tribe_dir: str, agent_name: str) -> Path:
    """Separate individual-memory path for one Hermes agent."""
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in agent_name).strip("-")
    root = Path(tribe_dir) / "agents"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{safe or 'agent'}.memory.json"
