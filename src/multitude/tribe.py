# -*- coding: utf-8 -*-
"""Tribe: the kernel. All state is derived by replaying the event log.

Governance semantics implemented here:

- Members are biological or technological nodes with equal rights.
  Technological nodes may be marked non-voting at the tribe's discretion
  (a policy choice recorded at join time), but they always retain voice.
- Proposals are decided by rule: consensus (no opposition), majority
  (for > against), or unanimity (every voting member for).
- A BLOCK is a principled objection: it rejects under consensus, and
  counts as opposition under majority.
- Quorum is the minimum number of voting members who must cast a vote.
- Dissent is never discarded: adopted decisions record who stood against
  and why. The log is append-only, so history belongs to everyone.
"""
from __future__ import annotations

from typing import Any, Optional

from multitude.goals import GoalError, replay_goal_event
from multitude.layers import (
    LayerError,
    default_seeds,
    format_member_layers,
    normalize_layer_name,
    replay_layer_record,
)
from multitude.models import (
    AgentProfile,
    CareRecord,
    ContributionRecord,
    Decision,
    DeviceRecord,
    BiometricSignalRecord,
    EconomicAgentRecord,
    EconomicAgreementRecord,
    EconomicCommitmentRecord,
    EconomicIntentRecord,
    EntityLink,
    EntityRef,
    FederationAgreementRecord,
    GovernanceRuleRecord,
    Layer,
    LexiconEntry,
    Member,
    MemoryEntry,
    Message,
    NodeKind,
    Outcome,
    PhysicalEvent,
    Position,
    PrivateNote,
    Proposal,
    ProposalStatus,
    ProtocolTermRecord,
    RhythmRecord,
    ResourceRecord,
    Rule,
    SensingEvent,
    TribeEconomyProfileRecord,
    TribeMembershipRecord,
    ValueFlowRecord,
    Vote,
    WorkLogRecord,
    WorkAllocation,
    new_id,
    now_iso,
)
from multitude.store import TribeStore


class TribeError(Exception):
    """Domain rule violation (unknown member, double vote, etc.)."""


# Goal/treasury/wellbeing event types, replayed by goals.replay_goal_event.
GOAL_EVENT_TYPES = frozenset(
    {
        "goal_opened",
        "goal_closed",
        "task_opened",
        "task_claimed",
        "task_released",
        "task_done",
        "profit_recorded",
        "profit_distributed",
        "contribution_recorded",
        "value_flow_recorded",
        "wellbeing_recorded",
        "interests_declared",
    }
)


class Tribe:
    """A running tribe: a TribeStore plus replayed state."""

    def __init__(self, store: TribeStore) -> None:
        self.store = store
        self.members: dict[str, Member] = {}
        self.former_members: dict[str, Member] = {}
        self.messages: list[Message] = []
        self.memory: dict[str, MemoryEntry] = {}
        self.private_notes: dict[str, PrivateNote] = {}
        self.proposals: dict[str, Proposal] = {}
        self.decisions: list[Decision] = []
        self.goals: dict[str, Any] = {}
        self.tasks: dict[str, Any] = {}
        self.treasury: dict[str, Any] = {"total": 0.0, "entries": []}
        self.profit_ledger: dict[str, float] = {}
        self.contributions: dict[str, ContributionRecord] = {}
        self.value_flows: dict[str, ValueFlowRecord] = {}
        self.wellbeing_stream: list[dict[str, Any]] = []
        self.interests: dict[str, list[str]] = {}
        self.lexicon: dict[str, LexiconEntry] = {}
        self.devices: dict[str, DeviceRecord] = {}
        self.biometric_signals: dict[str, BiometricSignalRecord] = {}
        self.sensing_events: dict[str, Any] = {}
        self.resources: dict[str, ResourceRecord] = {}
        self.work_allocations: dict[str, WorkAllocation] = {}
        self.memberships: dict[str, TribeMembershipRecord] = {}
        self.work_logs: dict[str, WorkLogRecord] = {}
        self.governance_rules: dict[str, GovernanceRuleRecord] = {}
        self.intents: dict[str, EconomicIntentRecord] = {}
        self.commitments: dict[str, EconomicCommitmentRecord] = {}
        self.agreements: dict[str, EconomicAgreementRecord] = {}
        self.economy_profiles: dict[str, TribeEconomyProfileRecord] = {}
        self.federation_agreements: dict[str, FederationAgreementRecord] = {}
        self.economic_agents: dict[str, EconomicAgentRecord] = {}
        self.protocol_terms: dict[str, ProtocolTermRecord] = {}
        self.care_log: dict[str, CareRecord] = {}
        self.rhythms: dict[str, RhythmRecord] = {}
        self.physical_events: list[PhysicalEvent] = []
        self.entity_links: list[EntityLink] = []
        self._replay()

    # ------------------------------------------------------------ founding

    @classmethod
    def found(
        cls, root: str, name: str, charter: str, founder_name: str
    ) -> "Tribe":
        store = TribeStore.create(root, name, charter)
        tribe = cls(store)
        tribe._ensure_member(founder_name, NodeKind.BIOLOGICAL)
        tribe.remember(
            title="Charter",
            text=charter or f"Founding charter of {name}.",
            kind="charter",
            author=founder_name,
            tags=["charter"],
        )
        return tribe

    # ------------------------------------------------------------- replay

    def _replay(self) -> None:
        for note in self.store.replay_private_notes():
            self.private_notes[note.id] = note
        for ev in self.store.replay():
            self._apply(ev.type, ev.payload)

    def _apply(self, type_: str, payload: dict[str, Any]) -> None:
        if type_ == "member_joined":
            m = Member.model_validate(payload["member"])
            self.members[m.id] = m
        elif type_ == "member_updated":
            m = Member.model_validate(payload["member"])
            if m.id in self.former_members:
                self.former_members[m.id] = m
            else:
                self.members[m.id] = m
        elif type_ == "member_left":
            mid = payload["member_id"]
            if mid in self.members:
                self.former_members[mid] = self.members.pop(mid)
        elif type_ == "membership_recorded":
            membership = TribeMembershipRecord.model_validate(payload["membership"])
            self.memberships[membership.member_id] = membership
        elif type_ == "message":
            self.messages.append(Message.model_validate(payload["message"]))
        elif type_ == "memory_added":
            entry = MemoryEntry.model_validate(payload["entry"])
            self.memory[entry.id] = entry
        elif type_ == "memory_revised":
            entry = self.memory.get(payload["entry_id"])
            if entry is not None:
                entry.revisions.append(entry.text)
                entry.text = payload["new_text"]
                entry.human = bool(payload.get("human", entry.human))
        elif type_ == "proposal_opened":
            p = Proposal.model_validate(payload["proposal"])
            self.proposals[p.id] = p
        elif type_ == "vote_cast":
            p = self.proposals.get(payload["proposal_id"])
            if p is not None:
                v = Vote.model_validate(payload["vote"])
                v.ts = v.ts or now_iso()
                p.votes[v.member] = v
        elif type_ == "proposal_closed":
            d = Decision.model_validate(payload["decision"])
            self.decisions.append(d)
            # Replay must rebuild proposal status as well, or closed
            # proposals reopen after a reload (append-only fix 2026-09-01).
            p = self.proposals.get(d.proposal_id)
            if p is not None:
                p.status = (
                    ProposalStatus.ADOPTED
                    if d.outcome == Outcome.ADOPTED
                    else ProposalStatus.REJECTED
                    if d.outcome == Outcome.REJECTED
                    else ProposalStatus.FAILED_QUORUM
                )
                p.outcome = d.outcome
        elif type_ == "layer_recorded":
            m = self.members.get(payload.get("member_id"))
            if m is not None:
                # Replay rebuilds the typed profile; history stays in the log.
                replay_layer_record(m, payload)
        elif type_ == "lexicon_defined":
            entry = LexiconEntry.model_validate(payload["entry"])
            self.lexicon[entry.term.lower()] = entry
        elif type_ == "device_registered":
            device = DeviceRecord.model_validate(payload["device"])
            self.devices[device.id] = device
        elif type_ == "device_updated":
            device = DeviceRecord.model_validate(payload["device"])
            self.devices[device.id] = device
        elif type_ == "resource_registered":
            resource = ResourceRecord.model_validate(payload["resource"])
            self.resources[resource.id] = resource
        elif type_ == "resource_allocated":
            allocation = WorkAllocation.model_validate(payload["allocation"])
            self.work_allocations[allocation.id] = allocation
        elif type_ == "work_logged":
            record = WorkLogRecord.model_validate(payload["work_log"])
            self.work_logs[record.id] = record
        elif type_ == "governance_rule_defined":
            record = GovernanceRuleRecord.model_validate(payload["rule"])
            self.governance_rules[record.id] = record
        elif type_ == "intent_recorded":
            record = EconomicIntentRecord.model_validate(payload["intent"])
            self.intents[record.id] = record
        elif type_ == "commitment_recorded":
            record = EconomicCommitmentRecord.model_validate(payload["commitment"])
            self.commitments[record.id] = record
        elif type_ == "agreement_recorded":
            record = EconomicAgreementRecord.model_validate(payload["agreement"])
            self.agreements[record.id] = record
        elif type_ == "economy_profile_defined":
            record = TribeEconomyProfileRecord.model_validate(payload["economy_profile"])
            self.economy_profiles[record.id] = record
        elif type_ == "federation_agreement_recorded":
            record = FederationAgreementRecord.model_validate(payload["federation_agreement"])
            self.federation_agreements[record.id] = record
        elif type_ == "economic_agent_recorded":
            record = EconomicAgentRecord.model_validate(payload["economic_agent"])
            self.economic_agents[record.id] = record
        elif type_ == "protocol_term_recorded":
            record = ProtocolTermRecord.model_validate(payload["protocol_term"])
            self.protocol_terms[record.id] = record
        elif type_ == "care_recorded":
            record = CareRecord.model_validate(payload["care"])
            self.care_log[record.id] = record
        elif type_ == "rhythm_defined":
            record = RhythmRecord.model_validate(payload["rhythm"])
            self.rhythms[record.id] = record
        elif type_ == "physical_event_recorded":
            event = PhysicalEvent.model_validate(payload["event"])
            self.physical_events.append(event)
        elif type_ == "biometric_signal_recorded":
            signal = BiometricSignalRecord.model_validate(payload["signal"])
            self.biometric_signals[signal.id] = signal
        elif type_ == "sensing_event_recorded":
            event = payload["event"]
            self.sensing_events[event["id"]] = event
        elif type_ == "entity_linked":
            link = EntityLink.model_validate(payload["link"])
            self.entity_links.append(link)
        elif type_ in GOAL_EVENT_TYPES:
            replay_goal_event(self, type_, payload)

    # ------------------------------------------------------------ helpers

    def _emit(self, type_: str, actor: str, payload: dict[str, Any]) -> None:
        self.store.append(type_, actor, payload)
        self._apply(type_, payload)

    def _ensure_member(self, name: str, kind: NodeKind) -> Member:
        m = self.member_by_name(name)
        if m is not None:
            if m.kind != kind:
                raise TribeError(f"'{name}' already exists as a {m.kind.value} node")
            return m
        m = Member(
            id=new_id("node"),
            name=name,
            kind=kind,
            joined_ts=now_iso(),
            profile=AgentProfile(
                biological={"is_biological": kind == NodeKind.BIOLOGICAL},
                cybernetic={"interface_mode": "text"},
            ),
        )
        self._emit("member_joined", "tribe", {"member": m.model_dump()})
        self._emit(
            "membership_recorded",
            "tribe",
            {
                "membership": TribeMembershipRecord(
                    id=new_id("membership"),
                    ts=now_iso(),
                    member_id=m.id,
                    member_name=m.name,
                    role="founder" if kind == NodeKind.BIOLOGICAL else "technological_node",
                    status="active",
                    recorded_by="tribe",
                    notes="Founding or bootstrap membership record.",
                ).model_dump()
            },
        )
        return self._apply_layer_defaults(m)

    def update_member(
        self,
        name: str,
        *,
        persona: Optional[str] = None,
        model: Optional[str] = None,
        voting: Optional[bool] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Member:
        """Persist a member metadata change through the event log."""
        member = self._require_member(name)
        updated = member.model_copy(deep=True)
        if persona is not None:
            updated.persona = persona
        if model is not None:
            updated.model = model
            updated.profile.cybernetic.model_runtime = model
        if voting is not None:
            updated.voting = voting
        if meta:
            merged = dict(updated.meta)
            merged.update(meta)
            updated.meta = merged
        self._emit("member_updated", updated.name, {"member": updated.model_dump()})
        return self.members[updated.id]

    def _require_member(self, name: str) -> Member:
        m = self.member_by_name(name)
        if m is None:
            raise TribeError(f"no member named '{name}' - join first")
        return m

    def member_by_name(self, name: str) -> Optional[Member]:
        low = name.strip().lower()
        for m in self.members.values():
            if m.name.lower() == low:
                return m
        return None

    @property
    def charter(self) -> str:
        return self.store.read_config().get("charter", "")

    @property
    def name(self) -> str:
        return self.store.read_config().get("name", "tribe")

    def voting_members(self) -> list[Member]:
        return [m for m in self.members.values() if m.voting]

    # ------------------------------------------------------- communication

    def say(
        self,
        author: str,
        text: str,
        kind: str = "say",
        in_reply_to: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> Message:
        m = self._require_member(author)
        msg = Message(
            id=new_id("msg"),
            ts=now_iso(),
            author=m.name,
            kind=kind,
            text=text.strip(),
            in_reply_to=in_reply_to,
            meta=meta or {},
        )
        self._emit("message", m.name, {"message": msg.model_dump()})
        return msg

    # -------------------------------------------------------------- memory

    def remember(
        self,
        title: str,
        text: str,
        author: str = "",
        kind: str = "note",
        tags: Optional[list[str]] = None,
        human: bool = True,
        visibility: str = "shared",
        source: str = "",
        scope: str = "tribe",
        audience: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> MemoryEntry:
        scope_clean = (scope or "tribe").strip().lower()
        if scope_clean not in {"tribe", "research", "federated"}:
            raise TribeError("memory scope must be tribe, research, or federated")
        visibility_clean = (visibility or "shared").strip().lower()
        if visibility_clean not in {"shared", "private", "restricted"}:
            raise TribeError("memory visibility must be shared, private, or restricted")

        actor_name = (author or "tribe").strip()
        member = self.member_by_name(actor_name) if actor_name and actor_name != "tribe" else None
        if member is not None:
            author_kind = "technological" if member.kind == NodeKind.TECHNOLOGICAL else "biological"
        elif human is False:
            author_kind = "technological"
        elif actor_name == "tribe":
            author_kind = "system"
        else:
            author_kind = "biological"
        if audience is None:
            if visibility_clean == "private":
                audience_list = ["self"]
            elif scope_clean == "research":
                audience_list = ["research"]
            elif scope_clean == "federated":
                audience_list = ["federated"]
            else:
                audience_list = ["tribe"]
        else:
            audience_list = [str(item).strip().lower() for item in audience if str(item).strip()]
            if not audience_list:
                audience_list = ["tribe"] if visibility_clean == "shared" else ["self"]

        merged_meta = dict(meta or {})
        merged_meta.setdefault("author_name", actor_name)
        merged_meta.setdefault("author_kind", author_kind)
        merged_meta.setdefault("source", source or ("agent" if not human else "self_report"))
        merged_meta.setdefault("visibility", visibility_clean)
        merged_meta.setdefault("scope", scope_clean)
        merged_meta.setdefault("audience", audience_list)

        entry = MemoryEntry(
            id=new_id("mem"),
            ts=now_iso(),
            kind=kind,
            title=title.strip(),
            text=text.strip(),
            tags=tags or [],
            author=author,
            human=human,
            visibility=visibility_clean,
            source=source or merged_meta["source"],
            audience=audience_list,
            scope=scope_clean,
            meta=merged_meta,
        )
        self._emit("memory_added", author or "tribe", {"entry": entry.model_dump()})
        return entry

    def revise_memory(self, entry_id: str, new_text: str, editor: str) -> MemoryEntry:
        entry = self.memory.get(entry_id)
        if entry is None:
            raise TribeError(f"no memory entry '{entry_id}'")
        editor_m = self._require_member(editor)
        human = editor_m.kind == NodeKind.BIOLOGICAL
        self._emit(
            "memory_revised",
            editor_m.name,
            {
                "entry_id": entry_id,
                "new_text": new_text.strip(),
                "human": human,
            },
        )
        return self.memory[entry_id]

    def search_memory(
        self,
        query: str,
        scopes: Optional[list[str]] = None,
        audiences: Optional[list[str]] = None,
    ) -> list[MemoryEntry]:
        """Naive lexical search - good enough for small tribes, zero deps."""
        wanted_scopes = {
            (item or "").strip().lower()
            for item in (scopes or ["tribe"])
            if (item or "").strip()
        }
        wanted_audiences = {
            (item or "").strip().lower()
            for item in (audiences or [])
            if (item or "").strip()
        }
        q = query.lower().split()
        scored: list[tuple[int, MemoryEntry]] = []
        for e in self.memory.values():
            if wanted_scopes and e.scope.lower() not in wanted_scopes:
                continue
            if wanted_audiences and not set(e.audience or []) & wanted_audiences:
                continue
            if not wanted_audiences and e.visibility.lower() == "private":
                continue
            blob = f"{e.title} {e.text} {' '.join(e.tags)}".lower()
            score = sum(1 for t in q if t in blob)
            if score:
                scored.append((score, e))
        return [e for _, e in sorted(scored, key=lambda x: (-x[0], x[1].ts))]

    def add_private_note(
        self,
        *,
        owner: str,
        title: str,
        text: str,
        kind: str = "note",
        tags: Optional[list[str]] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> PrivateNote:
        member = self._require_member(owner)
        note = PrivateNote(
            id=new_id("pnote"),
            ts=now_iso(),
            owner_id=member.id,
            owner_name=member.name,
            kind=kind,
            title=title.strip(),
            text=text.strip(),
            tags=tags or [],
            meta=dict(meta or {}),
        )
        if not note.title:
            raise TribeError("private note title cannot be empty")
        if not note.text:
            raise TribeError("private note text cannot be empty")
        self.store.append_private_note(note)
        self.private_notes[note.id] = note
        return note

    def list_private_notes(self, owner: str) -> list[PrivateNote]:
        member = self._require_member(owner)
        return [
            note
            for note in sorted(self.private_notes.values(), key=lambda item: item.ts)
            if note.owner_id == member.id
        ]

    def publish_private_note(
        self,
        *,
        note_id: str,
        owner: str,
        published_by: str,
        scope: str = "tribe",
        title: Optional[str] = None,
        text: Optional[str] = None,
        tags: Optional[list[str]] = None,
        kind: Optional[str] = None,
    ) -> MemoryEntry:
        owner_member = self._require_member(owner)
        publisher = self._require_member(published_by)
        note = self.private_notes.get(note_id)
        if note is None or note.owner_id != owner_member.id:
            raise TribeError(f"no private note '{note_id}' for '{owner_member.name}'")
        merged_tags: list[str] = []
        for item in [*(note.tags or []), *(tags or [])]:
            value = str(item).strip()
            if value and value.lower() not in [existing.lower() for existing in merged_tags]:
                merged_tags.append(value)
        return self.remember(
            title=(title or note.title).strip(),
            text=(text or note.text).strip(),
            author=owner_member.name,
            kind=(kind or note.kind).strip() or note.kind,
            tags=merged_tags,
            human=owner_member.kind == NodeKind.BIOLOGICAL,
            visibility="shared" if scope == "tribe" else "restricted",
            source="private_note_publication",
            scope=scope,
            meta={
                "source_private_note_id": note.id,
                "source_private_note_owner_id": note.owner_id,
                "source_private_note_owner": note.owner_name,
                "published_by": publisher.name,
            },
        )

    def _resolve_entity_ref(self, kind: str, value: str) -> EntityRef:
        kind_clean = (kind or "").strip().lower().replace("-", "_")
        value_clean = (value or "").strip()
        if not kind_clean:
            raise TribeError("entity kind cannot be empty")
        if not value_clean:
            raise TribeError("entity id cannot be empty")
        if kind_clean == "member":
            member = self.member_by_name(value_clean)
            if member is None:
                member = self.members.get(value_clean)
            if member is None:
                member = self.former_members.get(value_clean)
            if member is None:
                raise TribeError(f"no member '{value_clean}'")
            return EntityRef(kind="member", id=member.id)
        if kind_clean == "memory":
            if value_clean not in self.memory:
                raise TribeError(f"no memory entry '{value_clean}'")
            return EntityRef(kind="memory", id=value_clean)
        if kind_clean == "proposal":
            if value_clean not in self.proposals:
                raise TribeError(f"no proposal '{value_clean}'")
            return EntityRef(kind="proposal", id=value_clean)
        if kind_clean == "goal":
            if value_clean not in self.goals:
                raise TribeError(f"no goal '{value_clean}'")
            return EntityRef(kind="goal", id=value_clean)
        if kind_clean == "task":
            if value_clean not in self.tasks:
                raise TribeError(f"no task '{value_clean}'")
            return EntityRef(kind="task", id=value_clean)
        if kind_clean == "resource":
            if value_clean not in self.resources:
                raise TribeError(f"no resource '{value_clean}'")
            return EntityRef(kind="resource", id=value_clean)
        if kind_clean == "contribution":
            if value_clean not in self.contributions:
                raise TribeError(f"no contribution '{value_clean}'")
            return EntityRef(kind="contribution", id=value_clean)
        if kind_clean == "value_flow":
            if value_clean not in self.value_flows:
                raise TribeError(f"no value flow '{value_clean}'")
            return EntityRef(kind="value_flow", id=value_clean)
        if kind_clean == "lexicon":
            term = value_clean.lower()
            if term not in self.lexicon:
                raise TribeError(f"no lexicon term '{value_clean}'")
            return EntityRef(kind="lexicon", id=term)
        if kind_clean == "device":
            if value_clean not in self.devices:
                raise TribeError(f"no device '{value_clean}'")
            return EntityRef(kind="device", id=value_clean)
        if kind_clean == "physical_event":
            for event in self.physical_events:
                if event.id == value_clean:
                    return EntityRef(kind="physical_event", id=value_clean)
            raise TribeError(f"no physical event '{value_clean}'")
        if kind_clean == "decision":
            for decision in self.decisions:
                if decision.id == value_clean:
                    return EntityRef(kind="decision", id=value_clean)
            raise TribeError(f"no decision '{value_clean}'")
        if kind_clean == "membership":
            if value_clean not in self.memberships:
                raise TribeError(f"no membership '{value_clean}'")
            return EntityRef(kind="membership", id=value_clean)
        if kind_clean == "work_log":
            if value_clean not in self.work_logs:
                raise TribeError(f"no work log '{value_clean}'")
            return EntityRef(kind="work_log", id=value_clean)
        if kind_clean == "governance_rule":
            if value_clean not in self.governance_rules:
                raise TribeError(f"no governance rule '{value_clean}'")
            return EntityRef(kind="governance_rule", id=value_clean)
        if kind_clean == "intent":
            if value_clean not in self.intents:
                raise TribeError(f"no intent '{value_clean}'")
            return EntityRef(kind="intent", id=value_clean)
        if kind_clean == "commitment":
            if value_clean not in self.commitments:
                raise TribeError(f"no commitment '{value_clean}'")
            return EntityRef(kind="commitment", id=value_clean)
        if kind_clean == "agreement":
            if value_clean not in self.agreements:
                raise TribeError(f"no agreement '{value_clean}'")
            return EntityRef(kind="agreement", id=value_clean)
        if kind_clean == "economy_profile":
            if value_clean not in self.economy_profiles:
                raise TribeError(f"no economy profile '{value_clean}'")
            return EntityRef(kind="economy_profile", id=value_clean)
        if kind_clean == "federation_agreement":
            if value_clean not in self.federation_agreements:
                raise TribeError(f"no federation agreement '{value_clean}'")
            return EntityRef(kind="federation_agreement", id=value_clean)
        if kind_clean == "care":
            if value_clean not in self.care_log:
                raise TribeError(f"no care record '{value_clean}'")
            return EntityRef(kind="care", id=value_clean)
        if kind_clean == "rhythm":
            if value_clean not in self.rhythms:
                raise TribeError(f"no rhythm '{value_clean}'")
            return EntityRef(kind="rhythm", id=value_clean)
        if kind_clean == "message":
            for message in self.messages:
                if message.id == value_clean:
                    return EntityRef(kind="message", id=value_clean)
            raise TribeError(f"no message '{value_clean}'")
        raise TribeError(
            "unknown entity kind "
            f"'{kind_clean}' - valid: member, memory, proposal, goal, task, resource, contribution, value_flow, lexicon, device, physical_event, decision, membership, work_log, governance_rule, intent, commitment, agreement, economy_profile, federation_agreement, care, rhythm, message"
        )

    def link_entities(
        self,
        *,
        source_kind: str,
        source: str,
        target_kind: str,
        target: str,
        relation: str,
        linked_by: str,
        meta: Optional[dict[str, Any]] = None,
    ) -> EntityLink:
        actor = self._require_member(linked_by)
        source_ref = self._resolve_entity_ref(source_kind, source)
        target_ref = self._resolve_entity_ref(target_kind, target)
        relation_clean = (relation or "").strip()
        if not relation_clean:
            raise TribeError("relation cannot be empty")
        if source_ref == target_ref:
            raise TribeError("cannot link an entity to itself")
        link = EntityLink(
            id=new_id("link"),
            ts=now_iso(),
            source=source_ref,
            target=target_ref,
            relation=relation_clean,
            linked_by=actor.name,
            meta=dict(meta or {}),
        )
        self._emit("entity_linked", actor.name, {"link": link.model_dump()})
        return link

    def entity_links_for(
        self,
        *,
        entity_kind: str,
        entity: str,
        direction: str = "both",
        relation: Optional[str] = None,
    ) -> list[EntityLink]:
        entity_ref = self._resolve_entity_ref(entity_kind, entity)
        direction_clean = (direction or "both").strip().lower()
        if direction_clean not in {"inbound", "outbound", "both"}:
            raise TribeError("direction must be inbound, outbound, or both")
        relation_clean = (relation or "").strip().lower()
        out: list[EntityLink] = []
        for link in self.entity_links:
            matches_direction = (
                direction_clean == "both"
                and (link.source == entity_ref or link.target == entity_ref)
            ) or (
                direction_clean == "outbound" and link.source == entity_ref
            ) or (
                direction_clean == "inbound" and link.target == entity_ref
            )
            if not matches_direction:
                continue
            if relation_clean and link.relation.lower() != relation_clean:
                continue
            out.append(link)
        return out

    # --------------------------------------------------------- membership

    def join(
        self,
        name: str,
        kind: NodeKind,
        persona: Optional[str] = None,
        model: Optional[str] = None,
        voting: bool = True,
        profile: Optional[AgentProfile] = None,
    ) -> Member:
        existing = self.member_by_name(name)
        if existing is not None:
            if existing.kind != kind:
                raise TribeError(f"'{name}' already exists as a {existing.kind.value} node")
            return self.update_member(
                name,
                persona=persona,
                model=model,
                voting=voting,
            )
        m = Member(
            id=new_id("node"),
            name=name,
            kind=kind,
            voting=voting,
            persona=persona,
            model=model,
            joined_ts=now_iso(),
            profile=profile
            or AgentProfile(
                biological={"is_biological": kind == NodeKind.BIOLOGICAL},
                cybernetic={"interface_mode": "text", "model_runtime": model},
            ),
        )
        self._emit("member_joined", "tribe", {"member": m.model_dump()})
        self.record_membership(
            member=m.name,
            recorded_by="tribe",
            role="member",
        )
        self._apply_layer_defaults(m)
        return m

    def leave(self, name: str) -> Member:
        m = self._require_member(name)
        self._emit("member_left", m.name, {"member_id": m.id})
        self.record_membership(
            member=m.name,
            recorded_by="tribe",
            role=self.memberships.get(m.id).role if m.id in self.memberships else "member",
            status="former",
            notes="Member left the active tribe roster.",
        )
        return m

    def record_membership(
        self,
        *,
        member: str,
        recorded_by: str,
        role: str = "member",
        circles: Optional[list[str]] = None,
        status: str = "active",
        notes: str = "",
        meta: Optional[dict[str, Any]] = None,
    ) -> TribeMembershipRecord:
        target = self._require_member(member) if status != "former" else (
            self.member_by_name(member) or next(
                (item for item in self.former_members.values() if item.name.lower() == member.strip().lower()),
                None,
            )
        )
        if target is None:
            raise TribeError(f"no member named '{member}' - join first")
        actor = self._require_member(recorded_by) if recorded_by != "tribe" else None
        status_clean = (status or "active").strip().lower()
        if status_clean not in {"active", "former", "guest"}:
            raise TribeError("membership status must be active, former, or guest")
        record = TribeMembershipRecord(
            id=new_id("membership"),
            ts=now_iso(),
            member_id=target.id,
            member_name=target.name,
            role=(role or "member").strip() or "member",
            circles=[item.strip() for item in (circles or []) if item.strip()],
            status=status_clean,
            recorded_by=actor.name if actor else "tribe",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        self._emit("membership_recorded", record.recorded_by, {"membership": record.model_dump()})
        return record

    # ------------------------------------------------------------ the layers

    def record_layer(
        self,
        member: str,
        layer: str,
        data: Optional[dict[str, Any]] = None,
        reported_by: Optional[str] = None,
        visible: bool = True,
    ) -> Member:
        """Record an observation of one of the agent's six layers.

        ``data`` is a free-form dict; per-layer keys it recognizes are
        validated (unknown keys are rejected so vocabularies stay clean).
        ``reported_by`` records authorship: the agent itself or another
        member observing it. The record lands in the append-only log as
        a ``layer_recorded`` event and becomes the member's newest
        reading for that layer.
        """
        m = self._require_member(member)
        layer_enum = normalize_layer_name(layer)
        if not isinstance(data, dict) or not data:
            raise LayerError("layer record must be a non-empty dict")
        reporter = self._require_member(reported_by) if reported_by else None
        reporter_name = reporter.name if reporter else m.name
        from multitude.layers import layer_recorded_payload

        payload = layer_recorded_payload(
            m, layer_enum, dict(data), reporter_name, visible=visible
        )
        payload["ts"] = now_iso()
        self._emit("layer_recorded", reporter_name, payload)
        return m

    def layer_history(self, member: str, layer: str) -> list[dict[str, Any]]:
        """All recorded changes of one layer, oldest first (from the log)."""
        m = self._require_member(member)
        layer_enum = normalize_layer_name(layer)
        out = []
        for ev in self.store.replay():
            if ev.type != "layer_recorded" or ev.payload.get("member_id") != m.id:
                continue
            if ev.payload.get("layer") == layer_enum.value:
                out.append({**ev.payload, "ts": ev.ts})
        return out

    def _apply_layer_defaults(self, member: Member) -> Member:
        """Seed starter readings for a freshly joined node (event-sourced)."""
        for layer_val, changes in default_seeds(member).items():
            payload = {
                "member_id": member.id,
                "layer": layer_val,
                "changes": changes,
                "reported_by": member.name,
                "visible": True,
            }
            self._emit("layer_recorded", member.name, payload)
        return member

    def conscious_members(self) -> list[Member]:
        """Members whose psychic layer currently marks them conscious."""
        out = []
        for m in self.members.values():
            if m.profile.psychic.is_conscious:
                out.append(m)
        return out

    # -------------------------------------------------------- lexicon

    def define_term(
        self,
        term: str,
        definition: str,
        *,
        added_by: str,
        aliases: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> LexiconEntry:
        author = self._require_member(added_by)
        entry = LexiconEntry(
            term=term.strip(),
            definition=definition.strip(),
            aliases=[a.strip() for a in (aliases or []) if a.strip()],
            tags=[t.strip() for t in (tags or []) if t.strip()],
            added_by=author.name,
            ts=now_iso(),
        )
        if not entry.term:
            raise TribeError("term cannot be empty")
        self._emit("lexicon_defined", author.name, {"entry": entry.model_dump()})
        return entry

    def search_lexicon(self, query: str) -> list[LexiconEntry]:
        q = query.lower().split()
        scored: list[tuple[int, LexiconEntry]] = []
        for entry in self.lexicon.values():
            blob = " ".join(
                [entry.term, entry.definition, *entry.aliases, *entry.tags]
            ).lower()
            score = sum(1 for token in q if token in blob)
            if score:
                scored.append((score, entry))
        return [entry for _, entry in sorted(scored, key=lambda item: (-item[0], item[1].ts))]

    # -------------------------------------------------------- devices

    def register_device(
        self,
        *,
        registered_by: str,
        name: str,
        kind: str,
        owner: str = "",
        linked_member: str = "",
        interface_modes: Optional[list[str]] = None,
        location_label: Optional[str] = None,
        gps: Optional[dict[str, float]] = None,
        notes: str = "",
        sensitivity: str = "shared",
        consent_required: bool = False,
        meta: Optional[dict[str, Any]] = None,
    ) -> DeviceRecord:
        actor = self._require_member(registered_by)
        linked = self._require_member(linked_member) if linked_member else None
        sensitivity_clean = (sensitivity or "shared").strip().lower()
        if sensitivity_clean not in {"shared", "limited", "private"}:
            raise TribeError("device sensitivity must be shared, limited, or private")
        device = DeviceRecord(
            id=new_id("dev"),
            name=name.strip(),
            kind=kind.strip(),
            owner=owner.strip(),
            linked_member_id=linked.id if linked else None,
            interface_modes=[item.strip() for item in (interface_modes or []) if item.strip()],
            location_label=location_label.strip() if location_label else None,
            gps=gps,
            notes=notes.strip(),
            sensitivity=sensitivity_clean,
            consent_required=bool(consent_required),
            meta=dict(meta or {}),
            registered_ts=now_iso(),
        )
        if not device.name:
            raise TribeError("device name cannot be empty")
        if not device.kind:
            raise TribeError("device kind cannot be empty")
        self._emit("device_registered", actor.name, {"device": device.model_dump()})
        return device

    def update_device(
        self,
        device_id: str,
        *,
        updated_by: str,
        status: Optional[str] = None,
        location_label: Optional[str] = None,
        gps: Optional[dict[str, float]] = None,
        interface_modes: Optional[list[str]] = None,
        notes: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> DeviceRecord:
        actor = self._require_member(updated_by)
        device = self.devices.get(device_id)
        if device is None:
            raise TribeError(f"no device '{device_id}'")
        updated = device.model_copy(deep=True)
        if status is not None:
            updated.status = status.strip()
        if location_label is not None:
            updated.location_label = location_label.strip() or None
        if gps is not None:
            updated.gps = gps
        if interface_modes is not None:
            updated.interface_modes = [item.strip() for item in interface_modes if item.strip()]
        if notes is not None:
            updated.notes = notes.strip()
        if meta:
            merged = dict(updated.meta)
            merged.update(meta)
            updated.meta = merged
        self._emit("device_updated", actor.name, {"device": updated.model_dump()})
        return updated

    @staticmethod
    def _normalise_signal_metadata(
        *,
        member: str,
        signal_type: str,
        source: str = "manual",
        sensitivity: str,
        consent_required: bool,
        meta: Optional[dict[str, Any]] = None,
        kind: str = "biological",
    ) -> tuple[str, bool, dict[str, Any]]:
        sensitivity_clean = (sensitivity or "private").strip().lower()
        if sensitivity_clean not in {"shared", "limited", "private"}:
            raise TribeError("signal sensitivity must be shared, limited, or private")

        signal_key = (signal_type or "signal").strip().lower()
        sensitive_keywords = {
            "attention", "valence", "sleep", "stress", "fatigue", "hrv", "heart",
            "brain", "bci", "neural", "cognitive", "awareness", "focus", "mood",
            "emotion", "alertness", "drowsiness", "eeg", "calm", "arousal",
        }
        is_sensitive = (
            kind in {"biological", "psychic", "cybernetic"}
            or any(keyword in signal_key for keyword in sensitive_keywords)
        )

        if is_sensitive and sensitivity_clean == "shared":
            raise TribeError(
                "health or awareness signals must not be silently shared; use limited or private with explicit consent"
            )
        if is_sensitive and not consent_required:
            raise TribeError("sensitive health or awareness signals require explicit consent")

        merged_meta = dict(meta or {})
        source_value = (source or "manual").strip() or "manual"
        if meta is not None and "source" in meta:
            merged_meta["source"] = meta["source"]
        else:
            merged_meta["source"] = source_value
        if is_sensitive:
            merged_meta.setdefault("visibility", "private")
            merged_meta.setdefault("scope", "private")
        else:
            merged_meta.setdefault("visibility", sensitivity_clean)
            merged_meta.setdefault("scope", sensitivity_clean)
        merged_meta.setdefault("consent_required", bool(consent_required))
        merged_meta.setdefault("signal_type", signal_key)
        return sensitivity_clean, bool(consent_required), merged_meta

    # ----------------------------------------------------- physical events

    def record_physical_event(
        self,
        *,
        reported_by: str,
        event_type: str,
        description: str,
        members: Optional[list[str]] = None,
        devices: Optional[list[str]] = None,
        location_label: Optional[str] = None,
        gps: Optional[dict[str, float]] = None,
        sensitivity: str = "shared",
        consent_required: bool = False,
        meta: Optional[dict[str, Any]] = None,
    ) -> PhysicalEvent:
        reporter = self._require_member(reported_by)
        member_ids = [self._require_member(name).id for name in (members or [])]
        device_ids: list[str] = []
        for device_id in devices or []:
            if device_id not in self.devices:
                raise TribeError(f"no device '{device_id}'")
            device_ids.append(device_id)
        event = PhysicalEvent(
            id=new_id("phy"),
            ts=now_iso(),
            event_type=event_type.strip(),
            description=description.strip(),
            reported_by=reporter.name,
            member_ids=member_ids,
            device_ids=device_ids,
            location_label=location_label.strip() if location_label else None,
            gps=gps,
            sensitivity=(sensitivity or "shared").strip() or "shared",
            consent_required=bool(consent_required),
            meta=dict(meta or {}),
        )
        if not event.event_type:
            raise TribeError("physical event type cannot be empty")
        if not event.description:
            raise TribeError("physical event description cannot be empty")
        self._emit("physical_event_recorded", reporter.name, {"event": event.model_dump()})
        return event

    def record_biometric_signal(
        self,
        *,
        member: str,
        signal_type: str,
        value: Any,
        unit: str = "",
        source: str = "manual",
        sensitivity: str = "private",
        consent_required: bool = True,
        meta: Optional[dict[str, Any]] = None,
    ) -> BiometricSignalRecord:
        m = self._require_member(member)
        sensitivity_clean, consent_ok, merged_meta = self._normalise_signal_metadata(
            member=m.name,
            signal_type=signal_type,
            source=source,
            sensitivity=sensitivity,
            consent_required=consent_required,
            meta=meta,
            kind="biological",
        )
        merged_meta["source"] = (source or "manual").strip() or "manual"
        rec = BiometricSignalRecord(
            id=new_id("sig"),
            ts=now_iso(),
            member_id=m.id,
            member_name=m.name,
            signal_type=(signal_type or "signal").strip() or "signal",
            value=value,
            unit=(unit or "").strip(),
            source=(source or "manual").strip() or "manual",
            sensitivity=sensitivity_clean,
            consent_required=bool(consent_ok),
            meta=merged_meta,
        )
        self.biometric_signals[rec.id] = rec
        self._emit(
            "biometric_signal_recorded",
            m.name,
            {"signal": rec.model_dump()},
        )
        return rec

    def record_sensing_event(
        self,
        *,
        member: str,
        kind: str,
        signal_type: str,
        value: Any,
        unit: str = "",
        source: str = "manual",
        sensitivity: str = "private",
        consent_required: bool = True,
        meta: Optional[dict[str, Any]] = None,
    ) -> SensingEvent:
        m = self._require_member(member)
        kind_clean = (kind or "biological").strip().lower()
        if kind_clean not in {"physical", "biological", "psychic", "cybernetic"}:
            raise TribeError("sensing event kind must be physical, biological, psychic, or cybernetic")
        sensitivity_clean, consent_ok, merged_meta = self._normalise_signal_metadata(
            member=m.name,
            signal_type=signal_type,
            source=source,
            sensitivity=sensitivity,
            consent_required=consent_required,
            meta=meta,
            kind=kind_clean,
        )
        merged_meta["source"] = (source or "manual").strip() or "manual"
        event = SensingEvent(
            id=new_id("sense"),
            ts=now_iso(),
            member_id=m.id,
            member_name=m.name,
            kind=kind_clean,
            signal_type=(signal_type or "signal").strip() or "signal",
            value=value,
            unit=(unit or "").strip(),
            source=(source or "manual").strip() or "manual",
            sensitivity=sensitivity_clean,
            consent_required=bool(consent_ok),
            visibility=merged_meta.get("visibility", "private"),
            scope=merged_meta.get("scope", "private"),
            meta=merged_meta,
        )
        self.sensing_events[event.id] = event
        self._emit("sensing_event_recorded", m.name, {"event": event.model_dump()})
        return event

    # -------------------------------------------------------- decisioning

    def open_proposal(
        self,
        title: str,
        text: str,
        opened_by: str,
        rule: Rule = Rule.CONSENSUS,
        quorum: Optional[int] = None,
    ) -> Proposal:
        m = self._require_member(opened_by)
        n_voting = len(self.voting_members())
        if quorum is None:
            quorum = max(1, n_voting // 2)  # default: half the voting members
        p = Proposal(
            id=new_id("prop"),
            title=title.strip(),
            text=text.strip(),
            rule=rule,
            quorum=quorum,
            opened_by=m.name,
            opened_ts=now_iso(),
        )
        self._emit("proposal_opened", m.name, {"proposal": p.model_dump()})
        return p

    def cast_vote(
        self,
        proposal_id: str,
        member: str,
        position: Position,
        reason: Optional[str] = None,
    ) -> Vote:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise TribeError(f"no proposal '{proposal_id}'")
        if p.status != ProposalStatus.OPEN:
            raise TribeError(f"proposal '{proposal_id}' is already {p.status.value}")
        m = self._require_member(member)
        if not m.voting:
            raise TribeError(f"'{m.name}' is a non-voting node")
        if m.id in p.votes:
            raise TribeError(f"'{m.name}' has already voted on this proposal")
        v = Vote(member=m.id, position=position, reason=reason, ts=now_iso())
        self._emit(
            "vote_cast",
            m.name,
            {"proposal_id": proposal_id, "vote": v.model_dump()},
        )
        return v

    def tally(self, proposal_id: str) -> dict[str, Any]:
        """Current tally: counts among voting members, per position."""
        p = self._require_proposal(proposal_id)
        counts = {pos.value: 0 for pos in Position}
        n_voters = 0
        for v in p.votes.values():
            member = self.members.get(v.member)
            if member is None or not member.voting:
                continue  # left or non-voting: not counted
            counts[v.position.value] += 1
            n_voters += 1
        return {
            "proposal_id": p.id,
            "title": p.title,
            "status": p.status.value,
            "rule": p.rule.value,
            "counts": counts,
            "votes_cast": n_voters,
            "quorum": p.quorum,
            "quorum_met": n_voters >= p.quorum,
        }

    def _require_proposal(self, proposal_id: str) -> Proposal:
        p = self.proposals.get(proposal_id)
        if p is None:
            raise TribeError(f"no proposal '{proposal_id}'")
        return p

    def register_resource(
        self,
        name: str,
        *,
        kind: str = "resource",
        owner: str = "",
        status: str = "available",
        meta: Optional[dict[str, Any]] = None,
    ) -> Any:
        owner_name = owner.strip() if owner else "tribe"
        if owner_name and owner_name != "tribe":
            self._require_member(owner_name)
        resource = ResourceRecord(
            id=new_id("res"),
            name=name.strip(),
            kind=kind.strip() or "resource",
            owner=owner_name,
            status=status.strip() or "available",
            meta=dict(meta or {}),
            created_ts=now_iso(),
        )
        if not resource.name:
            raise TribeError("resource name cannot be empty")
        self._emit("resource_registered", owner_name, {"resource": resource.model_dump()})
        return resource

    def allocate_resource(
        self,
        resource_id: str,
        assignee: str,
        purpose: str = "",
        status: str = "allocated",
    ) -> Any:
        resource = self.resources.get(resource_id)
        if resource is None:
            raise TribeError(f"no resource '{resource_id}'")
        member = self._require_member(assignee)
        allocation = WorkAllocation(
            id=new_id("alloc"),
            resource_id=resource.id,
            assignee=member.name,
            purpose=(purpose or "").strip(),
            status=(status or "allocated").strip() or "allocated",
            ts=now_iso(),
        )
        self._emit("resource_allocated", member.name, {"allocation": allocation.model_dump()})
        return allocation

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
    ) -> WorkLogRecord:
        worker = self._require_member(member)
        actor = self._require_member(logged_by or member)
        if task_id and task_id not in self.tasks:
            raise TribeError(f"no task '{task_id}'")
        if goal_id and goal_id not in self.goals:
            raise TribeError(f"no goal '{goal_id}'")
        if contribution_id and contribution_id not in self.contributions:
            raise TribeError(f"no contribution '{contribution_id}'")
        if hours <= 0:
            raise TribeError("work log hours must be greater than 0")
        record = WorkLogRecord(
            id=new_id("worklog"),
            ts=now_iso(),
            member_id=worker.id,
            member_name=worker.name,
            description=description.strip(),
            hours=float(hours),
            kind=(kind or "labor").strip() or "labor",
            task_id=task_id,
            goal_id=goal_id,
            contribution_id=contribution_id,
            tags=[item.strip() for item in (tags or []) if item.strip()],
            notes=notes.strip(),
            logged_by=actor.name,
            meta=dict(meta or {}),
        )
        if not record.description:
            raise TribeError("work log description cannot be empty")
        self._emit("work_logged", actor.name, {"work_log": record.model_dump()})
        return record

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
    ) -> GovernanceRuleRecord:
        actor = self._require_member(defined_by)
        record = GovernanceRuleRecord(
            id=new_id("gov"),
            ts=now_iso(),
            title=title.strip(),
            description=description.strip(),
            kind=(kind or "policy").strip() or "policy",
            scope=(scope or "tribe").strip() or "tribe",
            applies_to=[item.strip() for item in (applies_to or []) if item.strip()],
            status=(status or "active").strip() or "active",
            defined_by=actor.name,
            meta=dict(meta or {}),
        )
        if not record.title:
            raise TribeError("governance rule title cannot be empty")
        if not record.description:
            raise TribeError("governance rule description cannot be empty")
        self._emit("governance_rule_defined", actor.name, {"rule": record.model_dump()})
        return record

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
    ) -> EconomicIntentRecord:
        actor = self._require_member(created_by)
        targets = [self._require_member(name).name for name in (target_members or [])]
        resource_list = []
        for resource_id in resource_ids or []:
            if resource_id not in self.resources:
                raise TribeError(f"no resource '{resource_id}'")
            resource_list.append(resource_id)
        record = EconomicIntentRecord(
            id=new_id("intent"),
            ts=now_iso(),
            title=title.strip(),
            description=description.strip(),
            created_by=actor.name,
            kind=(kind or "need").strip() or "need",
            target_members=targets,
            resource_ids=resource_list,
            status=(status or "open").strip() or "open",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        if not record.title:
            raise TribeError("intent title cannot be empty")
        self._emit("intent_recorded", actor.name, {"intent": record.model_dump()})
        return record

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
    ) -> EconomicCommitmentRecord:
        actor = self._require_member(committed_by)
        owed_by_member = self._require_member(owed_by)
        owed_to_name = self._require_member(owed_to).name if owed_to else ""
        if task_id and task_id not in self.tasks:
            raise TribeError(f"no task '{task_id}'")
        resources = []
        for resource_id in resource_ids or []:
            if resource_id not in self.resources:
                raise TribeError(f"no resource '{resource_id}'")
            resources.append(resource_id)
        record = EconomicCommitmentRecord(
            id=new_id("commitment"),
            ts=now_iso(),
            title=title.strip(),
            description=description.strip(),
            committed_by=actor.name,
            owed_by=owed_by_member.name,
            owed_to=owed_to_name,
            resource_ids=resources,
            task_id=task_id,
            due_ts=due_ts,
            status=(status or "open").strip() or "open",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        if not record.title:
            raise TribeError("commitment title cannot be empty")
        self._emit("commitment_recorded", actor.name, {"commitment": record.model_dump()})
        return record

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
    ) -> EconomicAgreementRecord:
        actor = self._require_member(created_by)
        resolved_parties = [self._require_member(name).name for name in parties]
        if len(resolved_parties) < 2:
            raise TribeError("agreement requires at least two parties")
        commitment_list = []
        for commitment_id in commitment_ids or []:
            if commitment_id not in self.commitments:
                raise TribeError(f"no commitment '{commitment_id}'")
            commitment_list.append(commitment_id)
        record = EconomicAgreementRecord(
            id=new_id("agreement"),
            ts=now_iso(),
            title=title.strip(),
            description=description.strip(),
            created_by=actor.name,
            parties=resolved_parties,
            commitment_ids=commitment_list,
            status=(status or "active").strip() or "active",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        if not record.title:
            raise TribeError("agreement title cannot be empty")
        self._emit("agreement_recorded", actor.name, {"agreement": record.model_dump()})
        return record

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
    ) -> TribeEconomyProfileRecord:
        actor = self._require_member(created_by)
        value_types = [item.strip() for item in recognized_value_types if item.strip()]
        if not value_types:
            raise TribeError("economy profile requires at least one recognized value type")
        record = TribeEconomyProfileRecord(
            id=new_id("economy"),
            ts=now_iso(),
            created_by=actor.name,
            mission=mission.strip(),
            recognized_value_types=value_types,
            distribution_logic=distribution_logic.strip(),
            governance_style=governance_style.strip(),
            pricing_modes=[item.strip() for item in (pricing_modes or []) if item.strip()],
            solidarity_policy=solidarity_policy.strip(),
            external_alliances=[item.strip() for item in (external_alliances or []) if item.strip()],
            notes=notes.strip(),
            status=(status or "active").strip() or "active",
            meta=dict(meta or {}),
        )
        if not record.mission:
            raise TribeError("economy profile mission cannot be empty")
        if not record.distribution_logic:
            raise TribeError("economy profile distribution logic cannot be empty")
        if not record.governance_style:
            raise TribeError("economy profile governance style cannot be empty")
        self._emit("economy_profile_defined", actor.name, {"economy_profile": record.model_dump()})
        return record

    def current_economy_profile(self) -> Optional[TribeEconomyProfileRecord]:
        if not self.economy_profiles:
            return None
        return sorted(self.economy_profiles.values(), key=lambda item: item.ts)[-1]

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
    ) -> FederationAgreementRecord:
        actor = self._require_member(created_by)
        partner_name = partner_tribe.strip()
        if not partner_name:
            raise TribeError("federation partner tribe cannot be empty")
        if partner_name.lower() == self.name.strip().lower():
            raise TribeError("federation partner tribe must differ from the local tribe")
        resolved_resources: list[str] = []
        for resource_id in resource_ids or []:
            if resource_id not in self.resources:
                raise TribeError(f"no resource '{resource_id}'")
            resolved_resources.append(resource_id)
        resolved_related: list[str] = []
        for agreement_id in related_agreement_ids or []:
            if agreement_id not in self.agreements:
                raise TribeError(f"no agreement '{agreement_id}'")
            resolved_related.append(agreement_id)
        record = FederationAgreementRecord(
            id=new_id("federation"),
            ts=now_iso(),
            created_by=actor.name,
            title=title.strip(),
            partner_tribe=partner_name,
            partner_slug=partner_slug.strip() if partner_slug else None,
            agreement_type=(agreement_type or "alliance").strip() or "alliance",
            scopes=[item.strip() for item in (scopes or []) if item.strip()],
            description=description.strip(),
            status=(status or "proposed").strip() or "proposed",
            resource_ids=resolved_resources,
            related_agreement_ids=resolved_related,
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        if not record.title:
            raise TribeError("federation agreement title cannot be empty")
        self._emit(
            "federation_agreement_recorded",
            actor.name,
            {"federation_agreement": record.model_dump()},
        )
        return record

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
    ) -> EconomicAgentRecord:
        actor = self._require_member(created_by)
        clean_name = (name or "").strip()
        if not clean_name:
            raise TribeError("economic agent name cannot be empty")
        record = EconomicAgentRecord(
            id=new_id("agent"),
            ts=now_iso(),
            name=clean_name,
            created_by=actor.name,
            role=(role or "member").strip() or "member",
            obligations=[item.strip() for item in (obligations or []) if item.strip()],
            claims=[item.strip() for item in (claims or []) if item.strip()],
            resource_ids=[resource_id for resource_id in (resource_ids or []) if resource_id in self.resources],
            contribution_ids=[contribution_id for contribution_id in (contribution_ids or []) if contribution_id in self.contributions],
            status=(status or "active").strip() or "active",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        self._emit("economic_agent_recorded", actor.name, {"economic_agent": record.model_dump()})
        return record

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
    ) -> ProtocolTermRecord:
        actor = self._require_member(created_by)
        clean_term = (term or "").strip()
        if not clean_term:
            raise TribeError("protocol term cannot be empty")
        clean_definition = (definition or "").strip()
        if not clean_definition:
            raise TribeError("protocol definition cannot be empty")
        record = ProtocolTermRecord(
            id=new_id("proto"),
            ts=now_iso(),
            term=clean_term,
            definition=clean_definition,
            created_by=actor.name,
            domain=(domain or "economic").strip() or "economic",
            tags=[item.strip() for item in (tags or []) if item.strip()],
            status=(status or "active").strip() or "active",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        self._emit("protocol_term_recorded", actor.name, {"protocol_term": record.model_dump()})
        return record

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
    ) -> CareRecord:
        target = self._require_member(member)
        actor = self._require_member(recorded_by)
        domain_clean = (domain or "social").strip().lower()
        if domain_clean not in {"physical", "mental", "social", "economic"}:
            raise TribeError("care domain must be physical, mental, social, or economic")
        record = CareRecord(
            id=new_id("care"),
            ts=now_iso(),
            member_id=target.id,
            member_name=target.name,
            care_type=(care_type or "check_in").strip() or "check_in",
            domain=domain_clean,
            summary=summary.strip(),
            beneficiaries=[self._require_member(name).name for name in (beneficiaries or [])],
            hours=float(hours or 0.0),
            notes=notes.strip(),
            recorded_by=actor.name,
            tags=[item.strip() for item in (tags or []) if item.strip()],
            meta=dict(meta or {}),
        )
        if not record.summary:
            raise TribeError("care summary cannot be empty")
        self._emit("care_recorded", actor.name, {"care": record.model_dump()})
        return record

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
    ) -> RhythmRecord:
        actor = self._require_member(created_by)
        record = RhythmRecord(
            id=new_id("rhythm"),
            ts=now_iso(),
            name=name.strip(),
            cadence=cadence.strip(),
            purpose=purpose.strip(),
            participants=[self._require_member(item).name for item in (participants or [])],
            care_required=bool(care_required),
            created_by=actor.name,
            status=(status or "active").strip() or "active",
            notes=notes.strip(),
            meta=dict(meta or {}),
        )
        if not record.name:
            raise TribeError("rhythm name cannot be empty")
        if not record.cadence:
            raise TribeError("rhythm cadence cannot be empty")
        if not record.purpose:
            raise TribeError("rhythm purpose cannot be empty")
        self._emit("rhythm_defined", actor.name, {"rhythm": record.model_dump()})
        return record

    def proposal_summary(self, proposal_id: str) -> dict[str, Any]:
        p = self._require_proposal(proposal_id)
        decision = None
        for item in reversed(self.decisions):
            if item.proposal_id == p.id:
                decision = item
                break

        def _theme_keywords(reason: str) -> list[str]:
            text = (reason or "").lower()
            keywords = []
            for token in ["consent", "privacy", "risk", "trust", "cost", "justice", "data", "labor", "care", "safety", "speed"]:
                if token in text:
                    keywords.append(token)
            return keywords or ["general"]

        objections = [
            {
                "member": self.members.get(v.member).name if self.members.get(v.member) else v.member,
                "position": v.position.value,
                "reason": v.reason or "",
                "theme_keywords": _theme_keywords(v.reason or ""),
            }
            for v in p.votes.values()
            if v.position in (Position.AGAINST, Position.BLOCK)
        ]
        dissent_summary = decision.dissent if decision is not None else objections
        if decision is None:
            tally = self.tally(p.id)
            payload = {
                "proposal_id": p.id,
                "title": p.title,
                "decision": {
                    "outcome": "pending",
                    "rule": p.rule.value,
                    "votes_cast": tally["votes_cast"],
                    "quorum_met": tally["quorum_met"],
                    "tally": tally["counts"],
                },
                "major_objections": objections,
                "dissent_summary": dissent_summary,
                "counsel": [],
            }
        else:
            payload = {
                "proposal_id": p.id,
                "title": p.title,
                "decision": {
                    "outcome": decision.outcome.value,
                    "rule": decision.rule.value,
                    "votes_cast": decision.votes_cast,
                    "quorum_met": decision.votes_cast >= decision.quorum_required,
                    "tally": decision.tally,
                },
                "major_objections": objections or decision.dissent,
                "dissent_summary": dissent_summary,
                "counsel": [
                    {
                        "member": msg.author,
                        "kind": msg.kind,
                        "text": msg.text,
                        "ts": msg.ts,
                        "meta": msg.meta,
                    }
                    for msg in reversed(self.messages)
                    if msg.kind == "counsel" and str(msg.meta.get("proposal_id", "")) == p.id
                ],
            }

        if not payload["counsel"]:
            payload["counsel"] = [
                {
                    "member": msg.author,
                    "kind": msg.kind,
                    "text": msg.text,
                    "ts": msg.ts,
                    "meta": msg.meta,
                }
                for msg in reversed(self.messages)
                if msg.kind == "counsel" and str(msg.meta.get("proposal_id", "")) in {"", p.id}
            ][:5]

        return payload

    def close_proposal(self, proposal_id: str, closed_by: str) -> Decision:
        """Compute the outcome from cast votes and record a decision."""
        p = self._require_proposal(proposal_id)
        if p.status != ProposalStatus.OPEN:
            raise TribeError(f"proposal '{proposal_id}' is already {p.status.value}")
        closer = self._require_member(closed_by)

        counts = {pos.value: 0 for pos in Position}
        for v in p.votes.values():
            member = self.members.get(v.member)
            if member is None or not member.voting:
                continue
            counts[v.position.value] += 1
        votes_cast = sum(counts.values())
        n_voting = len(self.voting_members())
        quorum_met = votes_cast >= p.quorum

        if not quorum_met:
            outcome = Outcome.FAILED_QUORUM
        elif p.rule == Rule.UNANIMITY:
            outcome = (
                Outcome.ADOPTED
                if counts[Position.FOR.value] == n_voting and n_voting > 0
                else Outcome.REJECTED
            )
        elif p.rule == Rule.CONSENSUS:
            opposed = counts[Position.AGAINST.value] + counts[Position.BLOCK.value]
            outcome = (
                Outcome.ADOPTED
                if opposed == 0 and counts[Position.FOR.value] > 0
                else Outcome.REJECTED
            )
        else:  # MAJORITY
            opposed = counts[Position.AGAINST.value] + counts[Position.BLOCK.value]
            outcome = (
                Outcome.ADOPTED
                if counts[Position.FOR.value] > opposed
                else Outcome.REJECTED
            )

        # Dissent is recorded, never discarded.
        dissent: list[dict[str, Any]] = []
        for v in p.votes.values():
            member = self.members.get(v.member)
            if member is None or not member.voting:
                continue
            if v.position in (Position.AGAINST, Position.BLOCK):
                dissent.append(
                    {
                        "member": member.name,
                        "position": v.position.value,
                        "reason": v.reason or "",
                    }
                )

        decision = Decision(
            id=new_id("dec"),
            ts=now_iso(),
            proposal_id=p.id,
            proposal_title=p.title,
            rule=p.rule,
            outcome=outcome,
            tally=counts,
            quorum_required=p.quorum,
            votes_cast=votes_cast,
            closed_by=closer.name,
            dissent=dissent,
        )
        p.status = (
            ProposalStatus.ADOPTED
            if outcome == Outcome.ADOPTED
            else ProposalStatus.REJECTED
            if outcome == Outcome.REJECTED
            else ProposalStatus.FAILED_QUORUM
        )
        p.outcome = outcome
        self._emit("proposal_closed", closer.name, {"decision": decision.model_dump()})
        self.remember(
            title=f"Decision: {p.title}",
            text=(
                f"{outcome.value} under {p.rule.value} rule "
                f"({votes_cast}/{p.quorum} quorum). "
                + (f"Dissent: {dissent}." if dissent else "No dissent recorded.")
            ),
            kind="decision",
            author=closer.name,
            tags=["decision", outcome.value],
        )
        return decision

    # ------------------------------------------------------ LLM interface

    def context_for_llm(self, limit: int = 20) -> str:
        """Compact context so a technological node can speak with awareness."""
        lines: list[str] = []
        cfg = self.store.read_config()
        lines.append(f"Tribe: {cfg.get('name', '?')}")
        charter = cfg.get("charter", "")
        if charter:
            lines.append(f"Charter: {charter}")
        roster = ", ".join(
            f"{m.name} ({m.kind.value}, {'voting' if m.voting else 'voice'})"
            for m in self.members.values()
        )
        lines.append(f"Members: {roster}")
        lines.append("Member layer summaries:")
        for m in self.members.values():
            summary = format_member_layers(m).strip()
            if summary:
                lines.append(f"- {m.name}:")
                lines.append(summary)
        recent = [m for m in self.messages if m.kind != "system"][-limit:]
        if recent:
            lines.append("Recent conversation:")
            for msg in recent:
                lines.append(f"{msg.author}: {msg.text}")
        open_props = [
            p for p in self.proposals.values() if p.status == ProposalStatus.OPEN
        ]
        if open_props:
            lines.append("Open proposals:")
            for p in open_props:
                lines.append(f"- [{p.id}] {p.title}: {p.text} (rule={p.rule.value})")
        memories = [
            e for e in sorted(self.memory.values(), key=lambda e: e.ts)
            if e.scope == "tribe"
        ][-8:]
        if memories:
            lines.append("Shared memory:")
            for e in memories:
                lines.append(f"- {e.title}: {e.text[:200]}")
        if self.lexicon:
            lines.append("Tribe lexicon:")
            for entry in list(sorted(self.lexicon.values(), key=lambda item: item.ts))[-5:]:
                aliases = f" aliases={','.join(entry.aliases)}" if entry.aliases else ""
                lines.append(f"- {entry.term}: {entry.definition[:160]}{aliases}")
        if self.memberships:
            lines.append("Membership registry:")
            for record in list(sorted(self.memberships.values(), key=lambda item: item.ts))[-5:]:
                circles = f" circles={','.join(record.circles)}" if record.circles else ""
                lines.append(f"- {record.member_name}: role={record.role} status={record.status}{circles}")
        if self.devices:
            lines.append("Registered devices:")
            for device in list(self.devices.values())[-5:]:
                target = device.owner or device.linked_member_id or "unassigned"
                lines.append(f"- {device.name} ({device.kind}, {device.status}) owner={target}")
        if self.governance_rules:
            lines.append("Governance rules:")
            for record in list(sorted(self.governance_rules.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.title} [{record.scope}/{record.kind}] status={record.status}")
        if self.intents:
            lines.append("Open intents:")
            for record in list(sorted(self.intents.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.title} ({record.kind}, {record.status})")
        if self.commitments:
            lines.append("Commitments:")
            for record in list(sorted(self.commitments.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.title}: {record.owed_by} -> {record.owed_to or 'tribe'} [{record.status}]")
        if self.agreements:
            lines.append("Agreements:")
            for record in list(sorted(self.agreements.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.title}: parties={', '.join(record.parties)}")
        profile = self.current_economy_profile()
        if profile is not None:
            lines.append("Current economy profile:")
            lines.append(
                f"- mission: {profile.mission[:180]} | values={', '.join(profile.recognized_value_types)}"
            )
            lines.append(
                f"- governance={profile.governance_style} | distribution={profile.distribution_logic[:160]}"
            )
        if self.federation_agreements:
            lines.append("Federation agreements:")
            for record in list(sorted(self.federation_agreements.values(), key=lambda item: item.ts))[-5:]:
                scopes = f" scopes={','.join(record.scopes)}" if record.scopes else ""
                lines.append(
                    f"- {record.title}: partner={record.partner_tribe} "
                    f"type={record.agreement_type} status={record.status}{scopes}"
                )
        if self.work_logs:
            lines.append("Recent work logs:")
            for record in list(sorted(self.work_logs.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.member_name} {record.hours:g}h {record.kind}: {record.description}")
        if self.care_log:
            lines.append("Recent care records:")
            for record in list(sorted(self.care_log.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.member_name} {record.care_type}/{record.domain}: {record.summary}")
        if self.rhythms:
            lines.append("Tribe rhythms:")
            for record in list(sorted(self.rhythms.values(), key=lambda item: item.ts))[-5:]:
                lines.append(f"- {record.name}: {record.cadence} ({record.purpose})")
        if self.entity_links:
            lines.append("Recent entity links:")
            for link in self.entity_links[-5:]:
                lines.append(
                    f"- {link.source.kind}:{link.source.id} -[{link.relation}]-> "
                    f"{link.target.kind}:{link.target.id}"
                )
        if self.physical_events:
            lines.append("Recent physical events:")
            for event in self.physical_events[-5:]:
                lines.append(f"- {event.event_type}: {event.description}")
        return "\n".join(lines)
