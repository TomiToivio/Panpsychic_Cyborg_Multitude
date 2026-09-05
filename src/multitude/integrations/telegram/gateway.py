# -*- coding: utf-8 -*-
"""TelegramGateway: bridge Telegram Bot API <-> the TelegramAdapter."""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Optional

from multitude import config as kernconf
from multitude.http_json import request_json
from multitude.integrations.telegram.adapter import TelegramAdapter, TelegramEnvelope
from multitude.integrations.telegram.config import TelegramConfig, load_config
from multitude.service import MultitudeService
from multitude.store import TribeStore
from multitude.tribe import Tribe


class TelegramGateway:
    """Long-poll Telegram updates and drive one adapter per mapped chat."""

    def __init__(
        self,
        cfg: TelegramConfig,
        adapters: Optional[dict[str, tuple[TelegramAdapter, str]]] = None,
    ) -> None:
        self.cfg = cfg
        self.token = cfg.token()
        if not self.token:
            raise SystemExit(
                f"{cfg.bot_token_env} not set - keep the bot token outside Git and load it from the environment"
            )
        self.base_url = f"{cfg.api_base.rstrip('/')}/bot{self.token}"
        self.adapters = adapters or {}
        self.offset = 0
        self._seen_chats: set[str] = set()

    def send(self, chat_id: str, text: str, reply_markup: Optional[dict[str, Any]] = None) -> bool:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        status, data = request_json(
            "POST",
            f"{self.base_url}/sendMessage",
            payload=payload,
            timeout=30,
        )
        ok = status == 200 and bool((data or {}).get("ok", False))
        if not ok:
            code = "unreachable" if status is None else str(status)
            print(f"[telegram] send failed: HTTP {code}")
            return False
        print(f"[telegram] sent reply to {chat_id} ({len(text)} chars)")
        return True

    def poll_once(self) -> int:
        status, payload = request_json(
            "GET",
            f"{self.base_url}/getUpdates",
            params={
                "timeout": self.cfg.poll_timeout,
                "offset": self.offset,
                "allowed_updates": ["message", "callback_query"],
            },
            timeout=self.cfg.poll_timeout + 10,
        )
        if status != 200 or not payload or not payload.get("ok"):
            return 0
        updates = payload.get("result", [])
        handled = 0
        for update in updates:
            self.offset = max(self.offset, int(update.get("update_id", 0)) + 1)
            callback = update.get("callback_query")
            if callback:
                message = callback.get("message", {})
                chat_id = str((message.get("chat") or {}).get("id") or "")
                user_id = str((callback.get("from") or {}).get("id") or "")
                adapter = self.adapters.get(chat_id)
                if adapter is None:
                    continue
                reply = adapter[0].handle_callback(user_id, chat_id, callback.get("data", ""))
                if reply and self.send(chat_id, reply.text, reply.reply_markup):
                    handled += 1
                continue
            message = update.get("message") or update.get("edited_message")
            if not message:
                continue
            chat_id = str((message.get("chat") or {}).get("id") or "")
            chat_type = str((message.get("chat") or {}).get("type") or "")
            chat_title = str((message.get("chat") or {}).get("title") or "")
            user_id = str((message.get("from") or {}).get("id") or "")
            text = str(message.get("text") or "")
            if chat_id and chat_id not in self._seen_chats:
                label = f"{chat_type or 'unknown'} chat {chat_id}"
                if chat_title:
                    label += f" ({chat_title})"
                mapped = "mapped" if chat_id in self.adapters else "unmapped"
                print(f"[telegram] seen {label} [{mapped}]")
                self._seen_chats.add(chat_id)
            adapter = self.adapters.get(chat_id)
            if adapter is None:
                continue
            reply_to = message.get("reply_to_message") or {}
            reply_to_bot = str(((reply_to.get("from") or {}).get("is_bot"))).lower() == "true"
            reply = adapter[0].handle_message(
                TelegramEnvelope(
                    user_id=user_id,
                    chat_id=chat_id,
                    text=text,
                    message_id=str(message.get("message_id") or ""),
                    username=str((message.get("from") or {}).get("username") or ""),
                    direct_message=chat_type == "private",
                    reply_to_bot=reply_to_bot,
                    ambient=bool(adapter[0].telegram_config.ambient),
                )
            )
            if reply and self.send(chat_id, reply.text, reply.reply_markup):
                handled += 1
        return handled

    def run(self) -> None:
        print(f"[telegram] gateway polling {self.cfg.api_base} chats={list(self.cfg.chats)}")
        while True:
            try:
                self.poll_once()
            except KeyboardInterrupt:
                print("[telegram] gateway stopped")
                raise
            except Exception as exc:
                print(f"[telegram] poll error (retried): {exc!r}")
                time.sleep(2.0)


def build_gateway(cfg_path: Optional[str] = None) -> TelegramGateway:
    cfg = load_config(cfg_path)
    if not cfg.enabled:
        raise SystemExit("Telegram is disabled (config/telegram.json enabled=false or PCM_TELEGRAM_ENABLED=0)")
    adapters: dict[str, tuple[TelegramAdapter, str]] = {}
    for chat_id, tribe_ref in cfg.chats.items():
        candidate = os.path.join(kernconf.tribes_root(), tribe_ref)
        tribe_dir = candidate if os.path.isdir(candidate) else tribe_ref
        tribe = Tribe(TribeStore(tribe_dir))
        service = MultitudeService(tribe)
        adapters[str(chat_id)] = (TelegramAdapter(service=service, telegram_config=cfg), tribe_dir)
    return TelegramGateway(cfg, adapters)


def _load_repo_env() -> None:
    """Load .env from the repo root if present (token stays out of Git)."""
    env_file = Path(__file__).resolve().parents[4] / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    _load_repo_env()
    cfg = load_config()
    gateway = build_gateway()
    print(f"[telegram] chats mapped: {list(cfg.chats)}; identities: {len(cfg.identities)}")
    try:
        gateway.run()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
