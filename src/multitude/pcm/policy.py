# -*- coding: utf-8 -*-
"""PCM policy layer — authorization and physical-device safety (§21, §22).

Network reachability is not authorization. This module separates:

    reachable  — a node can be addressed on the fabric (Zenoh's concern)
    authenticated — the sender's signature verifies (envelope.verify)
    authorized  local policy allows the action             (pcm.policy)
    trusted     long-term relationships (VCs, allowlists)  (pcm.capability)

Design (KISS, local-first): each PCM node owns a local Policy object.
Rules are explicit, greppable, and fail-closed: anything not explicitly
allowed is denied. High-risk device actions additionally require a
SafetyConstraint check (rate limits, allowed ranges, forbidden targets)
so that prompt compliance is NEVER the safety mechanism.

Rule shape::

    PolicyRule(action="light.set", target="device:lamp01",
               allowed_authors=("agent:hermes",), max_per_minute=10)

    Policy(rules=[...], default=Decision.DENY)
"""
from __future__ import annotations

import fnmatch
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


# High-risk action prefixes that ALWAYS require explicit safety validation.
HIGH_RISK_ACTIONS = (
    "drone.",       # anything commanding a drone
    "lock.",        # physical locks
    "power.",       # mains power
    "robot.move",   # robot locomotion
)


@dataclass
class PolicyRule:
    """One authorization rule. Wildcards allowed in action/target patterns."""

    action: str                    # fnmatch pattern, e.g. "light.*"
    target: str = "*"              # fnmatch pattern over pcm id, e.g. "device:*"
    allowed_authors: tuple[str, ...] = ()   # exact pcm ids or fnmatch patterns
    max_per_minute: int | None = None       # rate limit (safety)
    parameter_limits: dict[str, tuple[float, float]] = field(default_factory=dict)
    note: str = ""


class PolicyDenied(PermissionError):
    """Action not authorized by local policy."""


@dataclass
class Policy:
    """Local authorization policy. Fail-closed: default is DENY."""

    rules: list[PolicyRule] = field(default_factory=list)
    default: Decision = Decision.DENY
    _counters: dict[tuple[str, str, int], list[float]] = field(
        default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def allow(self, action: str, target: str = "*", authors: tuple[str, ...] = (),
              **kwargs: Any) -> Policy:
        """Append an ALLOW rule (convenience builder)."""
        self.rules.append(PolicyRule(action=action, target=target,
                                     allowed_authors=authors, **kwargs))
        return self

    def decide(self, author: str, action: str, target: str,
               parameters: dict[str, Any] | None = None) -> Decision:
        """Return the decision for one action WITHOUT side effects."""
        parameters = parameters or {}
        for rule in self.rules:
            if not fnmatch.fnmatchcase(action, rule.action):
                continue
            if not fnmatch.fnmatchcase(target, rule.target):
                continue
            if rule.allowed_authors and not any(
                    fnmatch.fnmatchcase(author, a) for a in rule.allowed_authors):
                continue
            # parameter range checks: a limit constrains values WHEN
            # provided; absence of the parameter is not a violation
            ok = True
            for pname, (lo, hi) in rule.parameter_limits.items():
                val = parameters.get(pname)
                if val is None:
                    continue
                if not isinstance(val, (int, float)) or not (lo <= val <= hi):
                    ok = False
                    break
            if ok:
                return Decision.ALLOW
        return self.default

    def authorize(self, author: str, action: str, target: str,
                  parameters: dict[str, Any] | None = None) -> None:
        """Authorize one action; raises PolicyDenied when not allowed.

        Applies rate limiting for rules that declare max_per_minute and
        enforces the high-risk gate: a high-risk action must be matched
        by an explicit rule (default ALLOW never covers it).
        """
        parameters = parameters or {}
        decision = self.decide(author, action, target, parameters)
        if decision is not Decision.ALLOW:
            raise PolicyDenied(
                f"policy denies {author!r} -> {action!r} on {target!r}")
        if self._is_high_risk(action) and not self._explicitly_matched(action, target):
            raise PolicyDenied(
                f"high-risk action {action!r} requires an explicit rule")
        self._apply_rate_limits(author, action, target)

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _is_high_risk(action: str) -> bool:
        return any(action.startswith(p) for p in HIGH_RISK_ACTIONS)

    def _explicitly_matched(self, action: str, target: str) -> bool:
        """True when a rule matches action+target with a non-trivial pattern.

        A rule whose note marks it as a verified capability grant
        ("vc:…") counts as explicit on the action axis even when its
        target is the default "*": the grant was deliberately issued,
        signed, and admitted by the operator — it is not a sloppy
        default. Wildcard-everything rules ("*"/"*" with no note) are
        still trivial and never satisfy the gate.
        """
        for rule in self.rules:
            if fnmatch.fnmatchcase(action, rule.action) and \
                    fnmatch.fnmatchcase(target, rule.target):
                if rule.action != "*" and rule.target != "*":
                    return True
                if rule.note.startswith("vc:") and rule.action != "*":
                    return True
        return False

    def _apply_rate_limits(self, author: str, action: str, target: str) -> None:
        now = time.time()
        with self._lock:
            for rule in self.rules:
                if rule.max_per_minute is None:
                    continue
                if not (fnmatch.fnmatchcase(action, rule.action)
                        and fnmatch.fnmatchcase(target, rule.target)):
                    continue
                bucket = (author, rule.action, rule.max_per_minute)
                window = [t for t in self._counters.get(bucket, []) if now - t < 60.0]
                if len(window) >= rule.max_per_minute:
                    raise PolicyDenied(
                        f"rate limit exceeded for {action!r} "
                        f"({rule.max_per_minute}/min)")
                window.append(now)
                self._counters[bucket] = window


__all__ = [
    "Decision",
    "PolicyRule",
    "Policy",
    "PolicyDenied",
    "HIGH_RISK_ACTIONS",
]