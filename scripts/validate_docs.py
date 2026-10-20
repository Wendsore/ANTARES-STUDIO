"""Validate the foundational documentation only (NOT the application)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md",
    "AGENTS.md",
    "docs/ANTARES_MASTER_PROMPT.md",
    "docs/TEST_STRATEGY.md",
    "docs/RESEARCH_PROTOCOL.md",
    "docs/PROJECT_STATUS.md",
)
CRITICAL = {
    "AGENTS.md": ("autonome", "test", "licence", "PROJECT_STATUS"),
    "docs/ANTARES_MASTER_PROMPT.md": ("Phase 0", "Phase 9", "ManimGL", "Windows 11", "timeline", "ffmpeg"),
    "docs/TEST_STRATEGY.md": ("MOD-01", "TIM-01", "REN-01", "E2E-01", "PKG-01"),
    "docs/RESEARCH_PROTOCOL.md": ("https://", "ADR", "licence"),
}


def validate() -> list[str]:
    errors: list[str] = []
    for filename in REQUIRED:
        path = ROOT / filename
        if not path.is_file():
            errors.append(f"missing: {filename}")
            continue
        content = path.read_text(encoding="utf-8")
        if not content.strip():
            errors.append(f"empty: {filename}")
        if "ASTRA Studio" in content or "ASTRA-STUDIO" in content:
            errors.append(f"old project name in: {filename}")
        for token in CRITICAL.get(filename, ()):
            if token.casefold() not in content.casefold():
                errors.append(f"{filename} missing anchor: {token}")
        for link in re.findall(r"\]\(([^)]+\.md)\)", content):
            if "://" not in link and not (path.parent / link).exists():
                errors.append(f"broken local markdown link: {filename} -> {link}")
    return errors


if __name__ == "__main__":
    issues = validate()
    if issues:
        print("Documentation validation FAILED:")
        print("\n".join(f"- {item}" for item in issues))
        sys.exit(1)
    print(f"Documentation validation PASSED ({len(REQUIRED)} foundational files checked)")
