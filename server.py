"""
server — FastAPI backend for Open Skills web frontend.

Wraps core.py as a REST API and serves the built SPA.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import core

app = FastAPI(title="Open Skills", version=core.VERSION)

# ── Authentication ─────────────────────────────────────────────────────────

_API_TOKEN = os.environ.get("OPENSKILLS_API_TOKEN")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Shared-secret auth. Skips for localhost if no token is configured."""
    if _API_TOKEN:
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]
        if token != _API_TOKEN:
            return Response(status_code=401, content='{"detail":"Unauthorized"}', media_type="application/json")
    return await call_next(request)

# ── Request/Response models ────────────────────────────────────────────────

class CreateSkillRequest(BaseModel):
    name: str
    scope: str = "global"

class SaveSkillRequest(BaseModel):
    content: str

class SaveStructuredSkillRequest(BaseModel):
    frontmatter: dict
    body: str

class AddSkillRequest(BaseModel):
    path: str
    scope: str = "global"

class ImportGithubRequest(BaseModel):
    url: str
    scope: str = "global"
    subdir: str = ""

class ValidationCheck(BaseModel):
    label: str
    passed: bool
    detail: str = ""

class ValidationResult(BaseModel):
    valid: bool
    checks: list[ValidationCheck]
    errors: list[str]
    warnings: list[str] = []

# ── Validation logic (extracted from CLI) ──────────────────────────────────

def validate_skill_content(content: str, skill_dir: Path = None) -> ValidationResult:
    result = core.validate_skill_content(content, skill_dir=skill_dir)
    return ValidationResult(
        valid=result["valid"],
        checks=[ValidationCheck(**c) for c in result["checks"]],
        errors=result["errors"],
        warnings=result.get("warnings", []),
    )


def _resolve_or_404(name: str) -> tuple[Path, Path]:
    skill_dir, skill_file = core.resolve_skill(name)
    if not skill_file or not skill_file.exists():
        raise HTTPException(404, f"Skill '{name}' not found")
    return skill_dir, skill_file


# ── Skills endpoints ───────────────────────────────────────────────────────

@app.get("/api/skills")
def list_skills():
    skills, shadowed = core.get_all_skills()
    return {
        "skills": [
            {
                "name": s["name"],
                "scope": s["scope"],
                "path": str(s["path"]),
                "description": s["description"],
                "triggers": [str(t) if not isinstance(t, str) else t for t in (s["triggers"] or [])],
                "boundaries": [str(b) if not isinstance(b, str) else b for b in (s["boundaries"] or [])],
                "required_tools": [str(r) if not isinstance(r, str) else r for r in (s["required_tools"] or [])],
                "output_format": s["output_format"],
                "disable_model_invocation": s.get("disable_model_invocation", False),
                "user_invocable": s.get("user_invocable", True),
            }
            for s in sorted(skills, key=lambda x: x["name"])
        ],
        "shadowed": shadowed,
    }


@app.get("/api/skills/{name}")
def get_skill(name: str):
    skill_dir, skill_file = _resolve_or_404(name)
    content = skill_file.read_text()
    fm, body = core.parse_frontmatter(content)

    files = []
    for p in sorted(skill_dir.rglob("*")):
        if p.is_file():
            files.append(str(p.relative_to(skill_dir)))

    return {
        "name": fm.get("name", name),
        "scope": _scope_for_dir(skill_dir),
        "path": str(skill_file),
        "dir": str(skill_dir),
        "content": content,
        "frontmatter": fm,
        "body": body,
        "files": files,
    }


@app.post("/api/skills")
def create_skill(req: CreateSkillRequest):
    try:
        safe = core.slugify(req.name)
    except ValueError:
        raise HTTPException(400, f"Invalid skill name '{req.name}': slugified result is empty")
    base_dir = core.get_local_dir() if req.scope == "local" else core.get_global_dir()
    target_dir = base_dir / "skills" / safe

    if target_dir.exists():
        raise HTTPException(409, f"Skill '{safe}' already exists")

    target_dir.mkdir(parents=True)
    skill_file = target_dir / "skill.md"
    skill_file.write_text(core.SKELETON_SKILL.format(name=safe))
    (target_dir / "tests").mkdir(exist_ok=True)
    (target_dir / "tests" / ".gitkeep").write_text("")

    return {"name": safe, "path": str(skill_file), "scope": req.scope}


@app.put("/api/skills/{name}")
def save_skill(name: str, req: SaveSkillRequest):
    _, skill_file = _resolve_or_404(name)
    skill_file.write_text(req.content)
    fm, body = core.parse_frontmatter(req.content)
    return {"saved": True, "name": fm.get("name", name)}


@app.put("/api/skills/{name}/structured")
def save_skill_structured(name: str, req: SaveStructuredSkillRequest):
    """Save a skill from structured frontmatter + body, serializing YAML server-side."""
    _, skill_file = _resolve_or_404(name)
    import yaml as _yaml
    fm_yaml = _yaml.dump(req.frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    content = f"---\n{fm_yaml}---\n\n{req.body}\n"
    skill_file.write_text(content)
    return {"saved": True, "name": req.frontmatter.get("name", name)}


@app.delete("/api/skills/{name}")
def delete_skill(name: str):
    skill_dir, _ = _resolve_or_404(name)
    shutil.rmtree(skill_dir)
    return {"deleted": True, "name": name}


@app.post("/api/skills/{name}/validate")
def validate_skill(name: str):
    skill_dir, skill_file = _resolve_or_404(name)
    content = skill_file.read_text()
    return validate_skill_content(content, skill_dir=skill_dir)


class SuggestFixRequest(BaseModel):
    errors: list[str]
    warnings: list[str] = []


@app.post("/api/skills/{name}/suggest-fix")
def suggest_fix(name: str, req: SuggestFixRequest):
    from openskills import get_api_key, EXTRACT_API_BASE, EXTRACT_MODEL
    import urllib.request

    _, skill_file = _resolve_or_404(name)
    content = skill_file.read_text()

    api_key = get_api_key()
    if not api_key:
        raise HTTPException(400, "No API key found. Set OPENROUTER_API_KEY.")

    issues = "\n".join(f"- ERROR: {e}" for e in req.errors)
    if req.warnings:
        issues += "\n" + "\n".join(f"- WARNING: {w}" for w in req.warnings)

    system_prompt = (
        "You are an expert at writing Open Skill markdown files.\n"
        "The user will provide a skill file that failed validation, along with the specific errors.\n"
        "Return ONLY the corrected skill file content — raw markdown starting with ---.\n"
        "Do NOT wrap the response in ```markdown code fences.\n"
        "Fix every listed error while preserving the user's intent and existing content.\n"
        "If a required section is missing, add a minimal placeholder.\n"
        "If a frontmatter field is missing or malformed, add or fix it."
    )

    data = {
        "model": EXTRACT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": (
                f"This skill file failed validation with these issues:\n{issues}\n\n"
                f"Here is the current skill file content:\n\n{content}"
            )},
        ],
        "temperature": 0.2,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    http_req = urllib.request.Request(
        EXTRACT_API_BASE,
        data=__import__("json").dumps(data).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(http_req, timeout=90) as response:
            res_data = __import__("json").loads(response.read().decode("utf-8"))
            suggestion = res_data["choices"][0]["message"]["content"]
            suggestion = re.sub(r'\n*CRITICAL RULES:.*', '', suggestion, flags=re.DOTALL).rstrip() + "\n"
            suggestion = re.sub(r'^```\w*\n?', '', suggestion)
            suggestion = re.sub(r'\n?```$', '', suggestion)
            fm, body = core.parse_frontmatter(suggestion)
            return {"suggestion": suggestion, "frontmatter": fm, "body": body}
    except Exception as e:
        raise HTTPException(502, f"LLM API call failed: {e}")


@app.post("/api/skills/add")
def add_skill(req: AddSkillRequest):
    src = Path(req.path).resolve()
    if not src.is_dir():
        raise HTTPException(400, f"Path '{req.path}' is not a directory")

    home = Path.home().resolve()
    if not src.is_relative_to(home):
        raise HTTPException(403, "Import path must be inside the user's home directory")

    skill_file = core.find_skill_file(src)
    if not skill_file:
        raise HTTPException(400, f"No skill.md found in '{req.path}'")

    fm, _ = core.parse_frontmatter(skill_file.read_text())
    skill_name = fm.get("name")
    if not skill_name:
        raise HTTPException(400, "Skill has no 'name' field in frontmatter")

    try:
        safe = core.slugify(skill_name)
    except ValueError:
        raise HTTPException(400, f"Invalid skill name '{skill_name}': slugified result is empty")
    base_dir = core.get_local_dir() if req.scope == "local" else core.get_global_dir()
    target_dir = base_dir / "skills" / safe

    if target_dir.exists():
        raise HTTPException(409, f"Skill '{safe}' already exists")

    target_dir.mkdir(parents=True)
    shutil.copytree(src, target_dir, dirs_exist_ok=True)
    return {"name": safe, "scope": req.scope, "path": str(target_dir)}


def _parse_github_url(url: str) -> tuple[str, str, str, str]:
    """Parse a GitHub URL into (owner, repo, branch, subdir).

    Supports:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch/path/to/skill
      github.com/owner/repo
      owner/repo
    """
    url = url.strip().rstrip("/")
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")
    if not url.startswith("http"):
        if "/" in url and not url.startswith("github.com"):
            url = f"https://github.com/{url}"
        else:
            url = f"https://{url}"

    url = re.sub(r"\.git$", "", url)
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+)(?:/(.+))?)?", url)
    if not m:
        raise ValueError(f"Could not parse GitHub URL: {url}")
    owner, repo, branch, subdir = m.group(1), m.group(2), m.group(3) or "", m.group(4) or ""
    return owner, repo, branch, subdir


@app.post("/api/skills/import-github")
def import_github(req: ImportGithubRequest):
    try:
        owner, repo, branch, url_subdir = _parse_github_url(req.url)
    except ValueError as e:
        raise HTTPException(400, str(e))

    subdir = req.subdir or url_subdir
    clone_url = f"https://github.com/{owner}/{repo}.git"

    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [clone_url, tmp + "/repo"]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise HTTPException(
                400,
                f"git clone failed: {result.stderr.strip() or result.stdout.strip()}",
            )

        src = Path(tmp) / "repo"
        if subdir:
            src = src / subdir

        if not src.is_dir():
            raise HTTPException(400, f"Subdirectory '{subdir}' not found in repo")

        skill_file = core.find_skill_file(src)
        if not skill_file:
            subdirs = [d.name for d in sorted(src.iterdir()) if d.is_dir() and core.find_skill_file(d)]
            if subdirs:
                raise HTTPException(
                    400,
                    f"No skill.md in root, but found skills in subdirectories: {', '.join(subdirs)}. "
                    f"Specify one with the subdir field.",
                )
            raise HTTPException(400, f"No skill.md found in {owner}/{repo}" + (f"/{subdir}" if subdir else ""))

        fm, _ = core.parse_frontmatter(skill_file.read_text())
        skill_name = fm.get("name", src.name)

        try:
            safe = core.slugify(skill_name)
        except ValueError:
            safe = re.sub(r"[^a-z0-9-]", "-", repo.lower())
            safe = re.sub(r"-+", "-", safe).strip("-")
        if not safe:
            raise HTTPException(400, "Could not derive a valid skill name")

        base_dir = core.get_local_dir() if req.scope == "local" else core.get_global_dir()
        target_dir = base_dir / "skills" / safe

        if target_dir.exists():
            raise HTTPException(409, f"Skill '{safe}' already exists")

        shutil.rmtree(src / ".git", ignore_errors=True)
        target_dir.mkdir(parents=True)
        shutil.copytree(src, target_dir, dirs_exist_ok=True)

        return {
            "name": safe,
            "scope": req.scope,
            "path": str(target_dir),
            "source": f"https://github.com/{owner}/{repo}" + (f"/tree/{branch}/{subdir}" if subdir else ""),
        }


@app.post("/api/skills/extract")
def extract_skill():
    from openskills import get_last_session_transcript, get_api_key, call_llm_completion, extract_skill_name_from_md

    transcript = get_last_session_transcript()
    if not transcript:
        raise HTTPException(400, "No recent chat session found")

    api_key = get_api_key()
    if not api_key:
        raise HTTPException(400, "No API key found. Set OPENROUTER_API_KEY.")

    try:
        skill_content = call_llm_completion(api_key, transcript)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    skill_content = re.sub(
        r'\n*CRITICAL RULES:.*', '', skill_content, flags=re.DOTALL,
    ).rstrip() + "\n"

    name = extract_skill_name_from_md(skill_content)
    pending_dir = core.get_local_dir() / "skills" / "pending-review" / name
    pending_dir.mkdir(parents=True, exist_ok=True)
    (pending_dir / "skill.md").write_text(skill_content)

    return {"name": name, "path": str(pending_dir / "skill.md")}


@app.get("/api/skills/{name}/files")
def list_skill_files(name: str):
    skill_dir, _ = _resolve_or_404(name)
    files = []
    for p in sorted(skill_dir.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(skill_dir))
            files.append({"path": rel, "size": p.stat().st_size})
    return {"files": files}


@app.get("/api/skills/{name}/files/{filepath:path}")
def read_skill_file(name: str, filepath: str):
    skill_dir, _ = _resolve_or_404(name)
    try:
        target = core._safe_child(skill_dir, filepath)
    except ValueError:
        raise HTTPException(403, "Path traversal blocked")

    if not target.is_file():
        raise HTTPException(404, f"File '{filepath}' not found")

    try:
        content = target.read_text()
        return {"path": filepath, "content": content}
    except UnicodeDecodeError:
        raise HTTPException(400, "Binary file — cannot read as text")


# ── Runbook endpoints ──────────────────────────────────────────────────────

@app.get("/api/runbooks")
def list_runbooks():
    runbooks = []
    for scope_name, scope_dir in [("Local", core.get_local_dir()), ("Global", core.get_global_dir())]:
        rb_dir = scope_dir / "runbooks"
        if rb_dir.is_dir():
            for f in sorted(rb_dir.glob("*.md")):
                phases = core.parse_runbook(f)
                runbooks.append({
                    "name": f.stem,
                    "scope": scope_name,
                    "path": str(f),
                    "phase_count": len(phases),
                })
    return {"runbooks": runbooks}


@app.get("/api/runbooks/state")
def get_runbook_state():
    state = core.read_runbook_state()
    if not state:
        return {"active": False}
    return {"active": True, **state}


@app.post("/api/runbooks/{name}/start")
def start_runbook_endpoint(name: str):
    result = core.start_runbook(name)
    if result["status"] == "error":
        raise HTTPException(400, result["message"])
    return result


@app.post("/api/runbooks/advance")
def advance_runbook():
    result = core.advance_runbook()
    if result["status"] == "error":
        raise HTTPException(400, result["message"])
    return result


@app.post("/api/runbooks/prev")
def prev_runbook():
    result = core.prev_runbook()
    if result["status"] == "error":
        raise HTTPException(400, result["message"])
    return result


@app.post("/api/runbooks/reset")
def reset_runbook():
    return core.reset_runbook()


class CreateRunbookRequest(BaseModel):
    name: str
    scope: str = "local"
    phases: list[dict]


@app.post("/api/runbooks")
def create_runbook(req: CreateRunbookRequest):
    safe = re.sub(r'[^a-z0-9-]', '-', req.name.lower().strip())
    safe = re.sub(r'-+', '-', safe).strip('-')
    if not safe:
        raise HTTPException(400, "Invalid runbook name")

    base_dir = core.get_local_dir() if req.scope == "local" else core.get_global_dir()
    rb_dir = base_dir / "runbooks"
    rb_dir.mkdir(parents=True, exist_ok=True)
    rb_file = rb_dir / f"{safe}.md"

    if rb_file.exists():
        raise HTTPException(409, f"Runbook '{safe}' already exists")

    lines = [f"# Runbook: {req.name}", "",
             "Phase | Active Skill | Input | Expected Verified Output",
             "---|---|---|---"]
    for i, p in enumerate(req.phases, 1):
        lines.append(f"{i:02d} | {p.get('skill','')} | {p.get('input','')} | {p.get('output','')}")

    rb_file.write_text("\n".join(lines) + "\n")
    return {"name": safe, "scope": req.scope, "path": str(rb_file)}


@app.delete("/api/runbooks/{name}")
def delete_runbook(name: str):
    rb = core.resolve_runbook(name)
    if not rb:
        raise HTTPException(404, f"Runbook '{name}' not found")
    rb.unlink()
    return {"deleted": True, "name": name}


# ── Helpers ────────────────────────────────────────────────────────────────

def _scope_for_dir(skill_dir: Path) -> str:
    try:
        skill_dir.resolve().relative_to(core.get_local_dir().resolve())
        return "Local"
    except ValueError:
        return "Global"


# ── SPA static serving ─────────────────────────────────────────────────────

static_dir = Path(__file__).parent / "static"
if static_dir.is_dir():
    assets_dir = static_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"detail": f"API endpoint '/{full_path}' not found"},
            )
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(static_dir / "index.html")
