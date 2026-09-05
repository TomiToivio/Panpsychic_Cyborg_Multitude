# -*- coding: utf-8 -*-
"""Hermes-based technological node for Panpsychic Cyborg Multitude."""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from multitude import config
from multitude.llm import OllamaClient
from multitude.store import TribeStore
from multitude.tribe import Tribe
from multitude.integrations.hermes.adapter import MultitudeHermesAdapter
from multitude.integrations.hermes.config import (
    DEFAULT_AGENT_NAME,
    DEFAULT_AGENT_ROLE,
    memory_path,
)
from multitude.integrations.telegram import TelegramAdapter, TelegramEnvelope


class HermesAgentUnavailable(RuntimeError):
    """Live Hermes generation is unavailable."""


@dataclass
class IndividualMemoryStore:
    """Separate mutable memory for one Hermes node.

    This is intentionally distinct from the tribe's append-only social
    memory. It lives in its own file under the tribe directory.
    """

    path: Path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"facts": {}, "notes": [], "skills": [], "preferences": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def remember(self, key: str, value: Any) -> None:
        data = self.load()
        data.setdefault("facts", {})[key] = value
        self.save(data)

    def note(self, text: str) -> None:
        data = self.load()
        data.setdefault("notes", []).append(text)
        self.save(data)


class HermesAgent:
    """A non-sovereign technological participant backed by Hermes conventions."""

    def __init__(
        self,
        adapter: MultitudeHermesAdapter,
        client: Optional[OllamaClient] = None,
    ) -> None:
        self.adapter = adapter
        self.member = adapter.ensure_agent()
        self.client = client or OllamaClient(model=adapter.model or self.member.model)
        self.memory = IndividualMemoryStore(memory_path(adapter.tribe.store.path, self.member.name))

    def who_are_members(self) -> str:
        members = self.adapter.list_agents()
        parts = [
            f"{m.name} ({m.kind.value}, {'voting' if m.voting else 'voice'})"
            for m in members
        ]
        return "Members of the tribe: " + ", ".join(parts) + "."

    def summarize_recent_history(self, days: int = 7, limit: int = 50) -> str:
        events = self.adapter.get_recent_events(limit=limit, days=days)
        if not events:
            return f"No tribe events were recorded in the last {days} days."
        lines = [f"Recorded tribe events in the last {days} days:"]
        for ev in events:
            if ev.type == "proposal_closed":
                d = ev.payload["decision"]
                dissent = d.get("dissent", [])
                lines.append(
                    f"- decision {d['proposal_title']}: {d['outcome']} under {d['rule']} "
                    f"with tally {d['tally']}"
                )
                for row in dissent:
                    lines.append(
                        f"  dissent: {row['member']} ({row['position']}): {row['reason'] or '-'}"
                    )
            elif ev.type == "proposal_opened":
                p = ev.payload["proposal"]
                lines.append(f"- proposal opened by {p['opened_by']}: {p['title']}")
            elif ev.type == "goal_opened":
                g = ev.payload["goal"]
                lines.append(f"- goal opened [{g['category']}]: {g['title']}")
            elif ev.type == "task_opened":
                t = ev.payload["task"]
                lines.append(f"- task opened: {t['title']}")
            elif ev.type == "memory_added":
                entry = ev.payload["entry"]
                lines.append(f"- memory added [{entry['kind']}]: {entry['title']}")
            elif ev.type == "message":
                msg = ev.payload["message"]
                lines.append(f"- {msg['author']} said: {msg['text'][:120]}")
            else:
                lines.append(f"- {ev.type} by {ev.actor}")
        return "\n".join(lines)

    def current_goals(self) -> str:
        grouped = self.adapter.current_goals_summary()
        lines = ["Current open goals:"]
        any_goal = False
        for category in ("business", "social", "health"):
            items = grouped.get(category, [])
            if items:
                any_goal = True
                lines.append(f"- {category}: " + "; ".join(items))
        return "\n".join(lines) if any_goal else "There are no recorded open goals right now."

    def unresolved_proposals(self) -> str:
        open_props = self.adapter.list_proposals(status="open")
        if not open_props:
            return "There are no unresolved proposals."
        lines = ["Unresolved proposals:"]
        for p in open_props:
            tally = self.adapter.tribe.tally(p.id)
            lines.append(
                f"- {p.id}: {p.title} (rule={p.rule.value}, votes={tally['counts']}, quorum_met={tally['quorum_met']})"
            )
        return "\n".join(lines)

    def suggest_next_action(self) -> str:
        open_props = self.adapter.list_proposals(status="open")
        if open_props:
            p = open_props[0]
            return (
                f"Next action: resolve proposal {p.id} ({p.title}) by surfacing remaining objections "
                "or collecting the missing votes."
            )
        goals_text = self.adapter.current_goals_summary()
        for category in ("business", "health", "social"):
            items = goals_text.get(category, [])
            if items:
                return f"Next action: pick one open {category} goal and turn it into a concrete task or proposal."
        if self.adapter.tribe.memory:
            return "Next action: review the shared memory and define the tribe's next concrete business or health goal."
        return "Next action: record the tribe's first concrete goal or proposal."

    def draft_proposal(self, topic: str) -> dict[str, str]:
        self.adapter.permissions.require("draft")
        title = self._proposal_title(topic)
        body = (
            f"The tribe proposes to {topic.strip().rstrip('.')}.\n\n"
            f"This draft is AI-authored by {self.member.name} as a knowledge steward. "
            "It should be reviewed, revised, and then explicitly created by instruction."
        )
        return {"title": title[:100], "text": body[:600]}

    @staticmethod
    def _proposal_title(topic: str) -> str:
        """Turn a suggestion into a proposal title without 'Adopt Suggest' clutter."""
        t = topic.strip().rstrip(".")
        for prefix in ("suggest that we ", "suggesting that we ", "suggest we ", "that we "):
            low = t.lower()
            if low.startswith(prefix):
                t = t[len(prefix):]
                break
        if not t:
            t = "Untitled proposal"
        low = t.lower()
        if not low.startswith(("adopt", "test", "hold", "create", "review", "record",
                               "run", "start", "use", "organize", "organise")):
            t = "Adopt: " + t[0].upper() + t[1:]
        return t[:100]

    def create_proposal(self, topic: str) -> Any:
        draft = self.draft_proposal(topic)
        return self.adapter.create_proposal(draft["title"], draft["text"])

    def counsel(self, topic: str) -> str:
        self.adapter.permissions.require("counsel")
        prompt = (
            f"Tribe context:\n{self.adapter.tribe.context_for_llm()}\n\n"
            f"Question for {self.member.name}: {topic}\n\n"
            "Reply briefly, preserve disagreement, and never impersonate a human."
        )
        raw = self.client.chat(
            (
                f"You are {self.member.name}, a Hermes-based technological node in Panpsychic Cyborg Multitude. "
                "You are a knowledge steward, not a sovereign. Preserve dissent, authorship, and uncertainty."
            ),
            prompt,
        )
        if raw is None:
            self.adapter.tribe.say(
                self.member.name,
                f"[{self.member.name} is silent - model unreachable]",
                kind="system",
            )
            raise HermesAgentUnavailable("live Hermes counsel unavailable - model unreachable")
        msg = self.adapter.tribe.say(
            self.member.name,
            raw,
            kind="counsel",
            meta={"model": self.client.model, "origin": "hermes"},
        )
        return msg.text

    def ask(self, question: str) -> str:
        q = question.strip().lower()
        self.memory.note(question.strip())
        if "who are the members" in q or q == "members" or "members of the tribe" in q:
            return self.who_are_members()
        if "what happened" in q or "last week" in q or "history" in q:
            return self.summarize_recent_history()
        if "current goals" in q or "our goals" in q:
            return self.current_goals()
        if "unresolved" in q and ("proposal" in q or "decision" in q):
            return self.unresolved_proposals()
        if "suggest our next action" in q or "next action" in q:
            return self.suggest_next_action()
        hits = self.adapter.search_memory(question)
        if hits:
            lines = ["Relevant shared memory:"]
            for entry in hits[:5]:
                lines.append(f"- {entry.title}: {entry.text[:160]}")
            return "\n".join(lines)
        return "I do not find a direct recorded answer. Ask me to summarize history, current goals, members, or unresolved proposals."


def _load_agent(args: argparse.Namespace) -> HermesAgent:
    tribe_dir = config.find_tribe_dir(getattr(args, "tribe", None))
    tribe = Tribe(TribeStore(tribe_dir))
    adapter = MultitudeHermesAdapter(
        tribe=tribe,
        agent_name=args.name,
        role=args.role,
        model=args.model,
    )
    return HermesAgent(adapter)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-pcm", description="Hermes technological node for PCM")
    parser.add_argument("--tribe", default=None, help="tribe directory (default: most recent)")
    parser.add_argument("--name", default=DEFAULT_AGENT_NAME)
    parser.add_argument("--role", default=DEFAULT_AGENT_ROLE)
    parser.add_argument("--model", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ask", help="ask the technological node a grounded question")
    p.add_argument("question")

    p = sub.add_parser("draft-proposal", help="draft a proposal without mutating tribe state")
    p.add_argument("topic")

    p = sub.add_parser("create-proposal", help="create a real proposal attributed to the technological node")
    p.add_argument("topic")

    p = sub.add_parser("counsel", help="live model-backed counsel; fails cleanly if unavailable")
    p.add_argument("topic")

    p = sub.add_parser("status", help="show node and tribe status")

    p = sub.add_parser("telegram-message", help="handle one Telegram message through the technological node")
    p.add_argument("--user-id", required=True)
    p.add_argument("--message", required=True)
    p.add_argument("--chat-id", default=None)
    p.add_argument("--message-id", default=None)
    p.add_argument("--username", default=None)
    p.add_argument("--direct-message", action="store_true")
    p.add_argument("--reply-to-bot", dest="reply_to_bot", action="store_true")
    p.add_argument("--reply-to-athena", dest="reply_to_bot", action="store_true", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    agent = _load_agent(args)
    if args.command == "ask":
        print(agent.ask(args.question))
        return 0
    if args.command == "draft-proposal":
        print(json.dumps(agent.draft_proposal(args.topic), indent=2, ensure_ascii=False))
        return 0
    if args.command == "create-proposal":
        p = agent.create_proposal(args.topic)
        print(f"Created proposal {p.id}: {p.title}")
        return 0
    if args.command == "counsel":
        try:
            print(agent.counsel(args.topic))
            return 0
        except HermesAgentUnavailable as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "status":
        print(json.dumps(agent.adapter.get_status(), indent=2, ensure_ascii=False))
        return 0
    if args.command == "telegram-message":
        telegram = TelegramAdapter(
            tribe=agent.adapter.tribe,
            agent_name=agent.member.name,
            role=agent.adapter.role,
            model=agent.adapter.model,
        )
        response = telegram.handle_message(
            TelegramEnvelope(
                user_id=args.user_id,
                text=args.message,
                chat_id=args.chat_id,
                message_id=args.message_id,
                username=args.username,
                direct_message=args.direct_message,
                reply_to_bot=args.reply_to_bot,
            )
        )
        if response is not None and response.text:
            print(response.text)
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
