"""Toy comparison of passive prediction and epistemic action.

This is not a consciousness model. It demonstrates how selecting an observation
for expected information gain can reduce uncertainty about a hidden rule.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Belief:
    p_rule_zero: float

    @property
    def p_rule_one(self) -> float:
        return 1.0 - self.p_rule_zero

    def entropy_bits(self) -> float:
        values = (self.p_rule_zero, self.p_rule_one)
        return -sum(p * math.log2(p) for p in values if p > 0.0)


def likelihood(observation: int, query: int, rule: int) -> float:
    """Deterministic toy likelihood.

    Query 0 is uninformative: both rules emit 0.
    Query 1 distinguishes rules: rule 0 emits 0; rule 1 emits 1.
    """
    expected = 0 if query == 0 else rule
    return 1.0 if observation == expected else 0.0


def posterior(prior: Belief, query: int, observation: int) -> Belief:
    weights = [
        prior.p_rule_zero * likelihood(observation, query, 0),
        prior.p_rule_one * likelihood(observation, query, 1),
    ]
    total = sum(weights)
    if total == 0:
        raise ValueError("Observation impossible under the toy model")
    return Belief(weights[0] / total)


def expected_information_gain(prior: Belief, query: int) -> float:
    prior_h = prior.entropy_bits()
    expected_h = 0.0
    for observation in (0, 1):
        p_obs = sum(
            p_rule * likelihood(observation, query, rule)
            for rule, p_rule in enumerate((prior.p_rule_zero, prior.p_rule_one))
        )
        if p_obs > 0:
            expected_h += p_obs * posterior(prior, query, observation).entropy_bits()
    return prior_h - expected_h


def select_active_query(prior: Belief) -> int:
    return max((0, 1), key=lambda q: expected_information_gain(prior, q))


def run_demo(true_rule: int = 1) -> dict[str, float | int]:
    prior = Belief(0.5)
    passive_query = 0
    active_query = select_active_query(prior)

    passive_obs = 0 if passive_query == 0 else true_rule
    active_obs = 0 if active_query == 0 else true_rule

    passive_post = posterior(prior, passive_query, passive_obs)
    active_post = posterior(prior, active_query, active_obs)

    return {
        "passive_query": passive_query,
        "active_query": active_query,
        "passive_entropy_bits": passive_post.entropy_bits(),
        "active_entropy_bits": active_post.entropy_bits(),
        "active_expected_information_gain": expected_information_gain(prior, active_query),
    }


if __name__ == "__main__":
    print(run_demo())
