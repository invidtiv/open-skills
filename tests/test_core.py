"""
Unit tests for core.py — covers parsing, validation, runbook state,
trigger matching, path traversal, and new frontmatter fields.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core


# ── Fixtures ───────────────────────────────────────────────────────────────

VALID_SKILL = """---
name: test-skill
description: A test skill
triggers:
  - "on UI change"
boundaries:
  - "Do not run in production."
required_tools:
  - terminal
output_format: "output.txt"
disable-model-invocation: false
user-invocable: true
---

## Objective
Do the thing.

## Procedure
1. Step one
2. Step two

## Verification Contract (NON-NEGOTIABLE)
- [ ] Check one
- [ ] Check two
"""

VALID_SKILL_NO_OPTIONAL = """---
name: test-skill
description: A test skill
triggers:
  - "on UI change"
boundaries:
  - "Do not run in production."
required_tools:
  - terminal
output_format: "output.txt"
---

## Objective
Do the thing.

## Procedure
1. Step one

## Verification Contract (NON-NEGOTIABLE)
- [ ] Check one
"""

INVALID_SKILL_MISSING_FIELDS = """---
name: test-skill
---

## Objective
Do the thing.
"""

INVALID_SKILL_PLATFORM_SPECIFIC = """---
name: test-skill
description: A test skill
triggers:
  - "on UI change"
boundaries:
  - "Do not run in production."
required_tools:
  - terminal
output_format: "output.txt"
---

## Objective
Do the thing.

## Procedure
1. See .cursorrules for config

## Verification Contract (NON-NEGOTIABLE)
- [ ] Check one
"""

INVALID_SKILL_NO_CHECKLIST = """---
name: test-skill
description: A test skill
triggers:
  - "on UI change"
boundaries:
  - "Do not run in production."
required_tools:
  - terminal
output_format: "output.txt"
---

## Objective
Do the thing.

## Procedure
1. Step one

## Verification Contract (NON-NEGOTIABLE)
No checklist here.
"""


# ── slugify ────────────────────────────────────────────────────────────────

def test_slugify_basic():
    assert core.slugify("My Skill Name") == "my-skill-name"

def test_slugify_special_chars():
    assert core.slugify("My_Skill!@#Name") == "my-skill-name"

def test_slugify_empty():
    try:
        core.slugify("!!!")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_slugify_already_clean():
    assert core.slugify("test-skill") == "test-skill"


# ── parse_frontmatter ──────────────────────────────────────────────────────

def test_parse_frontmatter_valid():
    fm, body = core.parse_frontmatter(VALID_SKILL)
    assert fm["name"] == "test-skill"
    assert "## Objective" in body

def test_parse_frontmatter_none():
    fm, body = core.parse_frontmatter("No frontmatter here")
    assert fm == {}
    assert "No frontmatter here" in body

def test_parse_frontmatter_unclosed():
    text = "---\nname: test\n\ntitle: Test\n\n## Objective\nDo something.\n"
    fm, body = core.parse_frontmatter(text)
    assert fm.get("name") == "test"
    assert "## Objective" in body


# ── validate_skill_content ─────────────────────────────────────────────────

def test_validate_valid_skill():
    result = core.validate_skill_content(VALID_SKILL)
    assert result["valid"], f"Errors: {result['errors']}"

def test_validate_missing_fields():
    result = core.validate_skill_content(INVALID_SKILL_MISSING_FIELDS)
    assert not result["valid"]
    assert any("description" in e for e in result["errors"])
    assert any("triggers" in e for e in result["errors"])

def test_validate_platform_specific():
    result = core.validate_skill_content(INVALID_SKILL_PLATFORM_SPECIFIC)
    assert not result["valid"]
    assert any("platform-specific" in e for e in result["errors"])

def test_validate_no_checklist():
    result = core.validate_skill_content(INVALID_SKILL_NO_CHECKLIST)
    assert not result["valid"]
    assert any("checklist" in e for e in result["errors"])

def test_validate_optional_fields_present():
    result = core.validate_skill_content(VALID_SKILL)
    checks = [c["label"] for c in result["checks"]]
    assert any("disable-model-invocation" in c for c in checks)
    assert any("user-invocable" in c for c in checks)

def test_validate_optional_fields_absent_uses_defaults():
    result = core.validate_skill_content(VALID_SKILL_NO_OPTIONAL)
    assert result["valid"], f"Errors: {result['errors']}"
    fm, _ = core.parse_frontmatter(VALID_SKILL_NO_OPTIONAL)
    assert fm.get("disable-model-invocation") is None
    assert fm.get("user-invocable") is None

def test_validate_optional_fields_wrong_type():
    skill = VALID_SKILL.replace(
        "disable-model-invocation: false",
        'disable-model-invocation: "yes"',
    )
    result = core.validate_skill_content(skill)
    assert not result["valid"]
    assert any("disable-model-invocation" in e and "boolean" in e for e in result["errors"])

def test_validate_returns_warnings_key():
    result = core.validate_skill_content(VALID_SKILL)
    assert "warnings" in result
    assert isinstance(result["warnings"], list)


# ── _safe_child / path traversal ───────────────────────────────────────────

def test_safe_child_valid():
    base = Path(tempfile.mkdtemp())
    child = core._safe_child(base, "test-skill")
    assert child == (base / "test-skill").resolve()

def test_safe_child_traversal_blocked():
    base = Path(tempfile.mkdtemp())
    try:
        core._safe_child(base, "../../../etc/passwd")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass

def test_safe_child_nested_traversal_blocked():
    base = Path(tempfile.mkdtemp())
    try:
        core._safe_child(base, "valid/../../../etc/passwd")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


# ── match_triggers ─────────────────────────────────────────────────────────

def test_match_triggers_substring():
    skills = [{
        "name": "test-skill",
        "scope": "Local",
        "triggers": ["on UI change"],
        "description": "test",
        "body": "body",
        "disable_model_invocation": False,
    }]
    matches = core.match_triggers("please handle the UI change", skills=skills)
    assert len(matches) == 1
    assert matches[0]["name"] == "test-skill"

def test_match_triggers_word_overlap():
    skills = [{
        "name": "test-skill",
        "scope": "Local",
        "triggers": ["refund request billing"],
        "description": "test",
        "body": "body",
        "disable_model_invocation": False,
    }]
    matches = core.match_triggers("I need a refund for my billing request", skills=skills)
    assert len(matches) == 1

def test_match_triggers_no_match():
    skills = [{
        "name": "test-skill",
        "scope": "Local",
        "triggers": ["on UI change"],
        "description": "test",
        "body": "body",
        "disable_model_invocation": False,
    }]
    matches = core.match_triggers("help me with database migration", skills=skills)
    assert len(matches) == 0

def test_match_triggers_disable_model_invocation():
    skills = [{
        "name": "test-skill",
        "scope": "Local",
        "triggers": ["on UI change"],
        "description": "test",
        "body": "body",
        "disable_model_invocation": True,
    }]
    matches = core.match_triggers("please handle the UI change", skills=skills)
    assert len(matches) == 0, "disable-model-invocation should exclude from matching"


# ── runbook state ──────────────────────────────────────────────────────────

def test_runbook_state_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "get_local_dir", lambda: tmp_path)

    runbook_dir = tmp_path / "runbooks"
    runbook_dir.mkdir(parents=True)
    rb_file = runbook_dir / "test-rb.md"
    rb_file.write_text(
        "# Runbook: Test\n\n"
        "Phase | Active Skill | Input | Expected Verified Output\n"
        "---|---|---|---\n"
        "01 | skill-a | input-a | output-a\n"
        "02 | skill-b | input-b | output-b\n"
    )

    # Start
    result = core.start_runbook("test-rb")
    assert result["status"] == "success"
    assert result["state"]["current_phase"] == "01"
    assert "warnings" in result

    # Advance
    result = core.advance_runbook()
    assert result["status"] == "success"
    assert result["state"]["current_phase"] == "02"

    # Advance to end
    result = core.advance_runbook()
    assert result["status"] == "success"
    assert result["state"]["current_phase"] is None

    # Prev from end
    result = core.prev_runbook()
    assert result["status"] == "success"
    assert result["state"]["current_phase"] == "02"

    # Reset
    result = core.reset_runbook()
    assert result["status"] == "success"
    assert not core.get_runbook_state_file().exists()

def test_start_runbook_missing_skills_warning(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "get_local_dir", lambda: tmp_path)
    monkeypatch.setattr(core, "get_global_dir", lambda: tmp_path / "global")

    runbook_dir = tmp_path / "runbooks"
    runbook_dir.mkdir(parents=True)
    rb_file = runbook_dir / "test-rb.md"
    rb_file.write_text(
        "# Runbook: Test\n\n"
        "Phase | Active Skill | Input | Expected Verified Output\n"
        "---|---|---|---\n"
        "01 | nonexistent-skill | input-a | output-a\n"
    )

    result = core.start_runbook("test-rb")
    assert result["status"] == "success"
    assert len(result["warnings"]) > 0
    assert "nonexistent-skill" in result["warnings"][0]

def test_start_runbook_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "get_local_dir", lambda: tmp_path)
    monkeypatch.setattr(core, "get_global_dir", lambda: tmp_path / "global")

    result = core.start_runbook("does-not-exist")
    assert result["status"] == "error"

def test_advance_no_active(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "get_local_dir", lambda: tmp_path)
    result = core.advance_runbook()
    assert result["status"] == "error"


# ── adapter staleness ──────────────────────────────────────────────────────

def test_adapter_staleness_warning(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(VALID_SKILL)

    adapter_dir = skill_dir / "adapters"
    adapter_dir.mkdir()
    adapter_file = adapter_dir / "claude-code.md"
    adapter_file.write_text("old adapter content")

    # Set adapter mtime to past
    import os
    old_time = skill_file.stat().st_mtime - 100
    os.utime(adapter_file, (old_time, old_time))

    result = core.validate_skill_content(VALID_SKILL, skill_dir=skill_dir)
    assert len(result["warnings"]) > 0
    assert "stale" in result["warnings"][0].lower()

def test_adapter_not_stale(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(VALID_SKILL)

    adapter_dir = skill_dir / "adapters"
    adapter_dir.mkdir()
    adapter_file = adapter_dir / "claude-code.md"
    adapter_file.write_text("fresh adapter content")

    result = core.validate_skill_content(VALID_SKILL, skill_dir=skill_dir)
    assert len(result["warnings"]) == 0

def test_no_adapter_dir_no_warning(tmp_path):
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(VALID_SKILL)

    result = core.validate_skill_content(VALID_SKILL, skill_dir=skill_dir)
    assert len(result["warnings"]) == 0


# ── runbook parsing ────────────────────────────────────────────────────────

def test_parse_runbook_basic(tmp_path):
    rb = tmp_path / "test.md"
    rb.write_text(
        "# Runbook: Test\n\n"
        "Phase | Active Skill | Input | Expected Verified Output\n"
        "---|---|---|---\n"
        "01 | skill-a | input-a | output-a\n"
        "02 | skill-b | input-b | output-b\n"
    )
    phases = core.parse_runbook(rb)
    assert len(phases) == 2
    assert phases[0]["phase"] == "01"
    assert phases[0]["skill"] == "skill-a"
    assert phases[0]["status"] == "pending"

def test_parse_runbook_empty(tmp_path):
    rb = tmp_path / "empty.md"
    rb.write_text("# Just a title\n\nNo table here.\n")
    phases = core.parse_runbook(rb)
    assert len(phases) == 0


if __name__ == "__main__":
    # Allow running directly: python3 tests/test_core.py
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
