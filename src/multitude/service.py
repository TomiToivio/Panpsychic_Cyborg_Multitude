# -*- coding: utf-8 -*-
"""Small application/service layer shared by CLI, Web, and Telegram."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
from typing import Any, Optional

from multitude.llm import TechnologicalNode
from multitude.models import NodeKind, Position, ProposalStatus, Rule
from multitude.tribe import Tribe, TribeError


class ServiceError(RuntimeError):
    """Application-layer validation error."""


class UnknownMember(ServiceError):
    """Named author/voter/node does not exist in the tribe."""


@dataclass
class MultitudeService:
    """Thin facade over the kernel.

    The kernel remains the source of truth; this layer only normalizes
    shared operations so interface adapters stop duplicating them.
    """

    tribe: Tribe

    @classmethod
    def for_tribe_dir(cls, tribe_dir: str) -> "MultitudeService":
        from multitude.store import TribeStore

        return cls(Tribe(TribeStore(tribe_dir)))

    def _require_member(self, name: str) -> str:
        if not name or self.tribe.member_by_name(name) is None:
            raise UnknownMember(f"unknown member '{name}'")
        return self.tribe.member_by_name(name).name

    def status(self) -> dict[str, Any]:
        bio = sum(1 for m in self.tribe.members.values() if m.kind == NodeKind.BIOLOGICAL)
        tech = sum(1 for m in self.tribe.members.values() if m.kind == NodeKind.TECHNOLOGICAL)
        open_props = [p for p in self.tribe.proposals.values() if p.status == ProposalStatus.OPEN]
        return {
            "tribe": self.tribe.name,
            "charter": self.tribe.charter,
            "events": len(self.tribe.store.replay()),
            "events_total": len(self.tribe.store.replay()),
            "members_total": len(self.tribe.members),
            "members": len(self.tribe.members),
            "biological_members": bio,
            "technological_members": tech,
            "messages_total": len(self.tribe.messages),
            "messages": len(self.tribe.messages),
            "memory_entries": len(self.tribe.memory),
            "decisions": len(self.tribe.decisions),
            "open_proposals": len(open_props),
            "open_proposal_ids": [p.id for p in open_props],
            "goals": len(self.tribe.goals),
            "tasks": len(self.tribe.tasks),
            "lexicon_terms": len(self.tribe.lexicon),
            "devices": len(self.tribe.devices),
            "memberships": len(self.tribe.memberships),
            "work_logs": len(self.tribe.work_logs),
            "governance_rules": len(self.tribe.governance_rules),
            "intents": len(self.tribe.intents),
            "commitments": len(self.tribe.commitments),
            "agreements": len(self.tribe.agreements),
            "economy_profiles": len(self.tribe.economy_profiles),
            "federation_agreements": len(self.tribe.federation_agreements),
            "care_records": len(self.tribe.care_log),
            "rhythms": len(self.tribe.rhythms),
            "physical_events": len(self.tribe.physical_events),
        }

    def list_agents(self) -> list[dict[str, Any]]:
        items = []
        for member in sorted(self.tribe.members.values(), key=lambda m: m.joined_ts):
            items.append(
                {
                    "id": member.id,
                    "name": member.name,
                    "kind": member.kind.value,
                    "voting": member.voting,
                    "persona": member.persona,
                    "model": member.model,
                    "joined_ts": member.joined_ts,
                    "profile": member.profile.model_dump(),
                    "meta": dict(member.meta),
                }
            )
        return items

    def who(self) -> list[dict[str, Any]]:
        return self.list_agents()

    # ------------------------------------------------------------- rights

    def update_member(
        self,
        name: str,
        *,
        voting: Optional[bool] = None,
        persona: Optional[str] = None,
        model: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Persist a member metadata change through the event log."""
        member_name = self._require_member(name)
        updated = self.tribe.update_member(
            member_name, voting=voting, persona=persona, model=model, meta=meta
        )
        return updated.model_dump()

    def promote(self, name: str, *, actor: Optional[str] = None) -> dict[str, Any]:
        """Grant voting rights to a voice-only member (member_updated event)."""
        member_name = self._require_member(name)
        member = self.tribe.member_by_name(member_name)
        if member.voting:
            raise ServiceError(f"'{member_name}' already has voting rights")
        if actor:
            self._require_member(actor)
        updated = self.tribe.update_member(member_name, voting=True)
        if actor:
            self.tribe.say(
                actor,
                f"promoted {member_name} to voting member (member_updated event)",
                meta={"action": "promote", "target": member_name, "interface": "cli"},
            )
        return updated.model_dump()

    def demote(self, name: str, *, actor: Optional[str] = None) -> dict[str, Any]:
        """Revoke voting rights, keeping the member on the roster (voice-only)."""
        member_name = self._require_member(name)
        member = self.tribe.member_by_name(member_name)
        if not member.voting:
            raise ServiceError(f"'{member_name}' is already voice-only")
        if actor:
            self._require_member(actor)
        updated = self.tribe.update_member(member_name, voting=False)
        if actor:
            self.tribe.say(
                actor,
                f"demoted {member_name} to voice-only (member_updated event)",
                meta={"action": "demote", "target": member_name, "interface": "cli"},
            )
        return updated.model_dump()

    def list_lexicon(self) -> list[dict[str, Any]]:
        return [entry.model_dump() for entry in sorted(self.tribe.lexicon.values(), key=lambda item: item.ts)]

    def list_devices(self) -> list[dict[str, Any]]:
        return [device.model_dump() for device in sorted(self.tribe.devices.values(), key=lambda item: item.registered_ts)]

    def list_memberships(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.memberships.values(), key=lambda record: record.ts)]

    def list_work_logs(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.work_logs.values(), key=lambda record: record.ts)]

    def list_governance_rules(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.governance_rules.values(), key=lambda record: record.ts)]

    def list_intents(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.intents.values(), key=lambda record: record.ts)]

    def list_commitments(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.commitments.values(), key=lambda record: record.ts)]

    def list_agreements(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.agreements.values(), key=lambda record: record.ts)]

    def list_economy_profiles(self) -> list[dict[str, Any]]:
        return [
            item.model_dump()
            for item in sorted(self.tribe.economy_profiles.values(), key=lambda record: record.ts)
        ]

    def current_economy_profile(self) -> Optional[dict[str, Any]]:
        profile = self.tribe.current_economy_profile()
        return None if profile is None else profile.model_dump()

    def list_federation_agreements(self) -> list[dict[str, Any]]:
        return [
            item.model_dump()
            for item in sorted(self.tribe.federation_agreements.values(), key=lambda record: record.ts)
        ]

    def list_care_records(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.care_log.values(), key=lambda record: record.ts)]

    def list_rhythms(self) -> list[dict[str, Any]]:
        return [item.model_dump() for item in sorted(self.tribe.rhythms.values(), key=lambda record: record.ts)]

    # --------------------------------------------------
    # Work / commons write methods (Priority 1, ValueFlows-inspired).
    # All writes go through Tribe methods -> single append-only event log.
    # --------------------------------------------------

    def register_resource(
        self,
        name: str,
        registered_by: str,
        kind: str = "resource",
        owner: str = "tribe",
        status: str = "available",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.register_resource(
            name, kind=kind, owner=registered_by if owner == "__member__" else owner,
            status=status, meta=meta,
        )
        return record.model_dump()

    def allocate_resource(
        self, resource_id: str, assignee: str, purpose: str = "",
        status: str = "allocated",
    ) -> dict[str, Any]:
        allocation = self.tribe.allocate_resource(
            resource_id, assignee, purpose=purpose, status=status
        )
        return allocation.model_dump()

    def log_work(
        self,
        *,
        member: str,
        description: str,
        hours: float,
        logged_by: Optional[str] = None,
        kind: str = "labor",
        task_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        contribution_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.log_work(
            member=member, description=description, hours=hours,
            logged_by=logged_by, kind=kind, task_id=task_id, goal_id=goal_id,
            contribution_id=contribution_id, tags=tags, notes=notes, meta=meta,
        )
        return record.model_dump()

    def define_governance_rule(
        self,
        *,
        title: str,
        description: str,
        defined_by: str,
        kind: str = "policy",
        scope: str = "tribe",
        applies_to: Optional[list[str]] = None,
        status: str = "active",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.define_governance_rule(
            title=title, description=description, defined_by=defined_by,
            kind=kind, scope=scope, applies_to=applies_to, status=status, meta=meta,
        )
        return record.model_dump()

    def record_intent(
        self,
        *,
        title: str,
        created_by: str,
        description: str = "",
        kind: str = "need",
        target_members: Optional[list[str]] = None,
        resource_ids: Optional[list[str]] = None,
        status: str = "open",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_intent(
            title=title, created_by=created_by, description=description,
            kind=kind, target_members=target_members, resource_ids=resource_ids,
            status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def record_commitment(
        self,
        *,
        title: str,
        committed_by: str,
        owed_by: str,
        owed_to: str = "",
        description: str = "",
        resource_ids: Optional[list[str]] = None,
        task_id: Optional[str] = None,
        due_ts: Optional[str] = None,
        status: str = "open",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_commitment(
            title=title, committed_by=committed_by, owed_by=owed_by,
            owed_to=owed_to, description=description, resource_ids=resource_ids,
            task_id=task_id, due_ts=due_ts, status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def record_agreement(
        self,
        *,
        title: str,
        created_by: str,
        parties: list[str],
        description: str = "",
        commitment_ids: Optional[list[str]] = None,
        status: str = "active",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_agreement(
            title=title, created_by=created_by, parties=parties,
            description=description, commitment_ids=commitment_ids,
            status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def record_contribution(
        self,
        *,
        contributed_by: str,
        title: str,
        kind: str = "labor",
        task_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        device_id: Optional[str] = None,
        output_memory_id: Optional[str] = None,
        quantity: float = 1.0,
        unit: str = "unit",
        cost_amount: Optional[float] = None,
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        from multitude.goals import record_contribution as goals_record_contribution

        record = goals_record_contribution(
            self.tribe,
            contributed_by=contributed_by,
            title=title,
            kind=kind,
            task_id=task_id,
            resource_id=resource_id,
            device_id=device_id,
            output_memory_id=output_memory_id,
            quantity=quantity,
            unit=unit,
            cost_amount=cost_amount,
            notes=notes,
            meta=meta,
        )
        return record.model_dump()

    def record_care(
        self,
        *,
        member: str,
        summary: str,
        recorded_by: str,
        care_type: str = "check_in",
        domain: str = "social",
        beneficiaries: Optional[list[str]] = None,
        hours: float = 0.0,
        notes: str = "",
        tags: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_care(
            member=member, summary=summary, recorded_by=recorded_by,
            care_type=care_type, domain=domain, beneficiaries=beneficiaries,
            hours=hours, notes=notes, tags=tags, meta=meta,
        )
        return record.model_dump()

    def record_economic_agent(
        self,
        *,
        name: str,
        created_by: str,
        role: str = "member",
        obligations: Optional[list[str]] = None,
        claims: Optional[list[str]] = None,
        resource_ids: Optional[list[str]] = None,
        contribution_ids: Optional[list[str]] = None,
        status: str = "active",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_economic_agent(
            name=name, created_by=created_by, role=role, obligations=obligations,
            claims=claims, resource_ids=resource_ids,
            contribution_ids=contribution_ids, status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def record_protocol_term(
        self,
        *,
        term: str,
        definition: str,
        created_by: str,
        domain: str = "economic",
        tags: Optional[list[str]] = None,
        status: str = "active",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.record_protocol_term(
            term=term, definition=definition, created_by=created_by,
            domain=domain, tags=tags, status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def define_rhythm(
        self,
        *,
        name: str,
        cadence: str,
        purpose: str,
        created_by: str,
        participants: Optional[list[str]] = None,
        care_required: bool = False,
        status: str = "active",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        record = self.tribe.define_rhythm(
            name=name, cadence=cadence, purpose=purpose, created_by=created_by,
            participants=participants, care_required=care_required,
            status=status, notes=notes, meta=meta,
        )
        return record.model_dump()

    def work_summary(self) -> dict[str, Any]:
        """Derived work view: hours by member/kind, open obligations."""
        hours_by_member: dict[str, float] = {}
        hours_by_kind: dict[str, float] = {}
        for log in self.tribe.work_logs.values():
            hours_by_member[log.member_name] = round(
                hours_by_member.get(log.member_name, 0.0) + log.hours, 2
            )
            hours_by_kind[log.kind] = round(
                hours_by_kind.get(log.kind, 0.0) + log.hours, 2
            )
        open_commitments = [
            item.model_dump()
            for item in self.tribe.commitments.values()
            if item.status == "open"
        ]
        costs = [
            item.model_dump()
            for item in self.tribe.contributions.values()
            if item.cost_amount is not None
        ]
        return {
            "hours_by_member": hours_by_member,
            "hours_by_kind": hours_by_kind,
            "open_commitments": open_commitments,
            "costs_recorded": costs,
            "care_hours": round(
                sum(r.hours for r in self.tribe.care_log.values()), 2
            ),
        }

    def list_physical_events(self, limit: int = 20) -> list[dict[str, Any]]:
        return [event.model_dump() for event in self.tribe.physical_events[-limit:]]

    def recent_events(self, limit: int = 20, days: Optional[int] = None) -> list[dict[str, Any]]:
        events = self.tribe.store.replay()
        if days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            filtered = []
            for ev in events:
                try:
                    when = datetime.fromisoformat(ev.ts)
                except ValueError:
                    when = None
                if when is None or when >= cutoff:
                    filtered.append(ev)
            events = filtered
        return [ev.model_dump() for ev in events[-limit:]]

    def list_proposals(self, status: Optional[str] = None) -> list[dict[str, Any]]:
        items = list(self.tribe.proposals.values())
        if status is not None:
            items = [p for p in items if p.status.value == status]
        return [p.model_dump() for p in sorted(items, key=lambda p: p.opened_ts)]

    def get_proposal(self, proposal_id: str) -> dict[str, Any]:
        proposal = self.tribe.proposals.get(proposal_id)
        if proposal is None:
            raise TribeError(f"no proposal '{proposal_id}'")
        data = proposal.model_dump()
        data["tally"] = self.tribe.tally(proposal_id)
        return data

    def proposal_view(self, proposal_id: str) -> dict[str, Any]:
        data = self.get_proposal(proposal_id)
        summary = self.tribe.proposal_summary(proposal_id)
        data["summary"] = summary
        data["dissent_summary"] = summary.get("dissent_summary", [])
        data["counsel"] = summary.get("counsel", [])
        return data

    def search_memory(
        self,
        query: str,
        scopes: Optional[list[str]] = None,
        audiences: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        return [
            entry.model_dump()
            for entry in self.tribe.search_memory(query, scopes=scopes, audiences=audiences)
        ]

    def add_private_note(
        self,
        owner: str,
        title: str,
        text: str,
        kind: str = "note",
        tags: Optional[list[str]] = None,
        interface: str = "cli",
    ) -> dict[str, Any]:
        del interface
        owner_name = self._require_member(owner)
        note = self.tribe.add_private_note(
            owner=owner_name,
            title=title,
            text=text,
            kind=kind,
            tags=tags,
        )
        return note.model_dump()

    def list_private_notes(self, owner: str) -> list[dict[str, Any]]:
        owner_name = self._require_member(owner)
        return [note.model_dump() for note in self.tribe.list_private_notes(owner_name)]

    def publish_private_note(
        self,
        *,
        owner: str,
        note_id: str,
        published_by: str,
        scope: str = "tribe",
        title: Optional[str] = None,
        text: Optional[str] = None,
        tags: Optional[list[str]] = None,
        kind: Optional[str] = None,
        interface: str = "cli",
    ) -> dict[str, Any]:
        del interface
        owner_name = self._require_member(owner)
        publisher_name = self._require_member(published_by)
        entry = self.tribe.publish_private_note(
            note_id=note_id,
            owner=owner_name,
            published_by=publisher_name,
            scope=scope,
            title=title,
            text=text,
            tags=tags,
            kind=kind,
        )
        return entry.model_dump()

    def link_entities(
        self,
        *,
        author: str,
        source_kind: str,
        source: str,
        target_kind: str,
        target: str,
        relation: str,
        meta: Optional[dict[str, Any]] = None,
        interface: str = "cli",
    ) -> dict[str, Any]:
        del interface
        author_name = self._require_member(author)
        link = self.tribe.link_entities(
            source_kind=source_kind,
            source=source,
            target_kind=target_kind,
            target=target,
            relation=relation,
            linked_by=author_name,
            meta=meta,
        )
        return link.model_dump()

    def list_entity_links(
        self,
        *,
        entity_kind: str,
        entity: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        return [
            link.model_dump()
            for link in self.tribe.entity_links_for(
                entity_kind=entity_kind,
                entity=entity,
                direction=direction,
                relation=relation,
            )
        ]

    def define_economy_profile(
        self,
        *,
        created_by: str,
        mission: str,
        recognized_value_types: list[str],
        distribution_logic: str,
        governance_style: str,
        pricing_modes: Optional[list[str]] = None,
        solidarity_policy: str = "",
        external_alliances: Optional[list[str]] = None,
        notes: str = "",
        status: str = "active",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        author = self._require_member(created_by)
        record = self.tribe.define_economy_profile(
            created_by=author,
            mission=mission,
            recognized_value_types=recognized_value_types,
            distribution_logic=distribution_logic,
            governance_style=governance_style,
            pricing_modes=pricing_modes,
            solidarity_policy=solidarity_policy,
            external_alliances=external_alliances,
            notes=notes,
            status=status,
            meta=meta,
        )
        return record.model_dump()

    def record_federation_agreement(
        self,
        *,
        created_by: str,
        title: str,
        partner_tribe: str,
        partner_slug: Optional[str] = None,
        agreement_type: str = "alliance",
        scopes: Optional[list[str]] = None,
        description: str = "",
        status: str = "proposed",
        resource_ids: Optional[list[str]] = None,
        related_agreement_ids: Optional[list[str]] = None,
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        author = self._require_member(created_by)
        record = self.tribe.record_federation_agreement(
            created_by=author,
            title=title,
            partner_tribe=partner_tribe,
            partner_slug=partner_slug,
            agreement_type=agreement_type,
            scopes=scopes,
            description=description,
            status=status,
            resource_ids=resource_ids,
            related_agreement_ids=related_agreement_ids,
            notes=notes,
            meta=meta,
        )
        return record.model_dump()

    def say(self, author: str, text: str, interface: str = "cli") -> dict[str, Any]:
        author_name = self._require_member(author)
        return self.tribe.say(author_name, text, meta={"interface": interface}).model_dump()

    def remember(
        self,
        author: str,
        title: str,
        text: str,
        kind: str = "note",
        tags: Optional[list[str]] = None,
        human: bool = True,
        scope: str = "tribe",
        meta: Optional[dict[str, Any]] = None,
        interface: str = "cli",
    ) -> dict[str, Any]:
        author_name = self._require_member(author) if author else ""
        entry = self.tribe.remember(
            title,
            text,
            author=author_name,
            kind=kind,
            tags=tags,
            human=human,
            scope=scope,
            meta=meta,
        )
        return entry.model_dump()

    def create_proposal(
        self,
        author: str,
        title: str,
        text: str,
        rule: Rule | str = Rule.CONSENSUS,
        interface: str = "cli",
    ) -> dict[str, Any]:
        del interface
        author_name = self._require_member(author)
        enum_rule = Rule(rule) if isinstance(rule, str) else rule
        proposal = self.tribe.open_proposal(title, text, opened_by=author_name, rule=enum_rule)
        return proposal.model_dump()

    def cast_vote(
        self,
        voter: str,
        proposal_id: str,
        position: Position | str,
        reason: Optional[str] = None,
        interface: str = "cli",
    ) -> dict[str, Any]:
        del interface
        voter_name = self._require_member(voter)
        enum_position = Position(position) if isinstance(position, str) else position
        vote = self.tribe.cast_vote(proposal_id, voter_name, enum_position, reason=reason)
        return {
            "vote": vote.model_dump(),
            "tally": self.tribe.tally(proposal_id),
        }

    def vote(
        self,
        proposal_id: str,
        voter: str,
        position: Position | str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        return self.cast_vote(voter, proposal_id, position, reason=reason)

    def counsel(
        self,
        agent_name: Optional[str] = None,
        topic: str = "",
        model: Optional[str] = None,
        node: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        agent = self._require_member(node or agent_name or "")
        tech = TechnologicalNode(self.tribe, agent, model=model)
        msg = tech.speak(topic=topic)
        return None if msg is None else msg.model_dump()

    def hermes_ask(
        self,
        question: str,
        agent_name: str = "Panpsychic Cyborg Multitude",
        role: str = "knowledge_steward",
        model: Optional[str] = None,
    ) -> str:
        from multitude.integrations.hermes.agent import HermesAgent
        from multitude.integrations.hermes.adapter import MultitudeHermesAdapter

        adapter = MultitudeHermesAdapter(
            tribe=self.tribe,
            agent_name=agent_name,
            role=role,
            model=model,
        )
        return HermesAgent(adapter).ask(question)

    def hermes_draft_proposal(
        self,
        topic: str,
        agent_name: str = "Panpsychic Cyborg Multitude",
        role: str = "knowledge_steward",
        model: Optional[str] = None,
    ) -> dict[str, str]:
        del role, model
        from multitude.integrations.hermes.agent import HermesAgent

        title = HermesAgent._proposal_title(topic)
        body = (
            f"The tribe proposes to {topic.strip().rstrip('.')}.\n\n"
            f"This draft is AI-authored by {agent_name} as a knowledge steward. "
            "It should be reviewed, revised, and then explicitly created by instruction."
        )
        return {"title": title[:100], "text": body[:600]}
