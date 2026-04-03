"""Main AI coworker agent — picks up tasks, executes work, captures results."""

import json
import logging
from datetime import datetime
from pathlib import Path

from . import llm

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
MEMORY_DIR = ROOT_DIR / "memory"


def load_self_memory() -> str:
    """Load the agent's self-memory (soul, mission, motivation, level, etc.)."""
    self_dir = MEMORY_DIR / "self"
    if not self_dir.exists():
        return ""

    # Load in a specific order for coherence
    order = ["soul", "mission", "motivation", "level", "principles", "rules", "lessons"]
    parts = []
    for name in order:
        f = self_dir / f"{name}.md"
        if f.exists():
            content = f.read_text().strip()
            if content and "(No lessons yet" not in content and "(To be updated" not in content:
                parts.append(content)

    return "\n\n---\n\n".join(parts)


def load_people_memory() -> str:
    """Load memory about people the agent works with."""
    people_dir = MEMORY_DIR / "people"
    if not people_dir.exists():
        return ""

    parts = []
    for f in sorted(people_dir.glob("*.md")):
        content = f.read_text().strip()
        if content:
            parts.append(content)

    return "\n\n---\n\n".join(parts)


def load_work_memory() -> str:
    """Load current work context."""
    work_dir = MEMORY_DIR / "work"
    if not work_dir.exists():
        return ""

    parts = []
    for f in sorted(work_dir.glob("*.md")):
        content = f.read_text().strip()
        if content:
            parts.append(content)

    return "\n\n---\n\n".join(parts)


def load_system_prompt() -> str:
    """Build the full system prompt from self-memory."""
    self_mem = load_self_memory()
    if not self_mem:
        return "You are an AI coworker."
    return self_mem


def load_context() -> str:
    """Load people + work memory as context."""
    parts = []

    people = load_people_memory()
    if people:
        parts.append(f"# People I Work With\n\n{people}")

    work = load_work_memory()
    if work:
        parts.append(f"# Current Work\n\n{work}")

    return "\n\n===\n\n".join(parts) if parts else "(No context yet)"


def load_recent_chat(n: int = 10) -> str:
    """Load recent GChat conversation history for continuity."""
    chat_log = MEMORY_DIR / "chat_history.jsonl"
    if not chat_log.exists():
        return ""

    entries = []
    for line in chat_log.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not entries:
        return ""

    recent = entries[-n:]
    lines = []
    for e in recent:
        role = e.get("role", "user")
        text = e.get("text", "")[:500]
        lines.append(f"[{role}]: {text}")

    return "# Recent Conversation\n" + "\n".join(lines)


def save_chat_turn(role: str, text: str) -> None:
    """Save a conversation turn to chat history."""
    chat_log = MEMORY_DIR / "chat_history.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "text": text[:1000],
    }
    with open(chat_log, "a") as f:
        f.write(json.dumps(entry) + "\n")


def execute_task(
    task: str,
    model: str = "sonnet",
    allowed_tools: str | None = None,
) -> llm.LLMResult:
    """Execute a single task with self-memory as system prompt and context injected."""
    system_prompt = load_system_prompt()
    context = load_context()
    chat_history = load_recent_chat()

    context_block = context
    if chat_history:
        context_block = f"{context}\n\n===\n\n{chat_history}"

    prompt = f"""## Context
{context_block}

## Message
{task}"""

    logger.info(f"Executing task: {task[:100]}...")

    # Save user turn
    save_chat_turn("user", task)

    result = llm.run(
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        allowed_tools=allowed_tools,
    )

    # Save agent turn
    if result.success:
        save_chat_turn("agent", result.text)

    if result.success:
        logger.info("Task completed successfully")
    else:
        logger.error(f"Task failed: {result.error}")

    return result


def log_work(task: str, result: llm.LLMResult) -> None:
    """Append work to the work log."""
    log_path = MEMORY_DIR / "work_log.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "success": result.success,
        "response_length": len(result.text),
        "error": result.error,
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
