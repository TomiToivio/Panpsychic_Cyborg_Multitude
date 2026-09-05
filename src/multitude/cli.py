# -*- coding: utf-8 -*-
"""CLI for the tribe kernel.

Usage examples:
  multitude found --name "First Tribe" --founder alice
  multitude join --as "Panpsychic Cyborg Multitude" --kind technological --model glm-5.3-flash:cloud
  multitude say --as alice --text "Welcome, all nodes."
  multitude counsel --as "Panpsychic Cyborg Multitude" --topic "our first shared goal"
  multitude propose --by alice --title "Ritual" --text "We meet every full moon."
  multitude vote --as alice --proposal prop-... --position for --reason "Yes"
  multitude tally --proposal prop-...
  multitude close --by alice --proposal prop-...
  multitude members / log / status / search
  multitude layers --as alice                      # show one node's six layers
  multitude layer-set --as alice --layer physical --set location=Helsinki --set notes="at home"
  multitude layer-history --as alice --layer biological
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from multitude import config
from multitude.interfaces.web import run_api_server
from multitude.layers import ALIASES, LayerError, format_member_layers
from multitude.models import Layer, NodeKind, Position, ProposalStatus, Rule
from multitude.service import MultitudeService
from multitude.store import TribeStore
from multitude.tribe import Tribe, TribeError

# Layer fields that hold lists of values; --set accepts comma-separated them.
LIST_KEYS = {
    "languages",
    "vocabularies",
    "needs",
    "close_ties",
    "wider_networks",
    "systems",
    "network_links",
    "devices",
}


def _parse_gps(value: str) -> dict[str, float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2:
        raise TribeError("--gps expects lat,lon")
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError as exc:
        raise TribeError("--gps expects numeric lat,lon") from exc
    return {"lat": lat, "lon": lon}


def _load_tribe(args: argparse.Namespace) -> Tribe:
    tribe_dir = config.find_tribe_dir(getattr(args, "tribe", None))
    return Tribe(TribeStore(tribe_dir))


def cmd_found(args: argparse.Namespace) -> int:
    root = config.tribes_root()
    tribe = Tribe.found(root, args.name, args.charter, args.founder)
    print(f"founded: {tribe.name}")
    print(f"tribe dir: {tribe.store.path}")
    print(f"founder: {args.founder} (biological, voting)")
    return 0


def cmd_join(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    kind = NodeKind.BIOLOGICAL if args.kind == "biological" else NodeKind.TECHNOLOGICAL
    m = tribe.join(
        args.as_name,
        kind,
        persona=args.persona,
        model=args.model,
        voting=not args.no_vote,
    )
    print(f"joined: {m.name} ({m.kind.value}, {'voting' if m.voting else 'voice'})")
    return 0


def cmd_say(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    msg = tribe.say(args.as_name, args.text)
    print(f"[{msg.ts}] {msg.author}: {msg.text}")
    return 0


def cmd_counsel(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    msg = MultitudeService(tribe).counsel(args.as_name, topic=args.topic, model=args.model)
    if msg is not None:
        print(f"[{msg['ts']}] {msg['author']} (counsel): {msg['text']}")
        print(f"  model: {msg.get('meta', {}).get('model', '?')}")
    return 0 if msg is not None else 1


def cmd_propose(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    p = MultitudeService(tribe).create_proposal(author=args.by, title=args.title, text=args.text, rule=args.rule)
    print(f"proposal {p['id']} OPEN: {p['title']}")
    print(f"  rule={p['rule']} quorum={p['quorum']}")
    return 0


def cmd_vote(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    result = MultitudeService(tribe).vote(args.proposal, args.as_name, args.position, reason=args.reason)
    t = result["tally"]
    print(f"vote recorded: {args.as_name} -> {args.position}")
    print(f"tally: {t['counts']} (cast {t['votes_cast']}, quorum {t['quorum']})")
    return 0


def cmd_proposals(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    shown = 0
    for p in tribe.proposals.values():
        if args.open and p.status != ProposalStatus.OPEN:
            continue
        votes = f" votes={len(p.votes)}" if p.votes else ""
        if p.status == ProposalStatus.OPEN:
            state = "OPEN"
        else:
            state = f"CLOSED: {p.outcome.value}" if p.outcome else "CLOSED"
        print(f"  [{state}] {p.id}: {p.title}{votes}")
        print(f"      by {p.opened_by}, rule {p.rule.value}, opened {p.opened_ts}")
        if args.verbose and p.text:
            print(f"      {p.text[:160]}")
        if args.verbose and p.votes:
            for v in p.votes.values():
                reason = f" ({v.reason})" if v.reason else ""
                print(f"      vote: {v.member} -> {v.position.value}{reason}")
        shown += 1
    if not shown:
        print("no proposals" if not args.open else "no open proposals")
        return 1
    return 0


def cmd_tally(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    t = tribe.tally(args.proposal)
    print(json.dumps(t, indent=2, ensure_ascii=False))
    return 0


def cmd_close(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    d = tribe.close_proposal(args.proposal, closed_by=args.by)
    print(f"decision {d.id}: {d.outcome.value} ({d.rule.value} rule)")
    print(f"  tally: {d.tally} | votes {d.votes_cast}/{d.quorum_required} quorum")
    for row in d.dissent:
        print(f"  dissent: {row['member']} ({row['position']}): {row['reason'] or '-'}")
    return 0


def cmd_members(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    print(f"tribe: {tribe.name}")
    for m in MultitudeService(tribe).list_agents():
        persona = f" - {m['persona']}" if m.get("persona") else ""
        model = f" [model: {m['model']}]" if m.get("model") else ""
        print(
            f"  {m['name']} ({m['kind']}, {'voting' if m['voting'] else 'voice'})"
            f"{persona}{model}"
        )
    return 0


def cmd_member_update(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    service = MultitudeService(tribe)
    updated = service.update_member(
        args.name,
        voting=None if args.voting is None else args.voting == "voting",
        persona=args.persona,
        model=args.model,
    )
    print(
        f"updated {updated['name']}: "
        f"{'voting' if updated['voting'] else 'voice-only'}"
    )
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    updated = MultitudeService(tribe).promote(args.name, actor=args.by)
    print(f"promoted {updated['name']} -> voting member")
    return 0


def cmd_demote(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    updated = MultitudeService(tribe).demote(args.name, actor=args.by)
    print(f"demoted {updated['name']} -> voice-only")
    return 0


# ---------------------------------------------------------------- layers


def _parse_set_pairs(pairs: list[str]) -> dict:
    """Parse --set key=value pairs; list fields split comma-separated values."""
    changes: dict = {}
    for item in pairs:
        if "=" not in item:
            raise TribeError(f"--set expects key=value, got: {item}")
        key, _, val = item.partition("=")
        key = ALIASES.get(key.strip(), key.strip())
        if key in LIST_KEYS:
            changes[key] = [v.strip() for v in val.split(",") if v.strip()]
        else:
            changes[key] = val.strip()
    return changes


def cmd_layers(args: argparse.Namespace) -> int:
    from multitude.layers import format_member_layers

    tribe = _load_tribe(args)
    if args.as_name:
        m = tribe._require_member(args.as_name)
        print(f"tribe: {tribe.name}")
        print(f"node: {m.name} ({m.kind.value})")
        print(format_member_layers(m) or "  (no layer data)")
        return 0
    print(f"tribe: {tribe.name}")
    for m in tribe.members.values():
        print(f"node: {m.name} ({m.kind.value})")
        print(format_member_layers(m))
    return 0


def cmd_layer_set(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    changes = _parse_set_pairs(args.set)
    tribe.record_layer(
        args.as_name,
        args.layer,
        data=changes,
        reported_by=args.reported_by,
        visible=not args.private,
    )
    who = args.reported_by or args.as_name
    print(f"recorded: {args.layer} layer of {args.as_name} (reported by {who})")
    return 0


def cmd_layer_history(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    events = tribe.layer_history(args.as_name, args.layer)
    if not events:
        print("no layer records")
        return 1
    for ev in events:
        described = "; ".join(
            f"{k}={v}" for k, v in ev.get("changes", {}).items()
        )
        hidden = "" if ev.get("visible", True) else " [private]"
        print(
            f"[{ev.get('ts', '')}] {ev.get('reported_by', '?')}: "
            f"{described[:300]}{hidden}"
        )
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    events = tribe.store.replay()
    for ev in events[-args.limit :]:
        print(f"[{ev.ts}] {ev.type} ({ev.actor})")
        for k, v in ev.payload.items():
            s = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
            print(f"    {k}: {s[:300]}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    data = MultitudeService(tribe).status()
    print(f"tribe: {data['tribe']}")
    print(
        f"members: {data['members']} "
        f"({data['biological_members']} biological, {data['technological_members']} technological)"
    )
    print(f"messages: {data['messages']}")
    print(f"memory entries: {data['memory_entries']}")
    print(f"decisions: {data['decisions']}")
    print(f"lexicon terms: {data['lexicon_terms']}")
    print(f"devices: {data['devices']}")
    print(f"physical events: {data['physical_events']}")
    for proposal_id in data["open_proposal_ids"]:
        p = tribe.proposals[proposal_id]
        print(f"open proposal {p.id}: {p.title}")
    return 0


def cmd_lexicon_add(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    entry = tribe.define_term(
        args.term,
        args.definition,
        added_by=args.by,
        aliases=args.alias,
        tags=args.tag,
    )
    print(f"defined: {entry.term}")
    return 0


def cmd_lexicon(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    entries = tribe.search_lexicon(args.query) if args.query else list(
        sorted(tribe.lexicon.values(), key=lambda item: item.ts)
    )
    if not entries:
        print("no lexicon entries")
        return 1
    for entry in entries:
        aliases = f" aliases={', '.join(entry.aliases)}" if entry.aliases else ""
        tags = f" tags={', '.join(entry.tags)}" if entry.tags else ""
        print(f"- {entry.term}:{aliases}{tags}")
        print(f"    {entry.definition}")
    return 0


def cmd_device_register(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    device = tribe.register_device(
        registered_by=args.by,
        name=args.name,
        kind=args.kind,
        owner=args.owner,
        linked_member=args.member,
        interface_modes=args.interface,
        location_label=args.location or None,
        gps=_parse_gps(args.gps) if args.gps else None,
        notes=args.notes,
    )
    print(f"registered: {device.id} {device.name} ({device.kind})")
    return 0


def cmd_devices(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    if not tribe.devices:
        print("no devices")
        return 1
    members = {member.id: member.name for member in tribe.members.values()}
    for device in sorted(tribe.devices.values(), key=lambda item: item.registered_ts):
        linked = members.get(device.linked_member_id or "", device.linked_member_id or "")
        owner = device.owner or linked or "-"
        location = device.location_label or "-"
        print(f"- {device.id} {device.name} ({device.kind}, {device.status}) owner={owner} location={location}")
    return 0


def cmd_physical_event(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    event = tribe.record_physical_event(
        reported_by=args.by,
        event_type=args.type,
        description=args.description,
        members=args.member,
        devices=args.device,
        location_label=args.location or None,
        gps=_parse_gps(args.gps) if args.gps else None,
    )
    print(f"recorded: {event.id} {event.event_type}")
    return 0


def cmd_physical_events(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    if not tribe.physical_events:
        print("no physical events")
        return 1
    member_names = {member.id: member.name for member in tribe.members.values()}
    for event in tribe.physical_events[-args.limit:]:
        members = [member_names.get(member_id, member_id) for member_id in event.member_ids]
        devices = ", ".join(event.device_ids) if event.device_ids else "-"
        members_s = ", ".join(members) if members else "-"
        place = event.location_label or "-"
        print(f"[{event.ts}] {event.event_type} @ {place}")
        print(f"    members={members_s} devices={devices}")
        print(f"    {event.description}")
    return 0


def cmd_economy_profile_set(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    profile = MultitudeService(tribe).define_economy_profile(
        created_by=args.by,
        mission=args.mission,
        recognized_value_types=args.value_type,
        distribution_logic=args.distribution_logic,
        governance_style=args.governance_style,
        pricing_modes=args.pricing_mode,
        solidarity_policy=args.solidarity_policy,
        external_alliances=args.external_alliance,
        notes=args.notes,
        status=args.status,
    )
    print(f"economy profile: {profile['id']} [{profile['status']}]")
    print(f"  mission: {profile['mission']}")
    return 0


def cmd_economy_profile(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    profile = MultitudeService(tribe).current_economy_profile()
    if profile is None:
        print("no economy profile")
        return 1
    print(f"{profile['id']} [{profile['status']}]")
    print(f"  mission: {profile['mission']}")
    print(f"  values: {', '.join(profile['recognized_value_types'])}")
    print(f"  governance: {profile['governance_style']}")
    print(f"  distribution: {profile['distribution_logic']}")
    if profile["pricing_modes"]:
        print(f"  pricing: {', '.join(profile['pricing_modes'])}")
    if profile["external_alliances"]:
        print(f"  alliances: {', '.join(profile['external_alliances'])}")
    return 0


def cmd_federation_add(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_federation_agreement(
        created_by=args.by,
        title=args.title,
        partner_tribe=args.partner_tribe,
        partner_slug=args.partner_slug,
        agreement_type=args.agreement_type,
        scopes=args.scope,
        description=args.description,
        status=args.status,
        resource_ids=args.resource,
        related_agreement_ids=args.related_agreement,
        notes=args.notes,
    )
    print(f"federation agreement: {record['id']} [{record['status']}]")
    print(f"  partner: {record['partner_tribe']} type={record['agreement_type']}")
    return 0


def cmd_federations(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_federation_agreements()
    if not records:
        print("no federation agreements")
        return 1
    for record in records:
        scopes = f" scopes={','.join(record['scopes'])}" if record["scopes"] else ""
        print(
            f"- {record['id']} {record['title']} partner={record['partner_tribe']} "
            f"type={record['agreement_type']} status={record['status']}{scopes}"
        )
    return 0


def cmd_resource_register(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).register_resource(
        args.name, args.by, kind=args.kind, owner=args.owner, status=args.status
    )
    print(f"resource {record['id']} [{record['status']}]: {record['name']} ({record['kind']}, owner={record['owner']})")
    return 0


def cmd_resources(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = tribe.resources.values()
    shown = 0
    for r in sorted(records, key=lambda item: item.created_ts):
        if args.status and r.status != args.status:
            continue
        print(f"- {r.id} [{r.status}] {r.name} ({r.kind}, owner={r.owner})")
        shown += 1
    if not shown:
        print("no resources")
        return 1
    return 0


def cmd_resource_allocate(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).allocate_resource(
        args.resource, args.to, purpose=args.purpose, status=args.status
    )
    print(f"allocation {record['id']}: {record['resource_id']} -> {record['assignee']} [{record['status']}]")
    return 0


def cmd_work_log(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).log_work(
        member=args.as_name,
        description=args.description,
        hours=args.hours,
        logged_by=args.logged_by,
        kind=args.kind,
        task_id=args.task,
        goal_id=args.goal,
        tags=args.tag,
        notes=args.notes,
    )
    print(f"work log {record['id']}: {record['member_name']} {record['hours']}h {record['kind']}")
    return 0


def cmd_work_summary(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    summary = MultitudeService(tribe).work_summary()
    print("hours by member:")
    for name, hours in sorted(summary["hours_by_member"].items()):
        print(f"  {name}: {hours}h")
    print("hours by kind:")
    for kind, hours in sorted(summary["hours_by_kind"].items()):
        print(f"  {kind}: {hours}h")
    print(f"care hours (recorded via care log): {summary['care_hours']}h")
    print(f"open commitments: {len(summary['open_commitments'])}")
    for cm in summary["open_commitments"]:
        owed_to = f" -> {cm['owed_to']}" if cm["owed_to"] else ""
        due = f" (due {cm['due_ts']})" if cm.get("due_ts") else ""
        print(f"  - {cm['id']}: {cm['title']} [{cm['owed_by']}{owed_to}]{due}")
    if summary["costs_recorded"]:
        total = round(sum(item["cost_amount"] or 0.0 for item in summary["costs_recorded"]), 2)
        print(f"recorded costs: {total}")
    return 0


def cmd_intent_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_intent(
        title=args.title,
        created_by=args.by,
        description=args.description,
        kind=args.kind,
        target_members=args.target,
        resource_ids=args.resource,
        status=args.status,
        notes=args.notes,
    )
    print(f"intent {record['id']} [{record['kind']}]: {record['title']}")
    return 0


def cmd_intents(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_intents()
    if args.status:
        records = [r for r in records if r["status"] == args.status]
    if not records:
        print("no intents")
        return 1
    for record in records:
        print(f"- {record['id']} [{record['kind']}/{record['status']}]: {record['title']} (by {record['created_by']})")
    return 0


def cmd_commitment_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_commitment(
        title=args.title,
        committed_by=args.by,
        owed_by=args.owed_by,
        owed_to=args.owed_to,
        description=args.description,
        resource_ids=args.resource,
        task_id=args.task,
        due_ts=args.due,
        status=args.status,
        notes=args.notes,
    )
    print(f"commitment {record['id']} [{record['status']}]: {record['title']}")
    print(f"  owed by {record['owed_by']}" + (f" to {record['owed_to']}" if record["owed_to"] else ""))
    return 0


def cmd_commitments(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_commitments()
    if args.status:
        records = [r for r in records if r["status"] == args.status]
    if not records:
        print("no commitments")
        return 1
    for record in records:
        owed_to = f" -> {record['owed_to']}" if record["owed_to"] else ""
        due = f" (due {record['due_ts']})" if record.get("due_ts") else ""
        print(f"- {record['id']} [{record['status']}]: {record['title']} ({record['owed_by']}{owed_to}){due}")
    return 0


def cmd_agreement_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_agreement(
        title=args.title,
        created_by=args.by,
        parties=args.party,
        description=args.description,
        commitment_ids=args.commitment,
        status=args.status,
        notes=args.notes,
    )
    print(f"agreement {record['id']} [{record['status']}]: {record['title']}")
    print(f"  parties: {', '.join(record['parties'])}")
    return 0


def cmd_agreements(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_agreements()
    if not records:
        print("no agreements")
        return 1
    for record in records:
        print(f"- {record['id']} [{record['status']}]: {record['title']} — parties: {', '.join(record['parties'])}")
    return 0


def cmd_rule_define(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).define_governance_rule(
        title=args.title,
        description=args.description,
        defined_by=args.by,
        kind=args.kind,
        scope=args.scope,
        applies_to=args.applies_to,
        status=args.status,
    )
    print(f"governance rule {record['id']} [{record['status']}]: {record['title']} ({record['kind']}/{record['scope']})")
    return 0


def cmd_rules(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_governance_rules()
    if not records:
        print("no governance rules")
        return 1
    for record in records:
        print(f"- {record['id']} [{record['status']}] {record['title']} ({record['kind']}/{record['scope']})")
        if record["description"]:
            print(f"    {record['description'][:160]}")
    return 0


def cmd_care_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_care(
        member=args.member,
        summary=args.summary,
        recorded_by=args.by,
        care_type=args.type,
        domain=args.domain,
        beneficiaries=args.beneficiary,
        hours=args.hours,
        notes=args.notes,
        tags=args.tag,
    )
    print(f"care {record['id']}: {record['care_type']} for {record['member_name']} ({record['domain']}, {record['hours']}h)")
    return 0


def cmd_care(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_care_records()
    if args.member:
        records = [r for r in records if r["member_name"] == args.member]
    if not records:
        print("no care records")
        return 1
    for record in records:
        print(f"- {record['id']} {record['care_type']} for {record['member_name']} ({record['domain']}, {record['hours']}h): {record['summary'][:120]}")
    return 0


def cmd_rhythm_define(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).define_rhythm(
        name=args.name,
        cadence=args.cadence,
        purpose=args.purpose,
        created_by=args.by,
        participants=args.participant,
        care_required=args.care_required,
    )
    print(f"rhythm {record['id']} [{record['status']}]: {record['name']} ({record['cadence']})")
    return 0


def cmd_rhythms(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = MultitudeService(tribe).list_rhythms()
    if not records:
        print("no rhythms")
        return 1
    for record in records:
        care = " care-required" if record["care_required"] else ""
        print(f"- {record['id']} [{record['status']}] {record['name']} ({record['cadence']}){care}: {record['purpose'][:100]}")
    return 0


def cmd_term_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_protocol_term(
        term=args.term,
        definition=args.definition,
        created_by=args.by,
        domain=args.domain,
        tags=args.tag,
        status=args.status,
        notes=args.notes,
    )
    print(f"protocol term {record['id']} [{record['status']}]: {record['term']} ({record['domain']})")
    return 0


def cmd_terms(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = [item.model_dump() for item in sorted(tribe.protocol_terms.values(), key=lambda record: record.ts)]
    if args.domain:
        records = [r for r in records if r["domain"] == args.domain]
    if not records:
        print("no protocol terms")
        return 1
    for record in records:
        print(f"- {record['id']} [{record['domain']}] {record['term']}: {record['definition'][:140]}")
    return 0


def cmd_agent_record(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    record = MultitudeService(tribe).record_economic_agent(
        name=args.name,
        created_by=args.by,
        role=args.role,
        obligations=args.obligation,
        claims=args.claim,
        resource_ids=args.resource,
        contribution_ids=args.contribution,
        status=args.status,
        notes=args.notes,
    )
    print(f"economic agent {record['id']} [{record['status']}]: {record['name']} (role={record['role']})")
    if record["obligations"]:
        print(f"  obligations: {', '.join(record['obligations'])}")
    if record["claims"]:
        print(f"  claims: {', '.join(record['claims'])}")
    return 0


def cmd_agents(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    records = [item.model_dump() for item in sorted(tribe.economic_agents.values(), key=lambda record: record.ts)]
    if not records:
        print("no economic agents")
        return 1
    for record in records:
        print(f"- {record['id']} [{record['status']}] {record['name']} (role={record['role']})")
        if record["obligations"]:
            print(f"    obligations: {', '.join(record['obligations'])}")
    return 0


def cmd_remember(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    e = tribe.remember(
        args.title,
        args.text,
        author=args.as_name or "",
        kind=args.kind,
        tags=args.tags.split() if args.tags else [],
        scope=args.scope,
    )
    print(f"remembered: {e.id} - {e.title}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    hits = MultitudeService(tribe).search_memory(args.query)
    if not hits:
        print("no matches")
        return 1
    for e in hits:
        print(f"{e['id']} [{e['kind']}] {e['title']}")
        print(f"    {e['text'][:200]}")
    return 0


def cmd_entity_link(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    link = MultitudeService(tribe).link_entities(
        author=args.by,
        source_kind=args.source_kind,
        source=args.source,
        target_kind=args.target_kind,
        target=args.target,
        relation=args.relation,
    )
    print(
        f"linked: {link['source']['kind']}:{link['source']['id']} "
        f"-[{link['relation']}]-> {link['target']['kind']}:{link['target']['id']}"
    )
    print(f"  by {link['linked_by']} at {link['ts']}")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    links = MultitudeService(tribe).list_entity_links(
        entity_kind=args.kind,
        entity=args.entity,
        direction=args.direction,
        relation=args.relation,
    )
    if not links:
        print("no links")
        return 1
    for link in links:
        print(
            f"- {link['source']['kind']}:{link['source']['id']} "
            f"-[{link['relation']}]-> {link['target']['kind']}:{link['target']['id']}"
        )
        print(f"    by {link['linked_by']} at {link['ts']}")
    return 0


def cmd_private_note_add(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    note = MultitudeService(tribe).add_private_note(
        owner=args.as_name,
        title=args.title,
        text=args.text,
        kind=args.kind,
        tags=args.tags.split() if args.tags else [],
    )
    print(f"private note: {note['id']} - {note['title']}")
    return 0


def cmd_private_notes(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    notes = MultitudeService(tribe).list_private_notes(args.as_name)
    if not notes:
        print("no private notes")
        return 1
    for note in notes:
        print(f"- {note['id']} [{note['kind']}] {note['title']}")
        print(f"    {note['text'][:200]}")
    return 0


def cmd_private_note_publish(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    entry = MultitudeService(tribe).publish_private_note(
        owner=args.as_name,
        note_id=args.note,
        published_by=args.by,
        scope=args.scope,
        title=args.title or None,
        text=args.text or None,
        tags=args.tags.split() if args.tags else None,
        kind=args.kind or None,
    )
    print(f"published: {entry['id']} - {entry['title']} [{entry['scope']}]")
    print(f"  source private note: {entry['meta'].get('source_private_note_id', '?')}")
    return 0


def cmd_serve_api(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    return run_api_server(MultitudeService(tribe), host=args.host, port=args.port)


def cmd_telegram(args: argparse.Namespace) -> int:
    """Run the Telegram gateway through the canonical kernel entrypoint.

    Loads .env from the repo root if present so the bot token does not
    have to be exported by hand.
    """
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

    from multitude.integrations.telegram.gateway import main as gateway_main

    return gateway_main()


# --------------------------------------------------------------- scraping


def cmd_scrape(args: argparse.Namespace) -> int:
    from multitude.scraping import ScraperError, scrape_platform
    from multitude.scraping.storage import save_scrape_bundle

    out_path = args.out
    if not out_path:
        stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        label = "auto" if args.platform == "auto" else args.platform
        suffix = "4cat" if args.format == "4cat-x" else "normalized"
        out_path = str(Path("data") / "scrapes" / f"{label}-{suffix}-{stamp}.jsonl")
    try:
        session, written = scrape_platform(
            url=args.url,
            platform=args.platform,
            browser=args.browser,
            headless=args.headless,
            profile_dir=args.profile_dir,
            output_path=out_path,
            output_format=args.format,
            scrolls=args.scrolls,
            wait_ms=args.wait_ms,
            raw_dir=args.raw_dir,
        )
    except ScraperError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"platform: {session.platform}")
    print(f"url: {session.url}")
    print(f"items: {len(session.items)}")
    if written:
        print(f"saved: {written}")
    if session.items:
        bundle_path = Path(out_path)
        if args.format == "4cat-x":
            bundle_path = bundle_path.with_name(
                f"{bundle_path.stem}-normalized{bundle_path.suffix}"
            )
        bundle = save_scrape_bundle(session.items, bundle_path)
        print(f"sqlite: {bundle['sqlite']}")
        print(f"csv: {bundle['csv']}")
    return 0


# ---------------------------------------------------------- tribal goals


def cmd_goal_open(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    g = goals.open_goal(
        tribe, args.title, args.text, category=args.category, opened_by=args.by
    )
    print(f"goal {g.id} OPEN [{g.category}]: {g.title}")
    return None


def cmd_goals(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    shown = 0
    for g in tribe.goals.values():
        if args.category and g.category != args.category:
            continue
        print(f"  [{g.category}] {g.id} {g.status}: {g.title}")
        if g.text:
            print(f"      {g.text[:160]}")
        shown += 1
    if not shown:
        print("no goals")
        return 1
    return 0


def cmd_goal_close(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    g = goals.close_goal(
        tribe, args.goal, closed_by=args.by, status=args.status, notes=args.notes
    )
    print(f"goal {g.id} {g.status}: {g.title}")
    return 0


def cmd_task_open(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    t = goals.open_task(
        tribe,
        args.title,
        opened_by=args.by,
        description=args.text,
        goal_id=args.goal_id,
        skills=args.skills.split(),
    )
    skills = f" skills={t.skills}" if t.skills else ""
    goal = f" goal={t.goal_id}" if t.goal_id else ""
    print(f"task {t.id} OPEN: {t.title}{goal}{skills}")
    return 0


def cmd_tasks(args: argparse.Namespace) -> int:
    from multitude import goals as _goals  # noqa: F401

    tribe = _load_tribe(args)
    shown = 0
    for t in tribe.tasks.values():
        if args.status and t.status != args.status:
            continue
        extra = ""
        if t.status == "claimed":
            extra = f" (by {t.claimed_by})"
        elif t.status == "done":
            extra = f" (done by {t.done_by})"
        skills = f" skills={','.join(t.skills)}" if t.skills else ""
        print(f"  [{t.status}]{extra} {t.id}: {t.title}{skills}")
        shown += 1
    if not shown:
        print("no tasks")
        return 1
    return 0


def cmd_task_claim(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    t = goals.claim_task(tribe, args.task, args.as_name)
    print(f"claimed: {t.title} -> {args.as_name}")
    return 0


def cmd_task_done(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    t = goals.done_task(tribe, args.task, member=args.as_name)
    print(f"task done: {t.title} (by {t.done_by})")
    return 0


def cmd_task_assign(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    t = tribe.tasks.get(args.task)
    if t is None:
        print(f"error: no task '{args.task}'", file=sys.stderr)
        return 2
    ranked = goals.suggest_task_assignment(tribe, t)
    print("suggested order (best skill match first):")
    for name in ranked:
        print(f"  {name}")
    return 0


def cmd_profit_record(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    payload = goals.record_profit(
        tribe, args.amount, source=args.source, recorded_by=args.by
    )
    print(f"recorded: {payload['amount']} ({payload['source'] or 'no source'})")
    print(f"treasury total: {tribe.treasury['total']}")
    return 0


def cmd_profit_distribute(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    weights = None
    if args.weight:
        weights = {}
        for item in args.weight:
            if "=" not in item:
                print("error: --weight expects name=amount", file=sys.stderr)
                return 2
            name, _, val = item.partition("=")
            weights[name.strip()] = float(val)
    payload = goals.distribute_profit(tribe, args.amount, args.by, weights=weights)
    members = {m.id: m.name for m in tribe.members.values()}
    print(f"distributed {payload['amount']}:")
    for mid, amount in payload["distribution"].items():
        print(f"  {members.get(mid, mid)}: {amount}")
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    tribe = _load_tribe(args)
    print(f"treasury: {tribe.treasury['total']}")
    for p in tribe.treasury.get("entries", [])[-10:]:
        print(f"  +{p['amount']} from {p['source'] or '?'} [{p['ts']}]")
    members = {m.id: m.name for m in tribe.members.values()}
    if tribe.profit_ledger:
        print("profit shares:")
        for mid, amount in tribe.profit_ledger.items():
            print(f"  {members.get(mid, mid)}: {amount}")
    return 0


def cmd_wellbeing(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    if args.domain and args.level:
        payload = goals.record_wellbeing(
            tribe,
            args.as_name,
            args.domain,
            args.level,
            note=args.note,
            reported_by=args.reported_by,
        )
        print(f"recorded: {payload['member']} {payload['domain']}={payload['level']}")
        return 0
    # show mode
    wb = goals.latest_wellbeing(tribe, member=args.as_name)
    if args.as_name:
        doms = wb["by_member"].get(args.as_name, {})
        if not doms:
            print("no wellbeing readings")
            return 1
        for dom, lvl in doms.items():
            print(f"  {args.as_name} {dom}: {lvl}/5")
        return 0
    for name, doms in wb["by_member"].items():
        pretty = ", ".join(f"{d}={v}" for d, v in doms.items())
        print(f"  {name}: {pretty}")
    print(f"averages: {wb['averages']}")
    return 0


def cmd_interests(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    if args.add:
        items = [s.strip() for s in args.add.split(",") if s.strip()]
        payload = goals.declare_interests(tribe, args.as_name, items)
        print(f"declared for {payload['member']}: {payload['interests']}")
        return 0
    shared = goals.shared_interests(tribe)
    if not shared:
        print("no shared interests yet")
        return 1
    print("shared interests:")
    for item, names in shared.items():
        print(f"  {item}: {', '.join(names)}")
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    from multitude import goals

    tribe = _load_tribe(args)
    health = goals.tribe_health(tribe)
    wb = health["wellbeing"]
    print(f"tribe health: {tribe.name}")
    for name, doms in wb["by_member"].items():
        doms_str = ", ".join(f"{d}={v}/5" for d, v in doms.items())
        print(f"  {name}: {doms_str or 'no readings'}")
    if wb["averages"]:
        print(f"tribe averages: {wb['averages']}")
    shared = health["shared_interests"]
    if shared:
        print("shared interests:")
        for item, names in shared.items():
            print(f"  {item}: {', '.join(names)}")
    else:
        print("no shared interests recorded yet")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="multitude", description="Tribe kernel for hybrid human-AI groups"
    )
    parser.add_argument("--tribe", help="tribe directory (default: most recent)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("found", help="found a new tribe")
    p.add_argument("--name", required=True)
    p.add_argument("--charter", default="")
    p.add_argument("--founder", required=True)
    p.set_defaults(func=cmd_found)

    p = sub.add_parser("join", help="join the tribe as a new node")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--kind", choices=["biological", "technological"], default="biological")
    p.add_argument("--persona", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--no-vote", action="store_true", help="join as voice-only node")
    p.set_defaults(func=cmd_join)

    p = sub.add_parser("say", help="add a message to the stream")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--text", required=True)
    p.set_defaults(func=cmd_say)

    p = sub.add_parser("counsel", help="ask a technological node to speak")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--model", default=None)
    p.add_argument("--topic", default="")
    p.set_defaults(func=cmd_counsel)

    p = sub.add_parser("propose", help="open a proposal")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--rule", choices=[r.value for r in Rule], default="consensus")
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("vote", help="cast a vote")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--proposal", required=True)
    p.add_argument("--position", choices=[pos.value for pos in Position], required=True)
    p.add_argument("--reason", default=None)
    p.set_defaults(func=cmd_vote)

    p = sub.add_parser("tally", help="show current tally")
    p.add_argument("--proposal", required=True)
    p.set_defaults(func=cmd_tally)

    p = sub.add_parser("close", help="close a proposal and record the decision")
    p.add_argument("--by", required=True)
    p.add_argument("--proposal", required=True)
    p.set_defaults(func=cmd_close)

    p = sub.add_parser("proposals", help="list proposals (open and decided)")
    p.add_argument("--open", action="store_true", help="only open proposals")
    p.add_argument(
        "-v", "--verbose", action="store_true", help="show text and votes"
    )
    p.set_defaults(func=cmd_proposals)

    p = sub.add_parser("members", help="list members")
    p.set_defaults(func=cmd_members)

    p = sub.add_parser("member-update", help="update member metadata (voting/persona/model)")
    p.add_argument("--name", required=True)
    p.add_argument("--voting", choices=["voting", "voice"], default=None)
    p.add_argument("--persona", default=None)
    p.add_argument("--model", default=None)
    p.set_defaults(func=cmd_member_update)

    p = sub.add_parser("promote", help="grant voting rights to a voice-only member")
    p.add_argument("--name", required=True)
    p.add_argument("--by", default=None, help="actor recording the promotion")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("demote", help="revoke voting rights (member stays voice-only)")
    p.add_argument("--name", required=True)
    p.add_argument("--by", default=None, help="actor recording the demotion")
    p.set_defaults(func=cmd_demote)

    p = sub.add_parser("log", help="show raw event log")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("status", help="tribe summary")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("remember", help="write to shared memory")
    p.add_argument("--title", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--kind", default="note")
    p.add_argument("--tags", default="")
    p.add_argument("--scope", choices=["tribe", "research", "federated"], default="tribe")
    p.add_argument("--as", dest="as_name", default="")
    p.set_defaults(func=cmd_remember)

    p = sub.add_parser("search", help="search shared memory")
    p.add_argument("--query", required=True)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("private-note-add", help="write to a member's private local note store")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--kind", default="note")
    p.add_argument("--tags", default="")
    p.set_defaults(func=cmd_private_note_add)

    p = sub.add_parser("private-notes", help="list a member's private local notes")
    p.add_argument("--as", dest="as_name", required=True)
    p.set_defaults(func=cmd_private_notes)

    p = sub.add_parser("private-note-publish", help="publish one private note into shared memory")
    p.add_argument("--as", dest="as_name", required=True, help="private note owner")
    p.add_argument("--note", required=True)
    p.add_argument("--by", required=True, help="member who performs the publication")
    p.add_argument("--scope", choices=["tribe", "research", "federated"], default="tribe")
    p.add_argument("--title", default="")
    p.add_argument("--text", default="")
    p.add_argument("--kind", default="")
    p.add_argument("--tags", default="")
    p.set_defaults(func=cmd_private_note_publish)

    p = sub.add_parser("entity-link", help="record a typed link between two entities")
    p.add_argument("--by", required=True)
    p.add_argument("--source-kind", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--target-kind", required=True)
    p.add_argument("--target", required=True)
    p.add_argument("--relation", required=True)
    p.set_defaults(func=cmd_entity_link)

    p = sub.add_parser("links", help="list links touching one entity")
    p.add_argument("--kind", required=True)
    p.add_argument("--entity", required=True)
    p.add_argument("--direction", choices=["inbound", "outbound", "both"], default="both")
    p.add_argument("--relation", default=None)
    p.set_defaults(func=cmd_links)

    p = sub.add_parser("lexicon-add", help="define or update a tribe lexicon term")
    p.add_argument("--by", required=True)
    p.add_argument("--term", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--alias", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(func=cmd_lexicon_add)

    p = sub.add_parser("lexicon", help="list or search tribe lexicon")
    p.add_argument("--query", default="")
    p.set_defaults(func=cmd_lexicon)

    p = sub.add_parser("device-register", help="register a physical or cybernetic device")
    p.add_argument("--by", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True)
    p.add_argument("--owner", default="")
    p.add_argument("--member", default="")
    p.add_argument("--interface", action="append", default=[])
    p.add_argument("--location", default="")
    p.add_argument("--gps", default="")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_device_register)

    p = sub.add_parser("devices", help="list registered devices")
    p.set_defaults(func=cmd_devices)

    p = sub.add_parser("physical-event", help="record an event in physical space")
    p.add_argument("--by", required=True)
    p.add_argument("--type", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--member", action="append", default=[])
    p.add_argument("--device", action="append", default=[])
    p.add_argument("--location", default="")
    p.add_argument("--gps", default="")
    p.set_defaults(func=cmd_physical_event)

    p = sub.add_parser("physical-events", help="list recent physical events")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_physical_events)

    p = sub.add_parser("economy-profile-set", help="record the tribe's current intentional economy profile")
    p.add_argument("--by", required=True)
    p.add_argument("--mission", required=True)
    p.add_argument("--value-type", action="append", required=True)
    p.add_argument("--distribution-logic", required=True)
    p.add_argument("--governance-style", required=True)
    p.add_argument("--pricing-mode", action="append", default=[])
    p.add_argument("--external-alliance", action="append", default=[])
    p.add_argument("--solidarity-policy", default="")
    p.add_argument("--notes", default="")
    p.add_argument("--status", default="active")
    p.set_defaults(func=cmd_economy_profile_set)

    p = sub.add_parser("economy-profile", help="show the latest tribe economy profile")
    p.set_defaults(func=cmd_economy_profile)

    p = sub.add_parser("federation-add", help="record an inter-tribal federation agreement")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--partner-tribe", required=True)
    p.add_argument("--partner-slug")
    p.add_argument("--agreement-type", default="alliance")
    p.add_argument("--scope", action="append", default=[])
    p.add_argument("--description", default="")
    p.add_argument("--status", default="proposed")
    p.add_argument("--resource", action="append", default=[])
    p.add_argument("--related-agreement", action="append", default=[])
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_federation_add)

    p = sub.add_parser("federations", help="list recorded federation agreements")
    p.set_defaults(func=cmd_federations)

    # ---- work / commons commands (Priority 1) ----
    p = sub.add_parser("resource-register", help="register a shared resource (device, material, space)")
    p.add_argument("--by", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--kind", default="resource")
    p.add_argument("--owner", default="tribe")
    p.add_argument("--status", default="available")
    p.set_defaults(func=cmd_resource_register)

    p = sub.add_parser("resources", help="list registered resources")
    p.add_argument("--status", default=None)
    p.set_defaults(func=cmd_resources)

    p = sub.add_parser("resource-allocate", help="allocate a resource to a member with a purpose")
    p.add_argument("--resource", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--purpose", default="")
    p.add_argument("--status", default="allocated")
    p.set_defaults(func=cmd_resource_allocate)

    p = sub.add_parser("work-log", help="log hours of work (labor/care/maintenance/governance)")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--hours", type=float, required=True)
    p.add_argument("--kind", default="labor", choices=["labor", "care", "governance", "maintenance", "research", "coordination"])
    p.add_argument("--logged-by", default=None)
    p.add_argument("--task", default=None)
    p.add_argument("--goal", default=None)
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_work_log)

    p = sub.add_parser("work-summary", help="derived work view: hours by member/kind, open obligations, costs")
    p.set_defaults(func=cmd_work_summary)

    p = sub.add_parser("intent-record", help="record an economic intent (need/offer/request/proposal)")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--kind", default="need", choices=["need", "offer", "request", "proposal"])
    p.add_argument("--target", action="append", default=[])
    p.add_argument("--resource", action="append", default=[])
    p.add_argument("--status", default="open")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_intent_record)

    p = sub.add_parser("intents", help="list recorded intents")
    p.add_argument("--status", default=None)
    p.set_defaults(func=cmd_intents)

    p = sub.add_parser("commitment-record", help="record an obligation (who owes what to whom, due date)")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--owed-by", required=True)
    p.add_argument("--owed-to", default="")
    p.add_argument("--description", default="")
    p.add_argument("--resource", action="append", default=[])
    p.add_argument("--task", default=None)
    p.add_argument("--due", default=None, help="ISO timestamp")
    p.add_argument("--status", default="open")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_commitment_record)

    p = sub.add_parser("commitments", help="list recorded commitments (obligations)")
    p.add_argument("--status", default=None)
    p.set_defaults(func=cmd_commitments)

    p = sub.add_parser("agreement-record", help="record an agreement binding 2+ parties and commitments")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--party", action="append", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--commitment", action="append", default=[])
    p.add_argument("--status", default="active")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_agreement_record)

    p = sub.add_parser("agreements", help="list recorded agreements")
    p.set_defaults(func=cmd_agreements)

    p = sub.add_parser("rule-define", help="define a governance rule (policy/access/economic/care/moderation)")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--kind", default="policy", choices=["policy", "access", "economic", "care", "moderation"])
    p.add_argument("--scope", default="tribe", choices=["tribe", "business", "social", "health", "federated"])
    p.add_argument("--applies-to", action="append", default=[])
    p.add_argument("--status", default="active")
    p.set_defaults(func=cmd_rule_define)

    p = sub.add_parser("rules", help="list defined governance rules")
    p.set_defaults(func=cmd_rules)

    p = sub.add_parser("care-record", help="record care work (check-in, support, mediation, rest, celebration)")
    p.add_argument("--by", required=True)
    p.add_argument("--member", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--type", dest="type", default="check_in", choices=["check_in", "support", "mediation", "rest", "celebration"])
    p.add_argument("--domain", default="social", choices=["physical", "mental", "social", "economic"])
    p.add_argument("--beneficiary", action="append", default=[])
    p.add_argument("--hours", type=float, default=0.0)
    p.add_argument("--notes", default="")
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(func=cmd_care_record)

    p = sub.add_parser("care", help="list care records (optionally by member)")
    p.add_argument("--member", default=None)
    p.set_defaults(func=cmd_care)

    p = sub.add_parser("rhythm-define", help="define a tribe rhythm (recurring practice with cadence)")
    p.add_argument("--by", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--cadence", required=True)
    p.add_argument("--purpose", required=True)
    p.add_argument("--participant", action="append", default=[])
    p.add_argument("--care-required", action="store_true")
    p.set_defaults(func=cmd_rhythm_define)

    p = sub.add_parser("rhythms", help="list defined rhythms")
    p.set_defaults(func=cmd_rhythms)

    p = sub.add_parser("term-record", help="define a protocol term (shared vocabulary entry)")
    p.add_argument("--by", required=True)
    p.add_argument("--term", required=True)
    p.add_argument("--definition", required=True)
    p.add_argument("--domain", default="economic", choices=["economic", "governance", "care", "technical", "research"])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--status", default="active")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_term_record)

    p = sub.add_parser("terms", help="list protocol terms (optionally by domain)")
    p.add_argument("--domain", default=None, choices=["economic", "governance", "care", "technical", "research"])
    p.set_defaults(func=cmd_terms)

    p = sub.add_parser("agent-record", help="record an economic agent (role, obligations, claims)")
    p.add_argument("--by", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--role", default="member")
    p.add_argument("--obligation", action="append", default=[])
    p.add_argument("--claim", action="append", default=[])
    p.add_argument("--resource", action="append", default=[])
    p.add_argument("--contribution", action="append", default=[])
    p.add_argument("--status", default="active")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_agent_record)

    p = sub.add_parser("agents", help="list recorded economic agents")
    p.set_defaults(func=cmd_agents)

    p = sub.add_parser("serve-api", help="run the minimal shared JSON API")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve_api)

    p = sub.add_parser("telegram", help="run the Telegram gateway (loads repo .env)")
    p.set_defaults(func=cmd_telegram)

    p = sub.add_parser("scrape", help="browser-assisted scraping for X and similar feeds")
    p.add_argument("--url", required=True, help="page to open and collect from")
    p.add_argument("--platform", default="auto", choices=["auto", "x"])
    p.add_argument("--format", default="normalized", choices=["normalized", "4cat-x"])
    p.add_argument("--browser", default="firefox", choices=["firefox", "chromium", "webkit"])
    p.add_argument("--headless", action="store_true", help="run without a visible browser window")
    p.add_argument("--profile-dir", default=None, help="browser profile dir for logged-in sessions")
    p.add_argument("--out", default="", help="write NDJSON output here")
    p.add_argument("--raw-dir", default="", help="optional directory for raw captured JSON responses")
    p.add_argument("--scrolls", type=int, default=6, help="how many feed scrolls to perform")
    p.add_argument("--wait-ms", type=int, default=1500, help="wait between scrolls in milliseconds")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("layers", help="show the six layers of one or all nodes")
    p.add_argument("--as", dest="as_name", default="")
    p.set_defaults(func=cmd_layers)

    p = sub.add_parser("layer-set", help="record an observation of a node's layer")
    p.add_argument("--as", dest="as_name", required=True, help="node whose layer is recorded")
    p.add_argument(
        "--layer",
        choices=["physical", "biological", "social", "linguistic", "psychic", "cybernetic"],
        required=True,
    )
    p.add_argument("--set", action="append", required=True, help="key=value (repeatable)")
    p.add_argument("--reported-by", default=None, help="observer (default: the node itself)")
    p.add_argument("--private", action="store_true", help="store but hide from LLM context")
    p.set_defaults(func=cmd_layer_set)

    p = sub.add_parser("layer-history", help="show the event history of one layer")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument(
        "--layer",
        choices=["physical", "biological", "social", "linguistic", "psychic", "cybernetic"],
        required=True,
    )
    p.set_defaults(func=cmd_layer_history)

    # --------------------------------------------------- tribal goals
    p = sub.add_parser("goal-open", help="open a tribal goal (business/social/health)")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--category", choices=["business", "social", "health"], required=True)
    p.set_defaults(func=cmd_goal_open)

    p = sub.add_parser("goals", help="list goals (optionally by category)")
    p.add_argument("--category", choices=["business", "social", "health"], default=None)
    p.set_defaults(func=cmd_goals)

    p = sub.add_parser("goal-close", help="close a goal as achieved or dropped")
    p.add_argument("--by", required=True)
    p.add_argument("--goal", required=True)
    p.add_argument("--status", choices=["achieved", "dropped"], required=True)
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_goal_close)

    p = sub.add_parser("task-open", help="open a task, optionally linked to a goal")
    p.add_argument("--by", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--text", default="")
    p.add_argument("--goal", dest="goal_id", default=None)
    p.add_argument("--skills", default="", help="space-separated skill tags")
    p.set_defaults(func=cmd_task_open)

    p = sub.add_parser("tasks", help="list tasks (optionally by status)")
    p.add_argument("--status", choices=["open", "claimed", "done"], default=None)
    p.set_defaults(func=cmd_tasks)

    p = sub.add_parser("task-claim", help="claim an open task")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--task", required=True)
    p.set_defaults(func=cmd_task_claim)

    p = sub.add_parser("task-done", help="mark a task done")
    p.add_argument("--as", dest="as_name", required=True)
    p.add_argument("--task", required=True)
    p.set_defaults(func=cmd_task_done)

    p = sub.add_parser("task-assign", help="suggest members for a task by skills")
    p.add_argument("--task", required=True)
    p.set_defaults(func=cmd_task_assign)

    p = sub.add_parser("profit-record", help="record revenue into the treasury")
    p.add_argument("--by", required=True)
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--source", default="")
    p.set_defaults(func=cmd_profit_record)

    p = sub.add_parser(
        "profit-distribute",
        help="split an amount among voting members (equal, or --weight name=amount)",
    )
    p.add_argument("--by", required=True)
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--weight", action="append", default=[], help="name=weight (repeatable)")
    p.set_defaults(func=cmd_profit_distribute)

    p = sub.add_parser("ledger", help="show treasury and profit shares")
    p.set_defaults(func=cmd_ledger)

    p = sub.add_parser("wellbeing", help="record or show wellbeing (mental/physical/social/economic)")
    p.add_argument("--as", dest="as_name", default="")
    p.add_argument("--domain", choices=["physical", "mental", "social", "economic"], default=None)
    p.add_argument("--level", type=int, choices=range(1, 6), default=None)
    p.add_argument("--note", default="")
    p.add_argument("--reported-by", default=None)
    p.set_defaults(func=cmd_wellbeing)

    p = sub.add_parser("interests", help="declare interests (hobbies, humor) or show shared ones")
    p.add_argument("--as", dest="as_name", default="")
    p.add_argument("--add", default="", help="comma-separated interests to declare")
    p.set_defaults(func=cmd_interests)

    p = sub.add_parser("health", help="tribe health: wellbeing averages + shared interests")
    p.set_defaults(func=cmd_health)

    return parser


def main(argv: list[str] | None = None) -> int:
    from multitude.goals import GoalError
    from multitude.service import ServiceError

    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (TribeError, ServiceError, LayerError, GoalError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
