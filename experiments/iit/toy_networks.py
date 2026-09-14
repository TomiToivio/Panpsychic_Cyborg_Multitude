"""Deterministic two-node causal models for IIT experiments.

The transition probability matrices (TPMs) are represented state-by-node in
little-endian state order: (0,0), (1,0), (0,1), (1,1).

No PyPhi import is required to construct or test these models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

State = tuple[int, int]


@dataclass(frozen=True)
class ToyNetwork:
    """Explicit deterministic two-node causal model."""

    name: str
    tpm: tuple[tuple[int, int], ...]
    cm: tuple[tuple[int, int], tuple[int, int]]
    state: State = (1, 0)
    description: str = ""


_STATES: tuple[State, ...] = ((0, 0), (1, 0), (0, 1), (1, 1))


def _tpm(update: Callable[[int, int], State]) -> tuple[tuple[int, int], ...]:
    return tuple(update(a, b) for a, b in _STATES)


def independent() -> ToyNetwork:
    """Each unit persists independently: A'=A, B'=B."""

    return ToyNetwork(
        name="independent",
        tpm=_tpm(lambda a, b: (a, b)),
        cm=((1, 0), (0, 1)),
        description="Two self-persistent units with no cross-coupling.",
    )


def feedforward() -> ToyNetwork:
    """One-way causal influence: A'=A, B'=A."""

    return ToyNetwork(
        name="feedforward",
        tpm=_tpm(lambda a, b: (a, a)),
        cm=((1, 1), (0, 0)),
        description="A drives itself and B; B does not influence A.",
    )


def reciprocal() -> ToyNetwork:
    """Bidirectional coupling: A'=B, B'=A."""

    return ToyNetwork(
        name="reciprocal",
        tpm=_tpm(lambda a, b: (b, a)),
        cm=((0, 1), (1, 0)),
        description="Each unit's next state depends on the other unit.",
    )


def recurrent_or() -> ToyNetwork:
    """Strong recurrent coupling: A'=A OR B, B'=A OR B."""

    return ToyNetwork(
        name="recurrent_or",
        tpm=_tpm(lambda a, b: (int(bool(a or b)), int(bool(a or b)))),
        cm=((1, 1), (1, 1)),
        description="Both units jointly determine both next states.",
    )


def as_pyphi(model: ToyNetwork):
    """Build a PyPhi Network for a toy model.

    PyPhi is optional and intentionally imported lazily. Current IIT 4.0
    experiments target the PyPhi 2.0 development line on Python 3.13+.
    """

    try:
        import pyphi
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise RuntimeError(
            "PyPhi is optional. On Python 3.13+, install PCM with the 'iit' extra."
        ) from exc

    return pyphi.Network(model.tpm, cm=model.cm)


def system_phi(model: ToyNetwork) -> float:
    """Compute system irreducibility for the model's full two-node boundary."""

    try:
        import pyphi
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "PyPhi is optional. On Python 3.13+, install PCM with the 'iit' extra."
        ) from exc

    network = as_pyphi(model)
    subsystem = pyphi.Subsystem(network, model.state, range(2))
    return float(pyphi.compute.sia(subsystem).phi)
