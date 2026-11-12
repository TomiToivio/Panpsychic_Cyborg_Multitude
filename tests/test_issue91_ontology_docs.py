"""#91: the ontology and the cyborg model must stay falsifiable, not just present.

The failure this guards against is a document that reads well and claims everything. #89's guards
check that the megatheory exists; these check that #91's two documents keep the properties that make
it a research programme rather than a creed: a stated preference that can change, a bridge that is
named as a bridge, and hypotheses with results that would count against them.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "docs" / "ONTOLOGY.md"
CYBORG = ROOT / "docs" / "CYBORG_ASSEMBLAGE.md"
SOURCES = ROOT / "docs" / "research" / "SOURCES.md"


def flat(text: str) -> str:
    """Collapse markdown line-wrapping so a phrase can be asserted across a line break."""
    return " ".join(text.split())


class DocumentPresenceTests(unittest.TestCase):
    def test_both_documents_exist_and_are_not_stubs(self):
        for path in (ONTOLOGY, CYBORG):
            self.assertTrue(path.exists(), f"{path.name} is missing")
            self.assertGreater(len(path.read_text(encoding="utf-8").splitlines()), 80,
                               f"{path.name} looks like a stub")


class OntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = flat(ONTOLOGY.read_text(encoding="utf-8"))

    def test_the_working_proposition_is_stated(self):
        for phrase in ("pluralist", "Spinoza-inspired", "cybersemiotic", "cyborg hypothesis"):
            self.assertIn(phrase, self.text)

    def test_exploratory_pluralism_keeps_three_positions_live(self):
        for position in ("Panpsychism", "Idealism", "Physicalism"):
            self.assertIn(position, self.text)
        self.assertIn("does **not** claim", self.text)

    def test_panpsychism_is_a_preference_that_can_change(self):
        self.assertIn("favoured hypothesis, not the rule", self.text)
        self.assertIn("what would change my mind", self.text)

    def test_spinoza_is_an_analogy_not_a_reconciliation(self):
        self.assertIn("working analogy, not solution", self.text)
        self.assertIn("Spinoza resolves the contemporary debate", self.text)

    def test_the_bridge_names_all_three_thinkers(self):
        for name in ("Peirce", "Luhmann", "Brier"):
            self.assertIn(name, self.text)
        self.assertIn("tensions", self.text.lower())

    def test_luhmanns_closure_is_stated_as_a_constraint(self):
        self.assertIn("society thinks", self.text)
        self.assertIn("operative closure", self.text)

    def test_wendt_note_separates_argument_objections_and_status(self):
        for heading in ("**Argument", "**Objections", "**Empirical status"):
            self.assertIn(heading, self.text)
        self.assertIn("No experiment establishes quantum consciousness", self.text)

    def test_the_bridge_back_to_the_multitude_is_meaning_not_consciousness(self):
        self.assertIn("The bridge back to the Multitude", self.text)
        self.assertIn("not through consciousness", self.text)

    def test_every_register_is_used(self):
        for register in ("empirical", "interpretive", "philosophical", "speculative"):
            self.assertIn(register, self.text.lower())

    def test_the_document_links_to_the_megatheory(self):
        self.assertIn("MEGATHEORY.md", self.text)


class CyborgTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = CYBORG.read_text(encoding="utf-8")
        cls.text = flat(cls.raw)

    def test_the_equation_is_stated_verbatim(self):
        self.assertIn("CYBORG = HUMAN + LLM + LANGUAGE + INTERNET", self.text)

    def test_all_four_terms_are_defined(self):
        for term in ("HUMAN", "LLM", "LANGUAGE", "INTERNET"):
            self.assertIn(f"**{term}**", self.text)

    def test_agency_boundaries_are_explicit(self):
        section = self.text.split("## 2. Agency boundaries")[1].split("## 3.")[0]
        self.assertIn("Accountability does not distribute", section)
        self.assertIn("The network is not a mind", section)
        self.assertIn("Extension is a claim, not a default", section)

    def test_five_hypotheses_with_disconfirming_results(self):
        hypotheses = re.findall(r"^### H\d —", self.raw, flags=re.M)
        self.assertEqual(len(hypotheses), 5, hypotheses)
        self.assertIn("Disconfirming result", self.text)
        # one design and one disconfirming result per hypothesis
        self.assertEqual(self.text.count("Disconfirming result"), 5)

    def test_metrics_are_per_cell_not_only_aggregate(self):
        self.assertIn("per cell", self.text)

    def test_failure_modes_include_the_eight_named_in_the_issue(self):
        for mode in ("Hallucination", "Homogenisation", "Echo chambers", "Deskilling",
                     "Dependency", "Power concentration", "Surveillance", "Unequal access"):
            self.assertIn(mode, self.text)

    def test_falsification_summary_covers_every_hypothesis(self):
        section = self.text.split("## 6. Falsification summary")[1].split("## 7.")[0]
        for tag in ("H1", "H2", "H3", "H4", "H5"):
            self.assertIn(tag, section)

    def test_the_model_does_not_claim_consciousness(self):
        self.assertIn("not a claim that a present-day LLM is conscious", self.text)
        self.assertIn("evidence for the *model*, not for panpsychism", self.text)


class SourcesTests(unittest.TestCase):
    def test_peirce_and_spinoza_are_registered(self):
        text = SOURCES.read_text(encoding="utf-8")
        self.assertIn("## 14. Ontology and cyborg assemblage (#91)", text)
        for name in ("Peirce", "Spinoza"):
            self.assertIn(name, text)

    def test_the_additions_are_tagged(self):
        section = SOURCES.read_text(encoding="utf-8").split("## 14.")[1]
        self.assertGreaterEqual(section.count("[book]"), 3)
        self.assertIn("[repository/speculative]", section)


if __name__ == "__main__":
    unittest.main()
