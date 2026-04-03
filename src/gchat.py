"""GChat integration — send messages to and read messages from Google Chat."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _escape_html(text: str) -> str:
    """Escape text for use in GHTML card content, preserving GChat formatting."""
    # Escape HTML entities
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert newlines to <br> for card display
    text = text.replace("\n", "<br/>")
    return text


def _run(cmd: str, timeout: int = 30) -> str:
    """Run a gchat command and return stdout. Filters timing lines from output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        # gchat outputs timing lines like "[0.5s] GET ..." before JSON
        # Filter to only the JSON line
        lines = result.stdout.strip().splitlines()
        json_lines = [l for l in lines if l.startswith("{") or l.startswith("[")]
        return json_lines[-1] if json_lines else result.stdout.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"gchat command timed out: {cmd[:80]}")
        return ""
    except Exception as e:
        logger.warning(f"gchat command failed: {e}")
        return ""


# --- Sending Messages ---

def send_to(target: str, message: str) -> bool:
    """Send a message to a GChat space as Meta Bot. Returns True on success."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(message)
        tmp_path = f.name

    try:
        raw = _run(f"gchat send {target} --text-file {tmp_path} --as-bot --json", timeout=30)
        if raw:
            try:
                data = json.loads(raw)
                if data.get("success"):
                    logger.info(f"Sent GChat message to {target}")
                    return True
            except json.JSONDecodeError:
                pass
        logger.error(f"Failed to send GChat message to {target}: {raw[:200]}")
        return False
    finally:
        Path(tmp_path).unlink(missing_ok=True)


# --- Reading Messages ---

def read_messages(target: str, count: int = 20, since: str | None = None) -> list[dict]:
    """Read messages from a space or DM."""
    cmd = f"gchat read {target} -c {count} --json"
    if since:
        cmd += f" --since {since}"

    raw = _run(cmd, timeout=60)
    if not raw:
        return []

    try:
        data = json.loads(raw)
        # Unwrap nested: {"data":{"data":[...]}} or {"data":{"data":{"messages":[...]}}}
        inner = data
        while isinstance(inner, dict) and "data" in inner:
            inner = inner["data"]
        if isinstance(inner, list):
            return inner
        if isinstance(inner, dict) and "messages" in inner:
            return inner["messages"]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def read_unread() -> list[dict]:
    """Get conversations with unread messages."""
    raw = _run("gchat unread --json", timeout=60)
    if not raw:
        return []

    try:
        data = json.loads(raw)
        inner = data
        while isinstance(inner, dict) and "data" in inner:
            inner = inner["data"]
        if isinstance(inner, dict) and "spaces" in inner:
            return inner["spaces"]
        if isinstance(inner, list):
            return inner
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def get_recent_chat_context(username: str, hours: int = 4) -> str:
    """Get recent GChat activity for context building.

    Reads the user's recent conversations to understand what they're working on.
    Returns raw text for LLM understanding.
    """
    parts = []

    # Read recent messages from the user's most active DMs
    since = f"{hours}h" if hours < 48 else f"{hours // 24}d"

    # Read messages from the user's own DM space (self-chat, if any)
    # and their recent conversations
    messages = read_messages(username, count=30, since=since)
    if messages:
        msg_texts = []
        for msg in messages[:30]:
            sender = "unknown"
            if isinstance(msg.get("sender"), dict):
                sender = msg["sender"].get("displayName", "unknown")
            text = msg.get("text", "")[:300]
            if text:
                msg_texts.append(f"  {sender}: {text}")
        if msg_texts:
            parts.append(f"## Recent Messages\n" + "\n".join(msg_texts))

    # Check unread conversations
    unread = read_unread()
    if unread:
        unread_names = []
        for space in unread[:10]:
            if isinstance(space, dict):
                name = space.get("displayName", space.get("name", "unknown"))
                unread_names.append(f"- Unread: {name}")
        if unread_names:
            parts.append("## Unread Conversations\n" + "\n".join(unread_names))

    return "\n\n".join(parts) if parts else "(No recent chat activity)"
