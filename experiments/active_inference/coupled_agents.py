"""Toy reciprocal-prediction experiment for PCM.

Two agents predict one another's binary state and update simple expectations.
The experiment measures coupling and adaptation, not consciousness.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Agent:
    expectation: float = 0.5
    learning_rate: float = 0.5

    def predict(self) -> int:
        return int(self.expectation >= 0.5)

    def update(self, observed_other: int) -> None:
        self.expectation += self.learning_rate * (observed_other - self.expectation)


def step(a: Agent, b: Agent, state_a: int, state_b: int, mode: str) -> tuple[float, float]:
    error_a = abs(a.expectation - state_b)
    error_b = abs(b.expectation - state_a)

    if mode == "one_way":
        a.update(state_b)
    elif mode == "reciprocal":
        a.update(state_b)
        b.update(state_a)
    elif mode != "uncoupled":
        raise ValueError(f"unknown mode: {mode}")

    return error_a, error_b


def run_demo(mode: str = "reciprocal") -> dict[str, float | str]:
    a = Agent(expectation=0.5)
    b = Agent(expectation=0.5)
    observations = [(0, 1), (0, 1), (1, 0), (1, 0)]

    total_error_a = 0.0
    total_error_b = 0.0
    for state_a, state_b in observations:
        err_a, err_b = step(a, b, state_a, state_b, mode)
        total_error_a += err_a
        total_error_b += err_b

    return {
        "mode": mode,
        "mean_error_a": total_error_a / len(observations),
        "mean_error_b": total_error_b / len(observations),
        "final_expectation_a": a.expectation,
        "final_expectation_b": b.expectation,
    }


if __name__ == "__main__":
    for coupling in ("uncoupled", "one_way", "reciprocal"):
        print(run_demo(coupling))
