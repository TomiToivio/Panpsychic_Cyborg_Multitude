"""Compare uncoupled and strongly recurrent two-node causal systems."""

from __future__ import annotations

from experiments.iit.toy_networks import independent, recurrent_or, system_phi


def run() -> dict[str, float]:
    """Return system irreducibility for modular and integrated toy models."""

    return {
        "modular": system_phi(independent()),
        "integrated": system_phi(recurrent_or()),
    }


if __name__ == "__main__":
    results = run()
    for name, value in results.items():
        print(f"{name}: phi={value}")
    print("Interpretation: toy causal integration only; no phenomenology is inferred.")
