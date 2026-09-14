from __future__ import annotations

import importlib.util

import pytest

from experiments.iit.toy_networks import feedforward, independent, reciprocal, recurrent_or


def test_toy_networks_are_deterministic_and_two_node() -> None:
    models = [independent(), feedforward(), reciprocal(), recurrent_or()]

    for model in models:
        assert len(model.tpm) == 4
        assert all(len(row) == 2 for row in model.tpm)
        assert all(bit in (0, 1) for row in model.tpm for bit in row)
        assert len(model.cm) == 2
        assert all(len(row) == 2 for row in model.cm)
        assert model.state == (1, 0)


def test_feedforward_and_reciprocal_have_distinct_causal_models() -> None:
    ff = feedforward()
    recurrent = reciprocal()

    assert ff.tpm != recurrent.tpm
    assert ff.cm != recurrent.cm
    assert ff.cm == ((1, 1), (0, 0))
    assert recurrent.cm == ((0, 1), (1, 0))


def test_independent_and_integrated_models_have_expected_connectivity() -> None:
    modular = independent()
    integrated = recurrent_or()

    assert modular.cm == ((1, 0), (0, 1))
    assert integrated.cm == ((1, 1), (1, 1))


@pytest.mark.iit
def test_pyphi_small_computation_when_optional_dependency_is_present() -> None:
    if importlib.util.find_spec("pyphi") is None:
        pytest.skip("optional PyPhi IIT dependency is not installed")

    from experiments.iit.toy_networks import system_phi

    value = system_phi(reciprocal())
    assert isinstance(value, float)
    assert value >= 0.0
