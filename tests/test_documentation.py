"""Documentation smoke tests only, not application feature tests."""
from pathlib import Path
import sys
import unittest

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

    def test_status_does_not_claim_app_is_done(self) -> None:
        content = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Logiciel développé : non", content)

if __name__ == "__main__":
    unittest.main()
