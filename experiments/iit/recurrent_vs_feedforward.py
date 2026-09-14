"""Compare feed-forward and reciprocal two-node causal organizations.

Interpretation is deliberately narrow: the resulting values describe
irreducibility of these explicit toy models under the selected PyPhi/IIT
formalism. They are not consciousness measurements.
"""

from __future__ import annotations

from experiments.iit.toy_networks import feedforward, reciprocal, system_phi


def run() -> dict[str, float]:
    """Return full-boundary PyPhi system-irreducibility values."""

    return {
        "feedforward": system_phi(feedforward()),
        "reciprocal": system_phi(reciprocal()),
    }


if __name__ == "__main__":
    results = run()
    for name, value in results.items():
        print(f"{name}: phi={value}")
    print("Interpretation: compare causal irreducibility only; do not infer consciousness.")
