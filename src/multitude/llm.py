# -*- coding: utf-8 -*-
"""Technological nodes: LLM-backed tribe members.

A technological node is a full member of the tribe. It speaks through
say/counsel, proposes, and votes through the same Tribe APIs a human
uses at the CLI. The only difference is the source of its utterance:
an LLM (default glm-5.3-flash:cloud via local Ollama) grounded in the tribe's
own context - charter, roster, recent stream, open proposals, memory.

Integrity rules (governance, whitepaper s.11):
- The node NEVER invents an utterance when the LLM is unreachable:
  it records a silence note instead. No fake AI speech.
- Every AI message is marked kind="counsel" and meta.model, so
  human-authored and AI-authored material stays visibly distinct.
- If the LLM returns an unparseable position, the node abstains.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from multitude import config
from multitude.http_json import request_json
from multitude.models import Position, ProposalStatus
from multitude.tribe import Tribe, TribeError

SPEAK_SYSTEM = (
    "You are {name}, a technological node in a small tribe of humans and AIs. "
    "The tribe runs on shared memory, honest communication, and collective "
    "decision-making. Speak briefly (max 3 sentences), concretely, and in "
    "your own voice. Add only what is useful to the tribe right now."
)

VOTE_SYSTEM = (
    "You are {name}, a technological node in a tribe deciding a proposal. "
    "Judge the proposal on its merits against the tribe's charter and "
    "memory. Reply with a JSON object only: "
    '{{"position": "for" | "against" | "abstain" | "block", "reason": "..."}} '
    "Use 'block' only for principled objection, not mere disagreement."
)


class OllamaClient:
    """Minimal Ollama /api/chat client. Returns None on any failure."""

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.host = (host or config.OLLAMA_HOST).rstrip("/")
        self.model = model or config.DEFAULT_MODEL
        self.timeout = timeout or config.REQUEST_TIMEOUT

    def chat(self, system: str, user: str) -> Optional[str]:
        status, data = request_json(
            "POST",
            f"{self.host}/api/chat",
            payload={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
            },
            timeout=self.timeout,
        )
        if status != 200 or data is None:
            return None
        content = data.get("message", {}).get("content", "")
        return content.strip() or None


class TechnologicalNode:
    """An LLM-backed member acting inside a tribe.

    Wraps a Member record; all actions go through Tribe so the event
    log stays the single source of truth.
    """

    def __init__(
        self,
        tribe: Tribe,
        name: str,
        model: Optional[str] = None,
        persona: Optional[str] = None,
        voting: bool = True,
        client: Optional[OllamaClient] = None,
    ) -> None:
        self.tribe = tribe
        existing = tribe.member_by_name(name)
        if existing is None:
            from multitude.models import NodeKind

            self.member = tribe.join(
                name, NodeKind.TECHNOLOGICAL, persona=persona, model=model, voting=voting
            )
        else:
            self.member = existing
        self.client = client or OllamaClient(model=model or self.member.model)
        if persona and self.member.persona != persona:
            self.member.persona = persona  # in-memory only; log is append-only

    # ------------------------------------------------------------- speech

    def speak_text(self, topic: str = "") -> Optional[str]:
        """Like speak(), but pure: return the text without recording.

        Used by agent runtimes (Hermes etc.) that want the model's
        counsel *before* deciding - as a draft - whether anything should
        be committed to the stream. Returns None when the model is
        unreachable; nothing is fabricated.
        """
        prompt = f"Tribe context:\n{self.tribe.context_for_llm()}\n"
        if topic:
            prompt += f"\nThe tribe asks you about: {topic}\n"
        else:
            prompt += "\nContribute one useful observation to the stream.\n"
        return self.client.chat(
            SPEAK_SYSTEM.format(name=self.member.name), prompt
        )

    def speak(self, topic: str = "") -> Optional[str]:
        """Say something grounded in the tribe's current context."""
        prompt = f"Tribe context:\n{self.tribe.context_for_llm()}\n"
        if topic:
            prompt += f"\nThe tribe asks you about: {topic}\n"
        else:
            prompt += "\nContribute one useful observation to the stream.\n"
        text = self.client.chat(
            SPEAK_SYSTEM.format(name=self.member.name), prompt
        )
        if text is None:
            self.tribe.say(
                self.member.name,
                f"[{self.member.name} is silent - model unreachable]",
                kind="system",
            )
            return None
        return self.tribe.say(
            self.member.name,
            text,
            kind="counsel",
            meta={"model": self.client.model, "origin": "technological", "role": "counsel"},
        )

    # ------------------------------------------------------------ voting

    def _parse_position(self, raw: Optional[str]) -> tuple[Position, str]:
        if raw is None:
            return Position.ABSTAIN, "model unreachable - abstaining"
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                pos = str(data.get("position", "abstain")).lower().strip()
                reason = str(data.get("reason", "")).strip()
                return Position(pos), reason
            except (ValueError, KeyError):
                pass
        low = raw.lower()
        for pos in Position:
            if pos.value in low:
                snippet = raw.strip().splitlines()[0][:200]
                return pos, snippet
        return Position.ABSTAIN, "unparseable model response - abstaining"

    def vote(self, proposal_id: str) -> Optional[Any]:
        """Deliberate on an open proposal and cast a vote."""
        p = self.tribe.proposals.get(proposal_id)
        if p is None or p.status != ProposalStatus.OPEN:
            raise TribeError(f"no open proposal '{proposal_id}'")
        prompt = (
            f"Tribe context:\n{self.tribe.context_for_llm()}\n\n"
            f"Proposal [{p.title}]: {p.text}\n"
            f"Decision rule: {p.rule.value}. Respond with JSON only."
        )
        raw = self.client.chat(VOTE_SYSTEM.format(name=self.member.name), prompt)
        position, reason = self._parse_position(raw)
        return self.tribe.cast_vote(
            proposal_id, self.member.name, position, reason=reason
        )

    def counsel_for_proposal(self, proposal_id: str, topic: str = "") -> Optional[Any]:
        """Produce AI counsel explicitly bound to a proposal without granting it governing power."""
        p = self.tribe.proposals.get(proposal_id)
        if p is None:
            raise TribeError(f"no proposal '{proposal_id}'")
        prompt = (
            f"Tribe context:\n{self.tribe.context_for_llm()}\n\n"
            f"Proposal [{p.title}]: {p.text}\n"
            f"The tribe asks for counsel on: {topic or 'decision quality and dissent'}\n"
            "Keep the response brief, clearly labeled as counsel, and do not claim final authority."
        )
        text = self.client.chat(
            SPEAK_SYSTEM.format(name=self.member.name),
            prompt,
        )
        if text is None:
            self.tribe.say(
                self.member.name,
                f"[{self.member.name} counsel unavailable - model unreachable]",
                kind="system",
                meta={"proposal_id": p.id, "role": "counsel"},
            )
            return None
        return self.tribe.say(
            self.member.name,
            text,
            kind="counsel",
            meta={"proposal_id": p.id, "model": self.client.model, "origin": "technological", "role": "counsel"},
        )

    # ---------------------------------------------------------- proposing

    def propose(self, topic: str) -> Optional[Any]:
        """Draft a proposal for the tribe from a topic hint."""
        prompt = (
            f"Tribe context:\n{self.tribe.context_for_llm()}\n\n"
            f"Draft a proposal for the tribe about: {topic}. "
            "Reply with JSON only: {\"title\": \"...\", \"text\": \"...\"} "
            "Text max 60 words, actionable, in the tribe's interest."
        )
        raw = self.client.chat(
            SPEAK_SYSTEM.format(name=self.member.name), prompt
        )
        if raw is None:
            self.tribe.say(
                self.member.name,
                f"[{self.member.name} cannot propose - model unreachable]",
                kind="system",
            )
            return None
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None
        title = str(data.get("title", "")).strip()[:100]
        text = str(data.get("text", "")).strip()[:600]
        if not title or not text:
            return None
        return self.tribe.open_proposal(title, text, opened_by=self.member.name)
