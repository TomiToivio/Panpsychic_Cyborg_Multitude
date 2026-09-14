import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from multitude.integrations.claude import ClaudeCodeAdapter, ClaudePermissions, ClaudeTools
from multitude.integrations.hermes.adapter import HermesPermissions, HermesPermissionError
from multitude.models import Position
from multitude.rhizome import Rhizome


class ClaudeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = os.path.join(self.tmp.name, "r")
        os.makedirs(root)
        self.rhizome = Rhizome.found(root, "Agent Rhizome", "Keep authority explicit.", "Alice")
        self.adapter = ClaudeCodeAdapter(self.rhizome)
        self.tools = ClaudeTools(self.adapter)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_claude_dependency_and_stable_identity(self):
        member = self.adapter.ensure_agent()
        self.assertEqual(member.name, "agent:claude-code")
        self.assertEqual(member.meta["runtime"], "claude-code")
        self.assertIsNone(member.profile.psychic.is_conscious)

    def test_same_permissions_class_and_fail_closed_vote(self):
        self.assertIs(ClaudePermissions, HermesPermissions)
        proposal = self.rhizome.open_proposal("Test", "No automatic authority", opened_by="Alice")
        with self.assertRaises(HermesPermissionError):
            self.tools.vote(proposal.id, Position.FOR.value)

    def test_proposal_uses_pcm_service_and_actor_provenance(self):
        proposal = self.tools.propose("Research note", "Inspect evidence first.")
        self.assertEqual(proposal.opened_by, "agent:claude-code")
        opened = [e for e in self.rhizome.store.replay() if e.type == "proposal_opened"][-1]
        self.assertEqual(opened.actor, "agent:claude-code")

    def test_no_admin_authority_by_default(self):
        perms = ClaudePermissions().as_dict()
        for key in ("vote", "block", "modify_governance", "delete_history", "spend_money"):
            self.assertFalse(perms[key])

    def test_consciousness_is_not_authority(self):
        self.assertFalse(self.adapter.audit_context(action="inspect")["consciousness_authority"])


if __name__ == "__main__":
    unittest.main()
