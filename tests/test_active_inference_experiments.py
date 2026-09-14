from experiments.active_inference.coupled_agents import Agent, run_demo as run_coupled
from experiments.active_inference.interoceptive_agent import (
    InteroceptiveAgent,
    deviation_from_preference,
    run_episode,
)
from experiments.active_inference.passive_vs_active import (
    Belief,
    expected_information_gain,
    run_demo as run_active,
    select_active_query,
)


def test_epistemic_query_reduces_uncertainty() -> None:
    prior = Belief(0.5)
    assert select_active_query(prior) == 1
    assert expected_information_gain(prior, 1) > expected_information_gain(prior, 0)

    result = run_active(true_rule=1)
    assert result["active_entropy_bits"] < result["passive_entropy_bits"]


def test_reciprocal_mode_updates_both_agents() -> None:
    uncoupled = run_coupled("uncoupled")
    reciprocal = run_coupled("reciprocal")

    assert uncoupled["final_expectation_a"] == 0.5
    assert uncoupled["final_expectation_b"] == 0.5
    assert reciprocal["final_expectation_a"] != 0.5
    assert reciprocal["final_expectation_b"] != 0.5


def test_interoceptive_term_supports_return_toward_preference() -> None:
    with_interoception = InteroceptiveAgent(internal_weight=1.0, external_weight=0.2)
    without_interoception = InteroceptiveAgent(internal_weight=0.0, external_weight=0.2)

    with_path = run_episode(with_interoception, start=0.1, external_cue=0)
    without_path = run_episode(without_interoception, start=0.1, external_cue=0)

    assert deviation_from_preference(with_interoception, with_path[-1]) < deviation_from_preference(
        without_interoception, without_path[-1]
    )


def test_agent_prediction_is_deterministic() -> None:
    assert Agent(expectation=0.49).predict() == 0
    assert Agent(expectation=0.5).predict() == 1
