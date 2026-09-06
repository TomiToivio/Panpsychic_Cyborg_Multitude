# -*- coding: utf-8 -*-
"""Optional configuration for the Telegram adapter and gateway."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class TelegramConfigError(RuntimeError):
    """Telegram configuration is missing or invalid."""


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_name: str = "Panpsychic Cyborg Multitude"
    bot_username: str = "@panpsychic_bot"
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    api_base: str = "https://api.telegram.org"
    mention_names: tuple[str, ...] = (
        "panpsychic multitude",
        "cyborg multitude",
        "@panpsychic_bot",
        "panpsychic_bot",
        "open natural intelligence",
        "@open_natural_intelligence_bot",
    )
    allow_remote_models: bool = True
    poll_timeout: int = 30
    ambient: bool = True
    ambient_cooldown_s: float = 300.0
    identities: dict[str, Any] = field(default_factory=dict)
    chats: dict[str, str] = field(default_factory=dict)
    state_path: str = ""

    def token(self) -> str:
        return os.environ.get(self.bot_token_env, "")

    def mapped_agent(self, user_id: str) -> str | None:
        entry = self.identities.get(user_id)
        if isinstance(entry, str):
            return entry
        if isinstance(entry, dict):
            agent_name = entry.get("agent_name") or entry.get("agent_id")
            return str(agent_name) if agent_name else None
        return None


def default_config_path() -> Path:
    override = os.environ.get("PCM_TELEGRAM_CONFIG")
    if override:
        return Path(override)
    return Path("config") / "telegram.json"


def load_config(path: str | None = None) -> TelegramConfig:
    cfg = TelegramConfig(
        enabled=_env_flag("PCM_TELEGRAM_ENABLED", False),
        bot_name=os.environ.get("PCM_TELEGRAM_BOT_NAME", "Panpsychic Cyborg Multitude"),
        bot_username=os.environ.get("PCM_TELEGRAM_BOT_USERNAME", "@panpsychic_bot"),
        bot_token_env=os.environ.get("PCM_TELEGRAM_BOT_TOKEN_ENV", "TELEGRAM_BOT_TOKEN"),
        api_base=os.environ.get("PCM_TELEGRAM_API_BASE", "https://api.telegram.org"),
        mention_names=tuple(
            name.strip().lower()
            for name in os.environ.get(
                "PCM_TELEGRAM_MENTIONS",
                "Panpsychic Cyborg Multitude,panpsychic multitude,cyborg multitude,@panpsychic_bot,panpsychic_bot,Ai (愛),Open Natural Intelligence,@open_natural_intelligence_bot",
            ).split(",")
            if name.strip()
        ),
        allow_remote_models=_env_flag("PCM_TELEGRAM_ALLOW_REMOTE_MODELS", True),
        poll_timeout=int(os.environ.get("PCM_TELEGRAM_POLL_TIMEOUT", "30")),
        ambient=_env_flag("PCM_TELEGRAM_AMBIENT", True),
        ambient_cooldown_s=float(os.environ.get("PCM_TELEGRAM_AMBIENT_COOLDOWN", "300")),
        state_path=os.environ.get("PCM_TELEGRAM_STATE", ""),
    )
    config_path = Path(path) if path else default_config_path()
    if not config_path.exists():
        return cfg
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    data = raw.get("telegram", raw)
    if "enabled" in data:
        cfg.enabled = bool(data["enabled"])
    if "bot_name" in data:
        cfg.bot_name = str(data["bot_name"])
    if "bot_username" in data:
        cfg.bot_username = str(data["bot_username"])
    if "bot_token_env" in data:
        cfg.bot_token_env = str(data["bot_token_env"])
    if "api_base" in data:
        cfg.api_base = str(data["api_base"])
    if "allow_remote_models" in data:
        cfg.allow_remote_models = bool(data["allow_remote_models"])
    if "poll_timeout" in data:
        cfg.poll_timeout = int(data["poll_timeout"])
    if "ambient" in data:
        cfg.ambient = bool(data["ambient"])
    if "ambient_cooldown_s" in data:
        cfg.ambient_cooldown_s = float(data["ambient_cooldown_s"])
    if data.get("mention_names"):
        cfg.mention_names = tuple(str(x).strip().lower() for x in data["mention_names"] if str(x).strip())
    cfg.identities = {str(k): v for k, v in dict(data.get("identities", {})).items()}
    cfg.chats = {str(k): str(v) for k, v in dict(data.get("chats", {})).items()}
    cfg.state_path = str(data.get("state_path") or cfg.state_path)
    if "PCM_TELEGRAM_ENABLED" in os.environ:
        cfg.enabled = _env_flag("PCM_TELEGRAM_ENABLED", cfg.enabled)
    # Guard against a raw token pasted into bot_token_env (name must look
    # like an env var NAME, not the secret itself).
    if cfg.bot_token_env and not cfg.bot_token_env.replace("_", "").isalnum():
        raise TelegramConfigError(
            "config bot_token_env must name an environment variable "
            "(e.g. TELEGRAM_BOT_TOKEN), not contain the token itself"
        )
    return cfg


def load_telegram_settings(rhizome_dir: str) -> TelegramConfig:
    cfg = load_config()
    if not cfg.state_path:
        cfg.state_path = str(Path(rhizome_dir) / "telegram.state.json")
    return cfg
