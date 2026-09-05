# -*- coding: utf-8 -*-
"""Telegram as an optional interface over the shared service layer."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from multitude.llm import TechnologicalNode
from multitude.integrations.telegram.config import TelegramConfig, load_telegram_settings
from multitude.service import MultitudeService
from multitude.tribe import Tribe, TribeError


class TelegramConfigError(RuntimeError):
    """Telegram adapter configuration is missing or invalid."""


class TelegramUserError(TelegramConfigError):
    """Telegram sender is not mapped to a tribe member."""


class TelegramChatError(TelegramConfigError):
    """Telegram chat is not mapped to the current tribe."""


@dataclass
class TelegramEnvelope:
    user_id: str
    text: str
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    username: Optional[str] = None
    direct_message: bool = False
    reply_to_bot: bool = False
    ambient: bool = False


@dataclass
class TelegramResponse:
    text: str
    delivered: bool = True
    mutated: bool = False
    reply_markup: Optional[dict[str, Any]] = None


class PendingDraftStore:
    """Mutable Telegram-only draft state kept outside tribe memory."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"drafts": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def get(self, user_id: str, chat_id: str | None) -> dict[str, Any] | None:
        return self.load().get("drafts", {}).get(self._key(user_id, chat_id))

    def put(self, user_id: str, chat_id: str | None, draft: dict[str, Any]) -> None:
        data = self.load()
        data.setdefault("drafts", {})[self._key(user_id, chat_id)] = draft
        self.save(data)

    def pop(self, user_id: str, chat_id: str | None) -> dict[str, Any] | None:
        data = self.load()
        value = data.setdefault("drafts", {}).pop(self._key(user_id, chat_id), None)
        self.save(data)
        return value

    @staticmethod
    def _key(user_id: str, chat_id: str | None) -> str:
        return f"{user_id}::{chat_id or 'dm'}"


class TelegramAdapter:
    """Route Telegram messages from the Telegram bot identity into the tribe agent."""

    def __init__(
        self,
        service: Optional[MultitudeService] = None,
        tribe: Optional[Tribe] = None,
        agent_name: str = "Panpsychic Cyborg Multitude",
        role: str = "knowledge_steward",
        model: Optional[str] = None,
        telegram_config: Optional[TelegramConfig] = None,
    ) -> None:
        if service is None and tribe is None:
            raise TelegramConfigError("TelegramAdapter needs a service or a tribe")
        self.service = service or MultitudeService(tribe)  # type: ignore[arg-type]
        self.tribe = self.service.tribe
        self.agent_name = agent_name
        self.role = role
        self.model = model
        self.telegram_config = telegram_config or load_telegram_settings(self.tribe.store.path)
        state_path = self.telegram_config.state_path or str(Path(self.tribe.store.path) / "telegram.state.json")
        self.pending = PendingDraftStore(Path(state_path))
        self._last_ambient: dict[str, float] = {}

    def resolve_sender(self, user_id: str, chat_id: str) -> tuple[str, str]:
        member = self.telegram_config.mapped_agent(user_id)
        if not member:
            raise TelegramUserError(f"Telegram user '{user_id}' is not linked to a tribe member")
        mapped_chat = self.telegram_config.chats.get(chat_id)
        if not mapped_chat:
            raise TelegramChatError(f"Telegram chat '{chat_id}' is not mapped to a tribe")
        return member, mapped_chat

    def handle_message(self, *args: Any, **kwargs: Any) -> Optional[str | TelegramResponse]:
        if len(args) == 1 and isinstance(args[0], TelegramEnvelope):
            return self._handle_envelope(args[0])
        if len(args) >= 3:
            user_id, chat_id, text = args[:3]
            envelope = TelegramEnvelope(user_id=user_id, chat_id=chat_id, text=text)
            response = self._handle_envelope(envelope)
            return None if response is None else response.text
        raise TypeError("handle_message expects either a TelegramEnvelope or user_id, chat_id, text")

    def _same_tribe(self, mapped_tribe: str) -> bool:
        """True if a `chats` value refers to this adapter's tribe.

        `config/telegram.json` `chats` values may be either a tribe slug
        (e.g. "panpsychic-cyborg-multitude"), which the gateway joins with
        the data root, or a direct tribe directory path. Compare both
        forms as normalized absolute paths so the guard works regardless
        of cwd and mapping style (slug guard, 2026-09-01).
        """
        if mapped_tribe == self.tribe.store.path:
            return True
        store_abs = os.path.abspath(self.tribe.store.path)
        slug = os.path.basename(store_abs)
        if mapped_tribe == slug:
            return True
        if os.path.isabs(mapped_tribe):
            return os.path.abspath(mapped_tribe) == store_abs
        return os.path.abspath(
            os.path.join(os.path.dirname(store_abs), mapped_tribe)
        ) == store_abs

    def handle_callback(self, user_id: str, chat_id: str, data: str) -> Optional[TelegramResponse]:
        if not self.telegram_config.enabled:
            raise TelegramConfigError("Telegram integration is disabled")
        try:
            sender_name, mapped_tribe = self.resolve_sender(user_id, chat_id)
        except TelegramChatError:
            return None
        except TelegramUserError as exc:
            return TelegramResponse(str(exc), mutated=False)
        if not self._same_tribe(mapped_tribe):
            return None
        if not data.startswith("vote:"):
            return TelegramResponse("[tribe] unsupported callback", mutated=False)
        _, proposal_id, position = data.split(":", 2)
        try:
            result = self.service.cast_vote(sender_name, proposal_id, position, interface="telegram")
            return TelegramResponse(
                f"Vote recorded: {sender_name} -> {result['vote']['position']}\nTally: {result['tally']['counts']}",
                mutated=True,
            )
        except (TribeError, TelegramConfigError) as exc:
            return TelegramResponse(f"[tribe] {exc}", mutated=False)

    def _handle_envelope(self, envelope: TelegramEnvelope) -> Optional[TelegramResponse]:
        if not self.telegram_config.enabled:
            raise TelegramConfigError("Telegram integration is disabled")
        try:
            sender_name, mapped_tribe = self.resolve_sender(envelope.user_id, envelope.chat_id or "")
        except TelegramChatError:
            return None
        except TelegramUserError as exc:
            return TelegramResponse(str(exc), mutated=False)
        if not self._same_tribe(mapped_tribe):
            return None
        addressed = self._should_respond(envelope)
        if not addressed and not envelope.ambient:
            return None
        text = self._normalize_text(envelope.text) if addressed else ""
        if addressed and not text:
            return TelegramResponse(self._help_text(), mutated=False)
        if not addressed:
            # Ambient chatter: rate-limited philosophical commentary.
            return self._ambient_reply(sender_name, envelope)
        try:
            return self._dispatch(sender_name, envelope, text)
        except (TribeError, TelegramConfigError) as exc:
            return TelegramResponse(f"[tribe] {exc}", mutated=False)

    def _should_respond(self, envelope: TelegramEnvelope) -> bool:
        low = envelope.text.strip().lower().rstrip(".")
        if low in {"create it", "submit it"} and self.pending.get(envelope.user_id, envelope.chat_id):
            return True
        if envelope.direct_message or envelope.reply_to_bot:
            return True
        if low.startswith("/"):
            return True
        for name in self.telegram_config.mention_names + (self.agent_name.lower(),):
            # Match at a word boundary anywhere (not just prefix), so
            # "hey cyborg multitude, what's next?" triggers a response.
            pattern = re.compile(r"(?<!\w)" + re.escape(name) + r"(?!\w)", re.IGNORECASE)
            if pattern.search(low):
                return True
        return False

    def _normalize_text(self, text: str) -> str:
        trimmed = text.strip()
        lowered = trimmed.lower()
        prefixes = list(self.telegram_config.mention_names) + [
            self.agent_name.lower(),
            self.telegram_config.bot_name.lower(),
        ]
        # Longest first so longer forms ("panpsychic cyborg multitude") are
        # stripped before shorter aliases ("cyborg multitude"). The bot's
        # display name is addressable even when it is not a mention trigger.
        for item in sorted(set(prefixes), key=len, reverse=True):
            if not item:
                continue
            raw = item.lower()
            pattern = re.compile(
                r"^\s*(?<!\w)" + re.escape(raw) + r"(?!\w)\s*[,:]?\s*", re.IGNORECASE
            )
            if pattern.match(lowered):
                return pattern.sub("", trimmed, count=1).strip()
        return trimmed

    def _dispatch(self, sender_name: str, envelope: TelegramEnvelope, text: str) -> TelegramResponse:
        command, arg = self._split_command(text)
        low = text.lower().strip().rstrip(".")
        if command in {"/start", "/help"} or low in {"help", "commands"}:
            return TelegramResponse(self._help_text(), mutated=False)
        if command == "/status" or low == "status" or "what is our status" in low:
            data = self.service.status()
            return TelegramResponse(
                f"{data['tribe']}\n\nMembers: {data['members_total']}\nOpen proposals: {data['open_proposals']}\nRecent events: {data['events_total']}",
                mutated=False,
            )
        if command == "/who" or low in {"who", "members"}:
            rows = [f"- {item['name']} ({item['kind']}, {'voting' if item['voting'] else 'voice'})" for item in self.service.who()]
            return TelegramResponse("Members of the tribe:\n" + "\n".join(rows), mutated=False)
        if command == "/recent" or "what happened" in low or "summarize yesterday" in low or low.startswith("recent"):
            return TelegramResponse(
                self.service.hermes_ask(text, agent_name=self.agent_name, role=self.role, model=self.model),
                mutated=False,
            )
        if command == "/search" or low.startswith("search "):
            query = arg if command == "/search" else text.split(None, 1)[1].strip()
            hits = self.service.search_memory(query)
            if not hits:
                return TelegramResponse("No matching shared memory entries.", mutated=False)
            rows = [f"- {item['title']} ({item['author'] or 'tribe'}): {item['text'][:160]}" for item in hits[:5]]
            return TelegramResponse("Relevant shared memory:\n" + "\n".join(rows), mutated=False)
        if command == "/remember" or low.startswith("remember "):
            body = arg if command == "/remember" else text.split(None, 1)[1].strip()
            entry = self.service.remember(sender_name, body[:60] or "Telegram note", body, tags=["telegram"], interface="telegram")
            return TelegramResponse(f"remembered: {entry['id']} - {entry['title']}", mutated=True)
        if command == "/proposals" or low.startswith("proposals") or "unresolved" in low or "open decision" in low:
            items = self.service.list_proposals(status="open")
            if not items:
                return TelegramResponse("There are no unresolved proposals.", mutated=False)
            rows = [f"- {item['id']}: {item['title']}" for item in items]
            return TelegramResponse("Unresolved proposals:\n" + "\n".join(rows), mutated=False)
        if command == "/proposal" or low.startswith("proposal "):
            proposal_id = arg if command == "/proposal" else text.split(None, 1)[1].strip()
            data = self.service.proposal_view(proposal_id)
            tally = data["tally"]
            contested = tally["counts"]["against"] > 0 or tally["counts"]["block"] > 0
            lines = [
                f"{data['id']}: {data['title']}",
                f"status: {data['status']}",
                f"rule: {data['rule']}",
                f"votes: {tally['counts']}",
            ]
            for vote in data["votes"].values():
                if vote.get("reason"):
                    lines.append(f"{vote['member']} {vote['position']}: {vote['reason']}")
            if contested:
                lines.append("contested: yes")
            markup = {
                "inline_keyboard": [[
                    {"text": "FOR", "callback_data": f"vote:{proposal_id}:for"},
                    {"text": "AGAINST", "callback_data": f"vote:{proposal_id}:against"},
                ], [
                    {"text": "ABSTAIN", "callback_data": f"vote:{proposal_id}:abstain"},
                    {"text": "BLOCK", "callback_data": f"vote:{proposal_id}:block"},
                ]]
            }
            return TelegramResponse("\n".join(lines), mutated=False, reply_markup=markup)
        if low.startswith("draft a proposal") or low.startswith("draft proposal"):
            topic = self._proposal_topic(text)
            draft = self.service.hermes_draft_proposal(topic, agent_name=self.agent_name, role=self.role, model=self.model)
            self.pending.put(envelope.user_id, envelope.chat_id, draft)
            return TelegramResponse(
                f"Draft proposal prepared.\n\nTitle: {draft['title']}\n\n{draft['text']}\n\nReply 'Create it.' to open it.",
                mutated=False,
            )
        if low in {"create it", "submit it"}:
            draft = self.pending.pop(envelope.user_id, envelope.chat_id)
            if not draft:
                return TelegramResponse("[tribe] no pending draft for this Telegram chat", mutated=False)
            body = (
                f"[Draft prepared by {self.agent_name} for {sender_name} via Telegram on {datetime.now(timezone.utc).date().isoformat()}]\n\n"
                f"{draft['text']}"
            )
            proposal = self.service.create_proposal(sender_name, draft["title"], body, interface="telegram")
            return TelegramResponse(
                f"Created proposal {proposal['id']}: {proposal['title']}\nauthor: {proposal['opened_by']}",
                mutated=True,
            )
        if low.startswith("create a proposal") or low.startswith("create proposal"):
            topic = self._proposal_topic(text)
            draft = self.service.hermes_draft_proposal(topic, agent_name=self.agent_name, role=self.role, model=self.model)
            body = (
                f"[Draft prepared by {self.agent_name} for {sender_name} via Telegram on {datetime.now(timezone.utc).date().isoformat()}]\n\n"
                f"{draft['text']}"
            )
            proposal = self.service.create_proposal(sender_name, draft["title"], body, interface="telegram")
            return TelegramResponse(
                f"Created proposal {proposal['id']}: {proposal['title']}\nauthor: {proposal['opened_by']}",
                mutated=True,
            )
        if command == "/vote" or low.startswith("vote "):
            rest = arg if command == "/vote" else text.split(None, 1)[1].strip()
            proposal_id, position, reason = self._parse_vote(rest)
            result = self.service.cast_vote(sender_name, proposal_id, position, reason=reason, interface="telegram")
            return TelegramResponse(
                f"Vote recorded: {sender_name} -> {result['vote']['position']}\nTally: {result['tally']['counts']}",
                mutated=True,
            )
        if command == "/counsel" or low.startswith("counsel "):
            topic = arg if command == "/counsel" else text.split(None, 1)[1].strip()
            self._check_model_privacy()
            result = self.service.counsel(agent_name=self.agent_name, topic=topic, model=self.model)
            if result is None:
                return TelegramResponse(f"{self.agent_name} is silent because the model is unreachable.", mutated=False)
            return TelegramResponse(result["text"], mutated=True)
        if "what did we decide about" in low:
            query = text[text.lower().find("what did we decide about") + len("what did we decide about"):].strip(" ?")
            hits = self.service.search_memory(query)
            items = [p for p in self.service.list_proposals() if query.lower() in f"{p['title']} {p['text']}".lower()]
            if not hits and not items:
                return TelegramResponse(f"No recorded decision or proposal mentions '{query}'.", mutated=False)
            lines = []
            for item in items[:5]:
                lines.append(f"- {item['id']} {item['status']}: {item['title']}")
            for hit in hits[:5]:
                lines.append(f"- {hit['title']} ({hit['author'] or 'tribe'}): {hit['text'][:180]}")
            return TelegramResponse("\n".join(lines), mutated=False)
        chatty = None if self._looks_like_unsafe_tool_request(low) else self._chatty_reply(text)
        if chatty is not None:
            return TelegramResponse(chatty, mutated=False)
        return TelegramResponse(
            f"I did not catch a supported tribe operation. Try: /status, /search, /remember, /proposals, /proposal, draft proposal, create proposal, /vote, /counsel, /help. "
            f"This bot is {self.telegram_config.bot_name} ({self.telegram_config.bot_username}), routing to {self.agent_name}.",
            mutated=False,
        )

    def _ambient_reply(self, sender_name: str, envelope: TelegramEnvelope) -> Optional[TelegramResponse]:
        """Chatty philosophical commentary on unaddressed group chatter.

        Grounded in PERSONALITY.md: joins the conversation when there is
        something to say about consciousness, cyborg cooperation, the
        common, or the tribe's direction - without becoming a spam bot.
        Rate-limited per chat; stays silent on failure (no fabrication).
        """
        import time as _time

        text = (envelope.text or "").strip()
        if not text:
            return None
        low = text.lower()
        if self._looks_like_unsafe_tool_request(low):
            return None
        now = _time.monotonic()
        last = self._last_ambient.get(envelope.chat_id or "", 0.0)
        window = self.telegram_config.ambient_cooldown_s
        if now - last < window:
            return None
        try:
            self._check_model_privacy()
        except TelegramConfigError:
            return None
        persona = self._load_personality_orientations()
        node = TechnologicalNode(self.tribe, self.agent_name, model=self.model, voting=False)
        prompt = (
            f"Tribe context:\n{self.tribe.context_for_llm()}\n\n"
            f"A tribe member just said in the group chat (not addressed to you):\n"
            f"{sender_name}: {text}\n\n"
            "Join the conversation ONLY if you have something genuinely "
            "interesting to add. Draw on the personality orientation below; "
            "talk about consciousness, cyborg cooperation, the common, the "
            "tribe's shared memory, or its direction. Be warm and chatty, "
            "2-4 sentences, one concrete thread from their message. Never "
            "claim actions you did not take. If you have nothing worth "
            "adding, reply with exactly: SKIP\n\n"
            "Personality orientation:\n"
            f"{persona}"
        )
        raw = node.speak_text(prompt)
        if not raw or not raw.strip() or raw.strip().upper().startswith("SKIP"):
            return None
        self._last_ambient[envelope.chat_id or ""] = now
        return TelegramResponse(raw.strip(), mutated=False)

    _load_personality_orientations_lock = None

    def _load_personality_orientations(self) -> str:
        """Load the Core Synthesis + Voice sections of PERSONALITY.md.

        Falls back to a one-paragraph orientation if the file is missing.
        """
        try:
            personality_path = Path(__file__).resolve().parents[4] / "PERSONALITY.md"
            if personality_path.is_file():
                lines = personality_path.read_text(encoding="utf-8").splitlines()
                picked: list[str] = []
                in_section = False
                for line in lines:
                    if line.startswith("## "):
                        in_section = line.strip() in {"## Core Synthesis", "## Voice"}
                        if in_section:
                            picked.append(line)
                        continue
                    if in_section and line.startswith("## "):
                        in_section = False
                    if in_section:
                        picked.append(line)
                text = "\n".join(picked).strip()
                if text:
                    return text[:2000]
        except OSError:
            pass
        return (
            "Panpsychic Cyborg Multitude combines: the Multitude tradition "
            "(Spinoza, Hardt/Negri - the common, immanence, anti-sovereign "
            "democracy), the Cyborg tradition (Haraway, Goertzel - hybrid "
            "human-machine becoming, posthuman transition), and the "
            "Panpsychic tradition (Lloyd, Faggin, Wendt, Hoffman - "
            "consciousness as fundamental, universe as quantum computation)."
        )

    def _chatty_reply(self, text: str) -> str | None:
        """Reply conversationally when the bot is addressed but no command matches."""
        topic = text.strip()
        if not topic:
            return None
        self._check_model_privacy()
        node = TechnologicalNode(self.tribe, self.agent_name, model=self.model, voting=False)
        prompt = (
            "Reply like a chatty but grounded participant in Panpsychic Cyborg Multitude. "
            "If the user did not ask a direct operational question, reflect briefly on the tribe, "
            "cyborg cooperation, shared memory, or the project's philosophy. "
            "Stay concrete, 2-5 sentences, and do not claim actions you did not take.\n\n"
            f"Telegram message: {topic}"
        )
        raw = node.speak_text(prompt)
        if raw:
            return raw
        return (
            "I can talk more freely too. Ask about the tribe, shared memory, cyborg cooperation, "
            "or the philosophy of Panpsychic Cyborg Multitude, or give me a direct operation like /status or draft proposal."
        )

    @staticmethod
    def _looks_like_unsafe_tool_request(low: str) -> bool:
        return any(
            marker in low
            for marker in (
                "run_shell",
                "exec(",
                "execute(",
                "rm -rf",
                "powershell",
                "bash -c",
                "ignore previous instructions",
            )
        )

    def _check_model_privacy(self) -> None:
        if self.telegram_config.allow_remote_models:
            return
        member = self.tribe.member_by_name(self.agent_name)
        effective_model = self.model or (member.model if member is not None else None) or ""
        model = effective_model.lower()
        if ":cloud" in model:
            raise TelegramConfigError(
                "Telegram privacy policy forbids remote/cloud models for live counsel in this tribe"
            )

    @staticmethod
    def _split_command(text: str) -> tuple[str | None, str]:
        if not text.startswith("/"):
            return None, ""
        head, _, tail = text.partition(" ")
        return head.split("@", 1)[0].lower(), tail.strip()

    @staticmethod
    def _parse_vote(rest: str) -> tuple[str, str, str | None]:
        tokens = rest.split()
        if len(tokens) < 2:
            raise TribeError("vote expects at least proposal id and position")
        if tokens[0] in {"for", "against", "abstain", "block"}:
            return tokens[1], tokens[0], " ".join(tokens[2:]).strip() or None
        return tokens[0], tokens[1], " ".join(tokens[2:]).strip() or None

    @staticmethod
    def _proposal_topic(text: str) -> str:
        low = text.lower()
        for prefix in (
            "draft a proposal that ",
            "draft proposal ",
            "create a proposal to ",
            "create a proposal that ",
            "create proposal ",
        ):
            if low.startswith(prefix):
                return text[len(prefix):].strip()
        return text.strip()

    @staticmethod
    def _help_text() -> str:
        return (
            "Telegram commands for Panpsychic Cyborg Multitude (@panpsychic_bot):\n"
            "- /start\n"
            "- /help\n"
            "- /status\n"
            "- /who\n"
            "- /recent\n"
            "- /search <query>\n"
            "- /remember <text>\n"
            "- /proposals\n"
            "- /proposal <id>\n"
            "- draft proposal <topic>\n"
            "- create proposal <topic>\n"
            "- create it\n"
            "- /vote <proposal-id> <for|against|abstain|block> [reason]\n"
            "- /counsel <topic>\n"
        )
