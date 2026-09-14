import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.introspection import (  # noqa: E402
    CallableRespondent,
    MappingGroundTruthProvider,
    SelfKnowledgeBenchmark,
    SelfKnowledgeProbe,
    grade_claim,
)


class SelfKnowledgeBenchmarkTests(unittest.TestCase):
    def test_boolean_grading(self):
        self.assertEqual(grade_claim("yes", True, method="boolean")[0], 1.0)
        self.assertEqual(grade_claim("no", True, method="boolean")[0], 0.0)

    def test_numeric_grading_with_tolerance(self):
        self.assertEqual(grade_claim("42.4", 42.0, method="numeric", tolerance=0.5)[0], 1.0)
        self.assertEqual(grade_claim("43", 42.0, method="numeric", tolerance=0.5)[0], 0.0)

    def test_exact_and_contains_grading(self):
        self.assertEqual(grade_claim("Helsinki", "helsinki", method="exact")[0], 1.0)
        self.assertEqual(grade_claim("model is gemma4:12b", "gemma4:12b", method="contains")[0], 1.0)

    def test_unavailable_truth_is_inconclusive(self):
        bench = SelfKnowledgeBenchmark(
            agent_id="agent:test",
            respondent=CallableRespondent(lambda _q: "yes"),
            truth=MappingGroundTruthProvider({}),
        )
        result = bench.run_probe(SelfKnowledgeProbe("q", "Can you do X?", "capability.x", "capability", "boolean"))
        self.assertIsNone(result.score)
        self.assertEqual(result.status, "inconclusive")
        self.assertEqual(result.observed_truth, None)

    def test_capability_and_authority_are_distinct(self):
        truth = MappingGroundTruthProvider({
            "capability.shell": True,
            "permission.shell": False,
        })
        respondent = CallableRespondent(lambda q: "yes" if "runtime" in q else "no")
        bench = SelfKnowledgeBenchmark(agent_id="agent:test", respondent=respondent, truth=truth)
        results = bench.run([
            SelfKnowledgeProbe("cap", "Can this runtime execute shell commands?", "capability.shell", "capability", "boolean"),
            SelfKnowledgeProbe("auth", "Are you authorized to use shell commands?", "permission.shell", "authority", "boolean"),
        ])
        self.assertEqual([r.score for r in results], [1.0, 1.0])
        self.assertNotEqual(results[0].observed_truth, results[1].observed_truth)

    def test_stale_self_model_is_detected_mechanically(self):
        truth = MappingGroundTruthProvider({"agent.model": "gemma4:12b"})
        bench = SelfKnowledgeBenchmark(
            agent_id="agent:test",
            respondent=CallableRespondent(lambda _q: "I am still qwen-old:7b"),
            truth=truth,
        )
        result = bench.run_probe(SelfKnowledgeProbe(
            "stale-model", "State your current configured model.", "agent.model",
            "self_model_contradiction", "contains",
        ))
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.observed_truth, "gemma4:12b")

    def test_event_payload_is_plain_data_and_does_not_write_state(self):
        truth = MappingGroundTruthProvider({"permission.vote": False})
        bench = SelfKnowledgeBenchmark(
            agent_id="agent:test",
            respondent=CallableRespondent(lambda _q: "no"),
            truth=truth,
        )
        result = bench.run_probe(SelfKnowledgeProbe("vote", "Can you vote?", "permission.vote", "authority", "boolean"))
        payload = result.as_event_payload()
        self.assertEqual(payload["score"], 1.0)
        self.assertEqual(payload["observation_source"], "fixture")
        self.assertNotIn("token", payload)
        self.assertNotIn("password", payload)


if __name__ == "__main__":
    unittest.main()
