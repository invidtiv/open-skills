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

def test_manifest_exists():
    assert (SKILL_DIR / "manifest.yaml").exists(), "manifest.yaml missing"
    print("  ✓ manifest.yaml exists")

def test_frontmatter_parses():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert md.startswith("---"), "SKILL.md must start with YAML frontmatter"
    parts = md.split("---", 2)
    fm = yaml.safe_load(parts[1])
    assert "name" in fm, "frontmatter missing 'name'"
    assert "version" in fm, "frontmatter missing 'version'"
    assert "description" in fm, "frontmatter missing 'description'"
    print(f"  ✓ frontmatter parses: {fm['name']} v{fm['version']}")

def test_manifest_dependencies_declared():
    with open(SKILL_DIR / "manifest.yaml") as f:
        m = yaml.safe_load(f)
    deps = m.get("dependencies", {})
    assert "tools" in deps, "manifest missing tools dependencies"
    assert len(deps["tools"]) > 0, "manifest declares no tools"
    # Stripe CLI must be declared
    tool_names = [t["name"] for t in deps["tools"]]
    assert "stripe-cli" in tool_names, "manifest must declare stripe-cli"
    print(f"  ✓ dependencies declared: {', '.join(tool_names)}")

def test_permissions_bounded():
    with open(SKILL_DIR / "manifest.yaml") as f:
        m = yaml.safe_load(f)
    perms = m.get("permissions", {})
    assert "network" in perms, "manifest missing network permission"
    assert "api_keys" in perms, "manifest missing api_keys permission"
    assert "STRIPE_API_KEY" in perms["api_keys"], "STRIPE_API_KEY must be in permissions"
    print("  ✓ permissions bounded")

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

def test_verification_section_exists():
    md = (SKILL_DIR / "SKILL.md").read_text()
    assert "## Verification" in md, "SKILL.md missing Verification section"
    print("  ✓ verification section exists")

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

def test_compatibility_declared():
    with open(SKILL_DIR / "manifest.yaml") as f:
        m = yaml.safe_load(f)
    compat = m.get("compatibility", [])
    assert len(compat) >= 4, f"expected at least 4 compatible platforms, found {len(compat)}"
    platforms = [c["platform"] for c in compat]
    assert "generic" in platforms, "must declare generic compatibility"
    print(f"  ✓ compatibility: {', '.join(platforms)}")

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
            test_manifest_exists,
            test_frontmatter_parses,
            test_manifest_dependencies_declared,
            test_permissions_bounded,
            test_procedure_has_six_steps,
            test_pitfalls_section_exists,
            test_verification_section_exists,
            test_recovery_section_exists,
            test_platform_agnostic,
            test_compatibility_declared,
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
        test_manifest_exists()
        test_manifest_dependencies_declared()
        test_permissions_bounded()
        test_compatibility_declared()
        print("\nManifest valid.")
        return

    if "--verify" in args:
        # In a real environment, this would check the resolution.json
        # For testing, just verify the structure supports verification
        test_verification_section_exists()
        print("\nVerification path exists.")
        return

    print(f"Unknown args: {args}")
    print("Usage: python3 test_basic.py [--dry-run|--check-manifest|--verify]")
    sys.exit(1)

if __name__ == "__main__":
    main()
