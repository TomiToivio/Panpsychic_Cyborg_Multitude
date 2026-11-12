# -*- coding: utf-8 -*-
"""Issue #89 — the megatheory documents exist, name their own commitments, and do not rot.

The issue asks for seven artefacts: an overview, a conceptual map, a tensions matrix, a claim taxonomy,
a LaclauGPT boundary statement, an annotated reading list, and research questions. Prose cannot be
tested, but the properties that make the prose usable can be:

* every layer assignment is *named*, so a reader can see which thinker is foundational, which is a
  bridge, and which is speculative — the failure this guards against is a synthesis that reads as
  agreement because nothing was sorted;
* the tensions matrix keeps the rows the issue says must not be erased (Laclau-Negri, Laclau-Žižek,
  social systems versus consciousness, competing consciousness ontologies) — deleting a disagreement is
  a quiet way of resolving it;
* the boundary statement stays present in the overview, because it is the one thing in the megatheory
  that is meant to be binding on the empirical programme;
* no relative link in these documents points at nothing. A theory document whose links rot becomes a
  document nobody follows, and the reading list is only useful if it is navigable.

Run: python3 -m unittest discover -s tests -p 'test_*.py'
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

OVERVIEW = DOCS / "MEGATHEORY.md"
TENSIONS = DOCS / "MEGATHEORY_TENSIONS.md"
READING = DOCS / "MEGATHEORY_READING_PATH.md"
SOURCES = DOCS / "research" / "SOURCES.md"

SIX_THINKERS = ("Laclau", "Negri", "Žižek", "Brier", "Wendt", "Haraway")

REQUIRED_TENSION_ROWS = (
    "L ↔ N",
    "L ↔ Ž",
    "Luhmann",
    "Faggin",
    "Kastrup",
    "Hoffman",
)


class DocumentsExist(unittest.TestCase):
    def test_the_three_megatheory_documents_exist_and_are_not_stubs(self):
        for path, minimum in ((OVERVIEW, 200), (TENSIONS, 80), (READING, 80)):
            with self.subTest(document=path.name):
                self.assertTrue(path.exists(), f"{path.name} is missing")
                lines = path.read_text(encoding="utf-8").splitlines()
                self.assertGreater(len(lines), minimum, f"{path.name} looks like a stub")


class OverviewNamesItsCommitments(unittest.TestCase):
    def setUp(self):
        self.text = OVERVIEW.read_text(encoding="utf-8")

    def test_all_six_principal_thinkers_are_named(self):
        for thinker in SIX_THINKERS:
            with self.subTest(thinker=thinker):
                self.assertIn(thinker, self.text)

    def test_the_commitment_classes_are_distinguished(self):
        """Foundational, bridging and speculative must be words in the document, not a vibe."""
        for word in ("Foundational", "Bridging", "speculative"):
            with self.subTest(word=word):
                self.assertIn(word, self.text)

    def test_the_conceptual_map_is_present(self):
        self.assertIn("```text", self.text, "the conceptual map must render as preformatted text")

    def test_the_claim_taxonomy_is_empirical_interpretive_and_speculative(self):
        for heading in ("### Empirical", "### Interpretive", "### Speculative"):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.text)

    def test_the_laclaugpt_boundary_is_stated_as_a_rule(self):
        self.assertIn("must not be silently transferred", self.text)
        self.assertIn("Direction of inclusion", self.text)

    def test_the_research_questions_number_at_least_five(self):
        numbers = re.findall(r"\*\*RQ(\d+)\.\*\*", self.text)
        self.assertGreaterEqual(len(set(numbers)), 5, f"found RQ numbers {sorted(set(numbers))}")

    def test_the_worked_examples_are_present(self):
        self.assertIn("### 8.1", self.text)
        self.assertIn("### 8.2", self.text)


class TensionsMatrixKeepsTheDisagreements(unittest.TestCase):
    def setUp(self):
        self.text = TENSIONS.read_text(encoding="utf-8")

    def test_the_rows_the_issue_requires_are_kept(self):
        for marker in REQUIRED_TENSION_ROWS:
            with self.subTest(marker=marker):
                self.assertIn(marker, self.text)

    def test_each_pair_row_states_what_would_have_to_be_given_up(self):
        """A tension with no cost is a comparison, not a tension."""
        self.assertGreaterEqual(self.text.count("What would have to be given up"), 2)

    def test_the_matrix_records_pcm_s_own_tensions_too(self):
        self.assertIn("Tensions that PCM itself creates", self.text)


class ReadingPathIsAnnotated(unittest.TestCase):
    def setUp(self):
        self.text = READING.read_text(encoding="utf-8")

    def test_each_principal_thinker_has_a_section(self):
        for thinker in SIX_THINKERS:
            with self.subTest(thinker=thinker):
                self.assertIn(thinker, self.text)

    def test_the_path_defers_to_the_canonical_bibliography(self):
        self.assertIn("research/SOURCES.md", self.text)

    def test_it_states_what_each_text_costs_the_framework(self):
        self.assertIn("The seam it opens", self.text)


class BibliographyRegistersThePrimaries(unittest.TestCase):
    def test_sources_carries_a_megatheory_section(self):
        text = SOURCES.read_text(encoding="utf-8")
        self.assertIn("## 13. Megatheory primary sources", text)
        for author in ("Laclau", "Negri", "Žižek", "Brier", "Wendt", "Haraway"):
            with self.subTest(author=author):
                self.assertIn(author, text)


class NoDeadRelativeLinks(unittest.TestCase):
    DOCUMENTS = (OVERVIEW, TENSIONS, READING, SOURCES, ROOT / "README.md",
                 DOCS / "research" / "README.md")

    def test_every_relative_markdown_link_resolves(self):
        pattern = re.compile(r"\[([^\]]+)\]\(([^)#\s]+)(?:#[^)]*)?\)")
        dead: list[str] = []
        for document in self.DOCUMENTS:
            text = document.read_text(encoding="utf-8")
            for label, target in pattern.findall(text):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if not (document.parent / target).resolve().exists():
                    dead.append(f"{document.relative_to(ROOT)}: [{label}]({target})")
        self.assertFalse(dead, "dead relative links:\n" + "\n".join(dead))


if __name__ == "__main__":
    unittest.main()
