"""Toy interoceptive-control experiment.

The agent regulates a scalar internal state toward a preferred range while an
external cue may encourage the opposite action. This studies adaptive control,
not phenomenal experience.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InteroceptiveAgent:
    preferred_internal: float = 0.5
    internal_weight: float = 1.0
    external_weight: float = 0.5

    def choose_action(self, internal_state: float, external_cue: int) -> int:
        """Return -1 or +1.

        Internal prediction error pulls toward the preferred state; the
        external cue contributes a competing contextual preference.
        """
        internal_drive = self.internal_weight * (self.preferred_internal - internal_state)
        external_drive = self.external_weight * (1 if external_cue else -1)
        return 1 if internal_drive + external_drive >= 0 else -1


def transition(internal_state: float, action: int, step_size: float = 0.1) -> float:
    return min(1.0, max(0.0, internal_state + step_size * action))


def run_episode(agent: InteroceptiveAgent, start: float, external_cue: int, steps: int = 5) -> list[float]:
    state = start
    trajectory = [state]
    for _ in range(steps):
        state = transition(state, agent.choose_action(state, external_cue))
        trajectory.append(state)
    return trajectory


def deviation_from_preference(agent: InteroceptiveAgent, state: float) -> float:
    return abs(state - agent.preferred_internal)


if __name__ == "__main__":
    with_interoception = InteroceptiveAgent(internal_weight=1.0, external_weight=0.2)
    without_interoception = InteroceptiveAgent(internal_weight=0.0, external_weight=0.2)
    print("with:", run_episode(with_interoception, start=0.1, external_cue=0))
    print("without:", run_episode(without_interoception, start=0.1, external_cue=0))
