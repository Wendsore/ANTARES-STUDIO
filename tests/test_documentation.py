"""Documentation smoke tests only, not application feature tests."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_docs import validate  # noqa: E402


class DocumentationTests(unittest.TestCase):
    def test_foundational_documents_are_coherent(self) -> None:
        self.assertEqual([], validate())

    def test_master_has_phase_zero_mission(self) -> None:
        content = (ROOT / "docs/ANTARES_MASTER_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("Première mission exécutable", content)
        self.assertIn("PoC", content)

    def test_status_does_not_claim_mvp_is_done_without_proof(self) -> None:
        """Le statut porte l'état du MVP ; « MVP candidat : oui » exige un parcours P1 prouvé."""
        content = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("MVP candidat :", content)
        if "MVP candidat : oui" in content:
            self.assertIn("parcours P1", content)
            self.assertIn("Windows", content)


if __name__ == "__main__":
    unittest.main()
