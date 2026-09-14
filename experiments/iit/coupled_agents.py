"""Compare independent, one-way, and reciprocal toy-agent coupling.

Each 'agent' is intentionally only one binary causal unit. This isolates the
question of cross-boundary causal coupling; it is not a phenomenological or
behavioral model of a human or LLM.
"""

from __future__ import annotations

from experiments.iit.toy_networks import independent, feedforward, reciprocal, system_phi


def run() -> dict[str, float]:
    """Compute full two-unit system irreducibility for three coupling regimes."""

    return {
        "independent": system_phi(independent()),
        "one_way": system_phi(feedforward()),
        "reciprocal": system_phi(reciprocal()),
    }


if __name__ == "__main__":
    results = run()
    for name, value in results.items():
        print(f"{name}: phi={value}")
    print(
        "Interpretation: changes concern the modeled causal boundary and coupling, "
        "not evidence of relational consciousness."
    )
