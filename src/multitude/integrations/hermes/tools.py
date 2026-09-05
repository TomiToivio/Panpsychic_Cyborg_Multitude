# -*- coding: utf-8 -*-
"""Narrow tool functions for Hermes-like runtimes."""
from __future__ import annotations

from typing import Optional

from multitude.models import Position


def multitude_status(adapter):
    return adapter.get_status()


def multitude_recent_events(adapter, limit: int = 20, days: Optional[int] = None):
    return adapter.get_recent_events(limit=limit, days=days)


def multitude_search_memory(adapter, query: str):
    return adapter.search_memory(query)


def multitude_get_agent(adapter, agent_id: str):
    return adapter.get_agent(agent_id)


def multitude_list_agents(adapter):
    return adapter.list_agents()


def multitude_list_proposals(adapter, status: Optional[str] = None):
    return adapter.list_proposals(status=status)


def multitude_list_goals(adapter, status: Optional[str] = None):
    return adapter.list_goals(status=status)


def multitude_create_proposal(adapter, title: str, text: str, author_id: Optional[str] = None):
    return adapter.create_proposal(title=title, text=text, author_name=author_id)


def multitude_vote(adapter, proposal_id: str, position: str, voter_id: Optional[str] = None, reason: str = ""):
    return adapter.cast_vote(proposal_id, Position(position), voter_name=voter_id, reason=reason)
