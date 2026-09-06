# -*- coding: utf-8 -*-
"""Tribal goals: running a worker's co-operative and keeping it healthy.

GOALS.md defines three goal layers for the first prototype rhizome, a
worker's co-operative:

* **business**  - running the co-operative: customer work, marketing and
  sales, customer communications, information sharing for collaboration;
* **social**    - the wider Panpsychic Cyborg Multitude goals: the rhizome
  as one rhizomatic node among future nodes, philosophy, networking;
* **health**    - the rhizome and its agents kept well: entertainment,
  social interaction, shared hobbies, and per-agent wellbeing across
  four domains: physical, mental, social, economic.

All of it is event-sourced like everything in the kernel:

- goals are opened and closed as events, never overwritten;
- tasks carry skill tags and link to goals, so work distribution can
  follow each member's best talents;
- profit shares are recorded as events; the ledger is the
  co-operative's shared record of its agreement - actual money moves
  outside the kernel;
- wellbeing readings and declared interests are streams; the rhizome's
  health is derived (averages), never a stored verdict.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from multitude.models import ContributionRecord, ValueFlowRecord, new_id, now_iso


class GoalError(Exception):
    """Invalid goal/task/treasury operation."""


class GoalCategory(str, Enum):
    BUSINESS = "business"
    SOCIAL = "social"
    HEALTH = "health"
    CARE = "care"
    MAINTENANCE = "maintenance"


class GoalStatus(str, Enum):
    OPEN = "open"
    ACHIEVED = "achieved"
    DROPPED = "dropped"


class TaskStatus(str, Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    DONE = "done"


VALID_CATEGORIES = {c.value for c in GoalCategory}
VALID_DOMAINS = ("physical", "mental", "social", "economic")
VALID_COMMONS_TYPES = {"care", "maintenance", "labor", "value", "governance"}


class Goal:
    """A tribal goal (business, social, or health)."""

    def __init__(
        self,
        id: str,
        title: str,
        text: str,
        category: str,
        opened_by: str,
        opened_ts: str,
        status: str = GoalStatus.OPEN.value,
        closed_ts: str = "",
        closed_by: str = "",
        notes: str = "",
    ) -> None:
        self.id = id
        self.title = title
        self.text = text
        self.category = category
        self.opened_by = opened_by
        self.opened_ts = opened_ts
        self.status = status
        self.closed_ts = closed_ts
        self.closed_by = closed_by
        self.notes = notes

    def dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "category": self.category,
            "opened_by": self.opened_by,
            "opened_ts": self.opened_ts,
            "status": self.status,
            "closed_ts": self.closed_ts,
            "closed_by": self.closed_by,
            "notes": self.notes,
        }

    @classmethod
    def load(cls, data: dict[str, Any]) -> "Goal":
        return cls(**data)


class Task:
    """A unit of work, optionally linked to a goal, tagged with skills."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str = "",
        goal_id: Optional[str] = None,
        skills: Optional[list[str]] = None,
        opened_by: str = "",
        opened_ts: str = "",
        status: str = TaskStatus.OPEN.value,
        claimed_by: Optional[str] = None,
        claimed_ts: str = "",
        done_by: Optional[str] = None,
        done_ts: str = "",
    ) -> None:
        self.id = id
        self.title = title
        self.description = description
        self.goal_id = goal_id
        self.skills = list(skills or [])
        self.opened_by = opened_by
        self.opened_ts = opened_ts
        self.status = status
        self.claimed_by = claimed_by
        self.claimed_ts = claimed_ts
        self.done_by = done_by
        self.done_ts = done_ts

    def dump(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "goal_id": self.goal_id,
            "skills": self.skills,
            "opened_by": self.opened_by,
            "opened_ts": self.opened_ts,
            "status": self.status,
            "claimed_by": self.claimed_by,
            "claimed_ts": self.claimed_ts,
            "done_by": self.done_by,
            "done_ts": self.done_ts,
        }

    @classmethod
    def load(cls, data: dict[str, Any]) -> "Task":
        return cls(**data)


def require_amount(amount: Any) -> float:
    """Validate a positive money amount; rounds to 2 decimals."""
    try:
        val = float(amount)
    except (TypeError, ValueError):
        raise GoalError(f"amount must be a number, got: {amount!r}")
    if val <= 0:
        raise GoalError("amount must be positive")
    return round(val, 2)


def _require_task(rhizome, task_id: Optional[str]) -> Optional[str]:
    if not task_id:
        return None
    if task_id not in rhizome.tasks:
        raise GoalError(f"no task '{task_id}'")
    return task_id


def _require_resource(rhizome, resource_id: Optional[str]) -> Optional[str]:
    if not resource_id:
        return None
    if resource_id not in rhizome.resources:
        raise GoalError(f"no resource '{resource_id}'")
    return resource_id


def _require_device(rhizome, device_id: Optional[str]) -> Optional[str]:
    if not device_id:
        return None
    if device_id not in rhizome.devices:
        raise GoalError(f"no device '{device_id}'")
    return device_id


def _require_memory_entry(rhizome, memory_id: Optional[str]) -> Optional[str]:
    if not memory_id:
        return None
    if memory_id not in rhizome.memory:
        raise GoalError(f"no memory entry '{memory_id}'")
    return memory_id


def _normalize_id_list(items: Optional[list[str]]) -> list[str]:
    out: list[str] = []
    for item in items or []:
        value = str(item).strip()
        if value and value not in out:
            out.append(value)
    return out


def replay_goal_event(rhizome, type_: str, payload: dict[str, Any]) -> None:
    """Replay one tribal-goal event into rhizome state (called from Rhizome)."""
    if type_ == "goal_opened":
        g = Goal.load(payload["goal"])
        rhizome.goals[g.id] = g
    elif type_ == "goal_closed":
        g = rhizome.goals.get(payload["goal_id"])
        if g is not None:
            g.status = payload["status"]
            g.closed_ts = payload.get("closed_ts", "")
            g.closed_by = payload.get("closed_by", "")
            if payload.get("notes"):
                g.notes = payload["notes"]
    elif type_ == "task_opened":
        t = Task.load(payload["task"])
        rhizome.tasks[t.id] = t
    elif type_ == "task_claimed":
        t = rhizome.tasks.get(payload["task_id"])
        if t is not None:
            t.status = TaskStatus.CLAIMED.value
            t.claimed_by = payload["member"]
            t.claimed_ts = payload.get("ts", "")
    elif type_ == "task_released":
        t = rhizome.tasks.get(payload["task_id"])
        if t is not None:
            t.status = TaskStatus.OPEN.value
            t.claimed_by = None
            t.claimed_ts = ""
    elif type_ == "task_done":
        t = rhizome.tasks.get(payload["task_id"])
        if t is not None:
            t.status = TaskStatus.DONE.value
            t.done_by = payload["member"]
            t.done_ts = payload.get("ts", "")
    elif type_ == "profit_recorded":
        rhizome.treasury["total"] = round(
            rhizome.treasury.get("total", 0.0) + payload["amount"], 2
        )
        rhizome.treasury.setdefault("entries", []).append(payload)
    elif type_ == "profit_distributed":
        for member_id, amount in payload["distribution"].items():
            ledger = rhizome.profit_ledger
            ledger[member_id] = round(ledger.get(member_id, 0.0) + amount, 2)
        rhizome.treasury["total"] = round(
            rhizome.treasury.get("total", 0.0) - payload["amount"], 2
        )
    elif type_ == "contribution_recorded":
        contribution = ContributionRecord.model_validate(payload["contribution"])
        rhizome.contributions[contribution.id] = contribution
    elif type_ == "value_flow_recorded":
        flow = ValueFlowRecord.model_validate(payload["flow"])
        rhizome.value_flows[flow.id] = flow
    elif type_ == "wellbeing_recorded":
        rhizome.wellbeing_stream.append(payload)  # stream of readings
    elif type_ == "interests_declared":
        member_id = payload["member_id"]
        merged = list(rhizome.interests.get(member_id, []))
        for item in payload["interests"]:
            if item not in merged:
                merged.append(item)
        rhizome.interests[member_id] = merged


# ------------------------------------------------------------- operations


def open_goal(rhizome, title: str, text: str, category: str, opened_by: str) -> Goal:
    if category not in VALID_CATEGORIES:
        raise GoalError(
            f"unknown category '{category}' - valid: {sorted(VALID_CATEGORIES)}"
        )
    member = rhizome._require_member(opened_by)
    g = Goal(
        id=new_id("goal"),
        title=title.strip(),
        text=text.strip(),
        category=category,
        opened_by=member.name,
        opened_ts=now_iso(),
    )
    rhizome._emit("goal_opened", member.name, {"goal": g.dump()})
    rhizome.remember(
        title=f"Goal: {g.title}",
        text=f"[{g.category}] {g.text}",
        author=member.name,
        kind="note",
        tags=["goal", g.category],
    )
    return g


def close_goal(
    rhizome, goal_id: str, closed_by: str, status: str, notes: str = ""
) -> Goal:
    if status not in (GoalStatus.ACHIEVED.value, GoalStatus.DROPPED.value):
        raise GoalError("status must be 'achieved' or 'dropped'")
    g = rhizome.goals.get(goal_id)
    if g is None:
        raise GoalError(f"no goal '{goal_id}'")
    if g.status != GoalStatus.OPEN.value:
        raise GoalError(f"goal '{goal_id}' is already {g.status}")
    member = rhizome._require_member(closed_by)
    rhizome._emit(
        "goal_closed",
        member.name,
        {
            "goal_id": goal_id,
            "status": status,
            "closed_ts": now_iso(),
            "closed_by": member.name,
            "notes": notes.strip(),
        },
    )
    return g


def open_task(
    rhizome,
    title: str,
    opened_by: str,
    description: str = "",
    goal_id: Optional[str] = None,
    skills: Optional[list[str]] = None,
) -> Task:
    if goal_id and goal_id not in rhizome.goals:
        raise GoalError(f"no goal '{goal_id}'")
    if isinstance(skills, str):
        skills = [skills]
    skills_clean: list[str] = []
    for s in skills or []:
        s = str(s).strip()
        if s and s.lower() not in [x.lower() for x in skills_clean]:
            skills_clean.append(s)
    member = rhizome._require_member(opened_by)
    t = Task(
        id=new_id("task"),
        title=title.strip(),
        description=(description or "").strip(),
        goal_id=goal_id,
        skills=skills_clean,
        opened_by=member.name,
        opened_ts=now_iso(),
    )
    rhizome._emit("task_opened", member.name, {"task": t.dump()})
    return t


def claim_task(rhizome, task_id: str, member: str) -> Task:
    t = rhizome.tasks.get(task_id)
    if t is None:
        raise GoalError(f"no task '{task_id}'")
    if t.status == TaskStatus.DONE.value:
        raise GoalError(f"task '{task_id}' is already done")
    if t.status == TaskStatus.CLAIMED.value and t.claimed_by:
        holder = rhizome.members.get(t.claimed_by)
        who = holder.name if holder else t.claimed_by
        if who != member:
            raise GoalError(f"task '{task_id}' is already claimed by {who}")
    member_m = rhizome._require_member(member)
    rhizome._emit(
        "task_claimed",
        member_m.name,
        {"task_id": task_id, "member": member_m.name, "ts": now_iso()},
    )
    return t


def release_task(rhizome, task_id: str, member: str) -> Task:
    t = rhizome.tasks.get(task_id)
    if t is None:
        raise GoalError(f"no task '{task_id}'")
    m = rhizome._require_member(member)
    if t.status != TaskStatus.CLAIMED.value:
        raise GoalError(f"task '{task_id}' is not claimed")
    if t.claimed_by and t.claimed_by != m.name:
        holder = rhizome.member_by_name(t.claimed_by)
        who = holder.name if holder else t.claimed_by
        raise GoalError(f"task '{task_id}' is claimed by {who}")
    rhizome._emit("task_released", m.name, {"task_id": t.id, "member": m.name})
    return t


def done_task(rhizome, task_id: str, member: str) -> Task:
    t = rhizome.tasks.get(task_id)
    if t is None:
        raise GoalError(f"no task '{task_id}'")
    if t.status == TaskStatus.DONE.value:
        raise GoalError(f"task '{task_id}' is already done")
    member_m = rhizome._require_member(member)
    rhizome._emit(
        "task_done",
        member_m.name,
        {"task_id": task_id, "member": member_m.name, "ts": now_iso()},
    )
    return t


def suggest_task_assignment(rhizome, task: Task) -> list[str]:
    """Rank members by skill overlap with the task's skill tags (best first)."""
    wanted = {s.lower() for s in (task.skills or [])}
    scored: list[tuple[int, str]] = []
    for m in rhizome.members.values():
        skills = {s.lower() for s in m.meta.get("skills", [])}
        score = len(wanted & skills)
        scored.append((-score, m.name))
    scored.sort()
    return [name for _, name in scored]


def record_profit(
    rhizome, amount: float, source: str, recorded_by: str
) -> dict[str, Any]:
    """Record revenue into the co-operative's shared treasury."""
    val = require_amount(amount)
    member_m = rhizome._require_member(recorded_by)
    payload = {
        "amount": val,
        "source": (source or "").strip(),
        "ts": now_iso(),
        "recorded_by": member_m.name,
    }
    rhizome._emit("profit_recorded", member_m.name, payload)
    return payload


def distribute_profit(
    rhizome,
    amount: float,
    recorded_by: str,
    weights: Optional[dict[str, float]] = None,
    contribution_ids: Optional[list[str]] = None,
    resource_ids: Optional[list[str]] = None,
    task_ids: Optional[list[str]] = None,
    notes: str = "",
) -> dict[str, Any]:
    """Split an amount among voting members (equal by default).

    Weights (by member name) split proportionally. Shares land in the
    rhizome's profit ledger - the co-operative's shared record of its
    agreement. Actual money moves outside the kernel.
    """
    val = require_amount(amount)
    member_m = rhizome._require_member(recorded_by)
    distribution_id = new_id("dist")
    cited_contributions = _normalize_id_list(contribution_ids)
    cited_resources = _normalize_id_list(resource_ids)
    cited_tasks = _normalize_id_list(task_ids)
    for contribution_id in cited_contributions:
        if contribution_id not in rhizome.contributions:
            raise GoalError(f"no contribution '{contribution_id}'")
    for resource_id in cited_resources:
        _require_resource(rhizome, resource_id)
    for task_id in cited_tasks:
        _require_task(rhizome, task_id)
    payees = rhizome.voting_members()
    if not payees:
        raise GoalError("no voting members to distribute to")
    distribution: dict[str, float] = {}
    if weights:
        clean: dict[str, float] = {}
        for name, w in weights.items():
            m = rhizome.member_by_name(name)
            if m is None or not m.voting:
                raise GoalError(f"'{name}' is not a voting member")
            clean[m.id] = require_amount(w)
        total_w = sum(clean.values())
        if total_w <= 0:
            raise GoalError("total weight must be positive")
        for mid, w in clean.items():
            distribution[mid] = round(val * w / total_w, 2)
    else:
        even = round(val / len(payees), 2)
        distribution = {m.id: even for m in payees}
    # fix rounding drift on the first payee (deterministic)
    diff = round(val - sum(distribution.values()), 2)
    if diff and distribution:
        first_key = next(iter(distribution))
        distribution[first_key] = round(distribution[first_key] + diff, 2)
    total = round(sum(distribution.values()), 2)
    if total != val:
        raise GoalError("distribution does not sum to the amount")
    payload = {
        "distribution_id": distribution_id,
        "amount": val,
        "distribution": distribution,
        "ts": now_iso(),
        "recorded_by": member_m.name,
    }
    rhizome._emit("profit_distributed", member_m.name, payload)
    flow = ValueFlowRecord(
        id=new_id("flow"),
        ts=payload["ts"],
        distribution_id=distribution_id,
        amount=val,
        recorded_by=member_m.name,
        source="weighted" if weights else "equal",
        distribution=dict(distribution),
        contribution_ids=cited_contributions,
        resource_ids=cited_resources,
        task_ids=cited_tasks,
        notes=(notes or "").strip(),
    )
    rhizome._emit("value_flow_recorded", member_m.name, {"flow": flow.model_dump()})
    payload["ledger_flow_id"] = flow.id
    return payload


def record_contribution(
    rhizome,
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
) -> ContributionRecord:
    contributor = rhizome._require_member(contributed_by)
    title_clean = (title or "").strip()
    if not title_clean:
        raise GoalError("contribution title cannot be empty")
    try:
        quantity_value = float(quantity)
    except (TypeError, ValueError):
        raise GoalError("quantity must be a number")
    if quantity_value <= 0:
        raise GoalError("quantity must be positive")
    if cost_amount is not None:
        cost_value = require_amount(cost_amount)
    else:
        cost_value = None
    contribution = ContributionRecord(
        id=new_id("contrib"),
        ts=now_iso(),
        contributor_id=contributor.id,
        contributor_name=contributor.name,
        kind=(kind or "labor").strip() or "labor",
        title=title_clean,
        task_id=_require_task(rhizome, task_id),
        resource_id=_require_resource(rhizome, resource_id),
        device_id=_require_device(rhizome, device_id),
        output_memory_id=_require_memory_entry(rhizome, output_memory_id),
        quantity=round(quantity_value, 2),
        unit=(unit or "unit").strip() or "unit",
        cost_amount=cost_value,
        notes=(notes or "").strip(),
        meta=dict(meta or {}),
    )
    rhizome._emit(
        "contribution_recorded",
        contributor.name,
        {"contribution": contribution.model_dump()},
    )
    return contribution


def explain_distribution(rhizome, distribution_id: str) -> dict[str, Any]:
    distribution_id = (distribution_id or "").strip()
    if not distribution_id:
        raise GoalError("distribution id cannot be empty")
    flow = None
    for item in rhizome.value_flows.values():
        if item.distribution_id == distribution_id:
            flow = item
            break
    if flow is None:
        raise GoalError(f"no distribution '{distribution_id}'")
    members = {}
    for member_id, amount in flow.distribution.items():
        member = rhizome.members.get(member_id) or rhizome.former_members.get(member_id)
        members[member.name if member else member_id] = amount
    cited_contributions = []
    for contribution_id in flow.contribution_ids:
        contribution = rhizome.contributions.get(contribution_id)
        if contribution is not None:
            cited_contributions.append(contribution.model_dump())
    cited_resources = []
    for resource_id in flow.resource_ids:
        resource = rhizome.resources.get(resource_id)
        if resource is not None:
            cited_resources.append(resource.model_dump())
    cited_tasks = []
    for task_id in flow.task_ids:
        task = rhizome.tasks.get(task_id)
        if task is not None:
            cited_tasks.append(task.dump())
    return {
        "distribution_id": flow.distribution_id,
        "flow_id": flow.id,
        "amount": flow.amount,
        "recorded_by": flow.recorded_by,
        "method": flow.source,
        "distribution": members,
        "contribution_ids": list(flow.contribution_ids),
        "resource_ids": list(flow.resource_ids),
        "task_ids": list(flow.task_ids),
        "contributions": cited_contributions,
        "resources": cited_resources,
        "tasks": cited_tasks,
        "notes": flow.notes,
        "meta": dict(flow.meta),
    }


def record_wellbeing(
    rhizome,
    member: str,
    domain: str,
    level: int,
    note: str = "",
    reported_by: Optional[str] = None,
) -> dict[str, Any]:
    """Record a wellbeing reading (1..5) in one of the four domains.

    Domains per GOALS.md: physical, mental, social, economic. Self-report
    by default; another member may record with their name attached.
    """
    if domain not in VALID_DOMAINS:
        raise GoalError(f"unknown domain '{domain}' - valid: {list(VALID_DOMAINS)}")
    try:
        level = int(level)
    except (TypeError, ValueError):
        raise GoalError("level must be an integer")
    if not 1 <= level <= 5:
        raise GoalError("level must be between 1 and 5")
    m = rhizome._require_member(member)
    reporter = rhizome._require_member(reported_by) if reported_by else m
    payload = {
        "member_id": m.id,
        "member": m.name,
        "domain": domain,
        "level": int(level),
        "note": (note or "").strip(),
        "ts": now_iso(),
        "recorded_by": reporter.name,
    }
    rhizome._emit("wellbeing_recorded", m.name, payload)
    return payload


def latest_wellbeing(rhizome, member: str = "") -> dict[str, Any]:
    """Newest reading per (member, domain); rhizome averages derived."""
    target = rhizome._require_member(member) if member else None
    newest: dict[tuple[str, str], dict[str, Any]] = {}
    for rec in rhizome.wellbeing_stream:
        rec_member = rec["member_id"]
        if target is not None and rec_member != target.id:
            continue
        key = (rec_member, rec["domain"])
        prev = newest.get(key)
        if prev is None or rec["ts"] >= prev["ts"]:
            newest[key] = rec
    by_member: dict[str, dict[str, int]] = {}
    for (mid, dom), rec in sorted(newest.items()):
        m = rhizome.members.get(mid)
        name = m.name if m else rec.get("member", mid)
        by_member.setdefault(name, {})[dom] = rec["level"]
    if target is not None:
        by_member = {
            name: doms
            for name, doms in by_member.items()
            if name == target.name
        }
    avgs: dict[str, float] = {}
    for dom in VALID_DOMAINS:
        vals = [r["level"] for (mid, dm), r in newest.items() if dm == dom]
        if vals:
            avgs[dom] = round(sum(vals) / len(vals), 2)
    return {"by_member": by_member, "averages": avgs}


def declare_interests(rhizome, member: str, interests: list[str]) -> dict[str, Any]:
    """Declare a member's interests (hobbies, loves, humor) to the rhizome."""
    if isinstance(interests, str):
        interests = [interests]
    items: list[str] = []
    for item in interests:
        s = str(item).strip()
        if s and s.lower() not in [x.lower() for x in items]:
            items.append(s)
    if not items:
        raise GoalError("no interests given")
    m = rhizome._require_member(member)
    payload = {
        "member_id": m.id,
        "member": m.name,
        "interests": items,
        "ts": now_iso(),
        "declared_by": m.name,
    }
    rhizome._emit("interests_declared", m.name, payload)
    return payload


def shared_interests(rhizome) -> dict[str, list[str]]:
    """Interests shared by 2+ members -> {interest: [names]}."""
    tally: dict[str, list[str]] = {}
    for member_id, items in rhizome.interests.items():
        m = rhizome.members.get(member_id)
        name = m.name if m else member_id
        for item in items:
            tally.setdefault(item.lower(), []).append(name)
    return {k: v for k, v in sorted(tally.items()) if len(set(v)) >= 2}


def rhizome_health(rhizome) -> dict[str, Any]:
    """Derived rhizome health: wellbeing averages + shared interests."""
    wb = latest_wellbeing(rhizome)
    return {
        "wellbeing": wb,
        "shared_interests": shared_interests(rhizome),
    }
