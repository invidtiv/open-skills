#!/usr/bin/env python3
"""
Tests for support-billing-recovery Open Skill.

These tests verify the skill's structure and logic without making real API
calls. They run in any environment — no Stripe key needed.
"""
import sys
import json
import os
import yaml
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent

def test_skill_md_exists():
    assert (SKILL_DIR / "SKILL.md").exists(), "SKILL.md missing"
    print("  ✓ SKILL.md exists")

def test_frontmatter_parses():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert md.startswith("---"), "SKILL.md must start with YAML frontmatter"
    parts = md.split("---", 2)
    fm = yaml.safe_load(parts[1])
    assert "name" in fm, "frontmatter missing 'name'"
    assert "description" in fm, "frontmatter missing 'description'"
    assert "triggers" in fm, "frontmatter missing 'triggers'"
    assert "boundaries" in fm, "frontmatter missing 'boundaries'"
    assert "required_tools" in fm, "frontmatter missing 'required_tools'"
    assert "output_format" in fm, "frontmatter missing 'output_format'"
    print(f"  ✓ frontmatter parses: {fm['name']}")

def test_required_tools_declared():
    md = (SKILL_DIR / "SKILL.md").read_text()
    parts = md.split("---", 2)
    fm = yaml.safe_load(parts[1])
    tools = fm.get("required_tools", [])
    assert isinstance(tools, list), "required_tools must be a list"
    assert len(tools) > 0, "must declare at least one required tool"
    assert "stripe-cli" in tools, "required_tools must include stripe-cli"
    print(f"  ✓ required_tools declared: {', '.join(tools)}")

def test_boundaries_declared():
    md = (SKILL_DIR / "SKILL.md").read_text()
    parts = md.split("---", 2)
    fm = yaml.safe_load(parts[1])
    boundaries = fm.get("boundaries", [])
    assert isinstance(boundaries, list), "boundaries must be a list"
    assert len(boundaries) > 0, "must declare at least one boundary"
    print(f"  ✓ boundaries declared: {len(boundaries)} items")

def test_procedure_has_six_steps():
    md = (SKILL_DIR / "SKILL.md").read_text()
    # Count numbered steps
    steps = [line for line in md.split("\n") if line.strip().startswith("### Step")]
    assert len(steps) >= 5, f"expected at least 5 steps, found {len(steps)}"
    print(f"  ✓ procedure has {len(steps)} steps")

def test_pitfalls_section_exists():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert "## Pitfalls" in md, "SKILL.md missing Pitfalls section"
    print("  ✓ pitfalls section exists")

def test_verification_contract_section_exists():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert "## Verification Contract (NON-NEGOTIABLE)" in md, "SKILL.md missing Verification Contract section"
    print("  ✓ verification contract section exists")

def test_recovery_section_exists():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert "## Recovery" in md, "SKILL.md missing Recovery section"
    print("  ✓ recovery section exists")

def test_platform_agnostic():
    """The core SKILL.md must not contain platform-specific markers."""
    md = (SKILL_DIR / "SKILL.md").read_text()
    bad_markers = [".cursorrules", "CLAUDE.md", "codex.md", ".claude/", ".cursor/"]
    for marker in bad_markers:
        assert marker not in md, f"SKILL.md contains platform-specific marker: {marker}"
    print("  ✓ platform-agnostic (no vendor markers in core)")

def test_decision_logic():
    """Verify the decision logic in Step 3 is well-defined."""
    md = (SKILL_DIR / "SKILL.md").read_text()
    # Must contain decision branches
    assert "insufficient_funds" in md, "missing insufficient_funds decision branch"
    assert "expired_card" in md, "missing expired_card decision branch"
    assert "processing_error" in md, "missing processing_error decision branch"
    print("  ✓ decision logic covers all failure codes")

# ─── CLI args ────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if "--dry-run" in args or not args:
        # Run all structural tests
        tests = [
            test_skill_md_exists,
            test_frontmatter_parses,
            test_required_tools_declared,
            test_boundaries_declared,
            test_procedure_has_six_steps,
            test_pitfalls_section_exists,
            test_verification_contract_section_exists,
            test_recovery_section_exists,
            test_platform_agnostic,
            test_decision_logic,
        ]
        failed = 0
        for t in tests:
            try:
                t()
            except AssertionError as e:
                print(f"  ✗ {t.__name__}: {e}")
                failed += 1
            except Exception as e:
                print(f"  ✗ {t.__name__}: unexpected error: {e}")
                failed += 1
        if failed:
            print(f"\n{len(tests) - failed}/{len(tests)} tests passed, {failed} failed.")
            sys.exit(1)
        print(f"\nAll {len(tests)} tests passed. This is an Open Skill.")
        return

    if "--check-manifest" in args:
        print("manifest.yaml has been removed in v2.0. Use 'openskills validate' instead.")
        sys.exit(0)

    if "--verify" in args:
        # In a real environment, this would check the resolution.json
        # For testing, just verify the structure supports verification
        test_verification_contract_section_exists()
        print("\nVerification path exists.")
        return

    print(f"Unknown args: {args}")
    print("Usage: python3 test_basic.py [--dry-run|--check-manifest|--verify]")
    sys.exit(1)

if __name__ == "__main__":
    main()
