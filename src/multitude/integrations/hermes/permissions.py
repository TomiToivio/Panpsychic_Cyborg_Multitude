# -*- coding: utf-8 -*-
"""Permission model: capability is separate from authority.

A technological agent - Hermes included - gets capabilities through
rhizome policy, never by accident of its technical powers. The default
below grants knowledge-steward capabilities (read, search, draft,
counsel, propose) and withholds all political authority (vote, block,
membership changes, governance changes, money).

A rhizome may change these permissions through its own decision process;
the code here does not hard-code political authority for any agent
runtime. Permissions are a small plain dict so that any other integration
(Claude, Codex, Ollama, BCI) can reuse exactly the same shape.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class PermissionDenied(PermissionError):
    """A technological agent lacks authority for a mutating action."""


# The knowledge-steward default for a technological node.
DEFAULT_PERMISSIONS: dict[str, bool] = {
    "read_memory": True,
    "search": True,
    "summarize": True,
    "counsel": True,
    "propose": True,
    # political authority: withheld by default, granted only by policy
    "vote": False,
    "block": False,
    "add_member": False,
    "remove_member": False,
    "modify_governance": False,
    "change_permissions": False,
    "delete_history": False,
    "spend_money": False,
    "transfer_assets": False,
}

# actions that only make sense for a member with a vote
VOTING_ACTIONS = ("vote", "block")

KINDS = ("read", "propose", "membership", "treasury", "governance", "history")


@dataclass
class Permissions:
    """Resolved permission set for one technological node."""

    node_name: str
    grants: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_PERMISSIONS))

    def allow(self, action: str) -> None:
        self.grants[action] = True

    def deny(self, action: str) -> None:
        self.grants[action] = False

    def require(self, action: str) -> None:
        if not self.grants.get(action, False):
            raise PermissionDenied(
                f"'{self.node_name}' lacks '{action}' authority - "
                "grant it through rhizome policy, not by accident"
            )