"""Context Engine — ingest sources, understand with LLM, maintain structured memory."""

import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime

from . import llm

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
MEMORY_DIR = ROOT_DIR / "memory"


def run_cmd(cmd: str, timeout: int = 30) -> str:
    """Run a shell command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, Exception) as e:
        logger.warning(f"Command failed: {cmd}: {e}")
        return ""


# --- Ingestion functions ---

def ingest_repo(repo_path: str) -> str:
    """Ingest context from a code repository. Returns raw context string."""
    parts = []

    # Recent commits (last 10)
    log = run_cmd(f"cd {repo_path} && (sl log -l 10 --template '{{desc|firstline}}\\n' 2>/dev/null || git log --oneline -10 2>/dev/null)")
    if log:
        parts.append(f"## Recent Commits\n{log}")

    # Current status
    status = run_cmd(f"cd {repo_path} && (sl status 2>/dev/null || git status --short 2>/dev/null)")
    if status:
        parts.append(f"## Working Copy Status\n{status}")

    # Directory structure (top 2 levels)
    tree = run_cmd(f"find {repo_path} -maxdepth 2 -type f -not -path '*/.git/*' -not -path '*/.sl/*' -not -path '*/__pycache__/*' -not -path '*/node_modules/*' | head -50")
    if tree:
        parts.append(f"## File Structure\n{tree}")

    # README if it exists
    for readme in ["README.md", "README", "README.rst"]:
        readme_path = Path(repo_path) / readme
        if readme_path.exists():
            content = readme_path.read_text()[:2000]
            parts.append(f"## README\n{content}")
            break

    # CLAUDE.md if it exists
    claude_md = Path(repo_path) / "CLAUDE.md"
    if claude_md.exists():
        content = claude_md.read_text()[:2000]
        parts.append(f"## CLAUDE.md\n{content}")

    return "\n\n".join(parts) if parts else "(No repo context found)"


def ingest_tasks(project_id: str | None = None) -> str:
    """Ingest tasks from GSD/task board via meta CLI. Returns raw context string."""
    cmd = "meta tasks.task list -o json -l 20 --show-links"
    if project_id:
        cmd += f" --project-id {project_id}"

    raw = run_cmd(cmd, timeout=60)
    if not raw:
        return "(No tasks found or meta CLI unavailable)"

    try:
        data = json.loads(raw)
        # Handle both list and dict responses from meta CLI
        tasks_list = data if isinstance(data, list) else data.get("data", data.get("tasks", []))
        if not isinstance(tasks_list, list):
            return f"## Tasks (raw)\n{raw[:2000]}"
        lines = []
        for t in tasks_list[:20]:
            if not isinstance(t, dict):
                continue
            title = t.get("title", t.get("name", "untitled"))
            status = t.get("status", "unknown")
            assignee = t.get("assignee", {}).get("name", "unassigned") if isinstance(t.get("assignee"), dict) else "unassigned"
            lines.append(f"- [{status}] {title} (assigned: {assignee})")
        return "## Tasks\n" + "\n".join(lines) if lines else f"## Tasks (raw)\n{raw[:2000]}"
    except (json.JSONDecodeError, TypeError):
        return f"## Tasks (raw)\n{raw[:2000]}"


def ingest_diffs(username: str | None = None) -> str:
    """Ingest recent diffs from Phabricator via meta CLI."""
    cmd = "meta phabricator.diff list -o json -l 10 --show-links"
    if username:
        cmd += f" --author {username}"

    raw = run_cmd(cmd, timeout=60)
    if not raw:
        return "(No diffs found or meta CLI unavailable)"

    try:
        data = json.loads(raw)
        diffs_list = data if isinstance(data, list) else data.get("data", data.get("diffs", []))
        if not isinstance(diffs_list, list):
            return f"## Recent Diffs (raw)\n{raw[:2000]}"
        lines = []
        for d in diffs_list[:10]:
            if not isinstance(d, dict):
                continue
            diff_id = d.get("id", "?")
            title = d.get("title", "untitled")
            status = d.get("status", "unknown")
            lines.append(f"- D{diff_id} [{status}] {title}")
        return "## Recent Diffs\n" + "\n".join(lines) if lines else f"## Recent Diffs (raw)\n{raw[:2000]}"
    except (json.JSONDecodeError, TypeError):
        return f"## Recent Diffs (raw)\n{raw[:2000]}"


# --- Understanding + Memory ---

def understand_and_save(raw_context: str, memory_file: str, instruction: str) -> str:
    """Use LLM to understand raw context and save structured memory.

    Args:
        raw_context: Raw ingested data.
        memory_file: Filename in memory/ to write to (e.g., "team.md").
        instruction: What the LLM should extract/understand.

    Returns:
        The structured understanding.
    """
    understanding = llm.understand(raw_context, instruction)

    memory_path = MEMORY_DIR / memory_file
    memory_path.write_text(understanding)
    logger.info(f"Saved understanding to {memory_path}")

    return understanding


def update_memory(memory_file: str, new_info: str) -> str:
    """Update an existing memory file with new information using LLM restructuring."""
    memory_path = MEMORY_DIR / memory_file
    current = memory_path.read_text() if memory_path.exists() else ""

    updated = llm.restructure_memory(current, new_info)

    memory_path.write_text(updated)
    logger.info(f"Updated memory: {memory_path}")

    return updated


def onboard(repo_path: str, project_id: str | None = None, username: str | None = None) -> dict:
    """Full onboarding: ingest all sources, understand, build initial memory.

    Returns dict of memory files created.
    """
    logger.info(f"Starting onboarding for repo: {repo_path}")
    results = {}

    # 1. Ingest repo context
    logger.info("Ingesting repo context...")
    repo_context = ingest_repo(repo_path)

    results["work/context.md"] = understand_and_save(
        repo_context,
        "work/context.md",
        """Analyze this repository context and produce a structured summary:
- What is this project/repo about?
- What is the team working on (based on recent commits)?
- What is the current state of the codebase?
- Key technologies and patterns used
Keep it concise — bullet points, not prose.""",
    )

    # 2. Ingest tasks if available
    logger.info("Ingesting tasks...")
    task_context = ingest_tasks(project_id)

    # 3. Ingest diffs if available
    logger.info("Ingesting diffs...")
    diff_context = ingest_diffs(username)

    # Combine tasks + diffs into current work understanding
    work_context = f"{task_context}\n\n{diff_context}"
    results["work/focus.md"] = understand_and_save(
        work_context,
        "work/focus.md",
        """Analyze these tasks and diffs to understand current work:
- What are the active priorities?
- What's in progress vs. blocked vs. done?
- Any patterns in the work (e.g., focused on one area)?
Keep it concise — bullet points, not prose.""",
    )

    # 4. Lessons file is in self/lessons.md — skip if already exists

    logger.info("Onboarding complete!")
    return results
