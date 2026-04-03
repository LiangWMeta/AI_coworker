"""Persistent AI coworker daemon — always running, listens, acts, notifies via GChat."""

import json
import os
import time
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path

from . import llm
from . import gchat
from .context import run_cmd, ingest_repo, ingest_diffs, ingest_tasks, update_memory
from .agent import execute_task, load_system_prompt, load_context, log_work

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
MEMORY_DIR = ROOT_DIR / "memory"
STATE_FILE = MEMORY_DIR / "daemon_state.json"
ACTIVITY_LOG = MEMORY_DIR / "activity.log"
OUTBOX = MEMORY_DIR / "outbox.jsonl"     # Local fallback
INBOX = MEMORY_DIR / "inbox.jsonl"       # Local fallback

# Polling intervals (seconds)
POLL_CODE = 60
POLL_TASKS = 300
POLL_INBOX = 5
POLL_GCHAT_INBOX = 3     # Check GChat space for user messages every 3 seconds
POLL_GCHAT_CONTEXT = 120 # Read broader GChat for context every 2 minutes
POLL_CONTEXT_REFRESH = 600

_running = True
_owner_username = None   # Set during daemon start
_gchat_space = None      # GChat space ID for notifications


# --- Communication (GChat-first, file-fallback) ---

def notify(message: str, priority: str = "info") -> None:
    """Send notification — via GChat, splitting long messages into chunks."""
    log_activity("NOTIFY", f"[{priority}] {message[:100]}")

    if _gchat_space:
        prefix = ""
        if priority == "urgent":
            prefix = "*URGENT*: "
        elif priority == "important":
            prefix = "*Note*: "

        full_msg = prefix + message
        # Split into chunks of ~4000 chars (GChat limit is ~4096)
        CHUNK_SIZE = 4000
        chunks = []
        while full_msg:
            if len(full_msg) <= CHUNK_SIZE:
                chunks.append(full_msg)
                break
            # Find a good break point (newline or space)
            cut = full_msg.rfind("\n", 0, CHUNK_SIZE)
            if cut < CHUNK_SIZE // 2:
                cut = full_msg.rfind(" ", 0, CHUNK_SIZE)
            if cut < CHUNK_SIZE // 2:
                cut = CHUNK_SIZE
            chunks.append(full_msg[:cut])
            full_msg = full_msg[cut:].lstrip()

        all_sent = True
        for chunk in chunks:
            if not gchat.send_to(_gchat_space, chunk):
                all_sent = False
                break
        if all_sent:
            return

    # Fallback to file outbox
    entry = {
        "timestamp": datetime.now().isoformat(),
        "priority": priority,
        "message": message,
    }
    with open(OUTBOX, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_inbox() -> list[dict]:
    """Check for new messages — file-based inbox."""
    if not INBOX.exists():
        return []

    messages = []
    remaining = []
    for line in INBOX.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            if not msg.get("read"):
                msg["read"] = True
                messages.append(msg)
            remaining.append(json.dumps(msg))
        except json.JSONDecodeError:
            continue

    INBOX.write_text("\n".join(remaining) + "\n" if remaining else "")
    return messages


def send_message(text: str) -> None:
    """Send a message to the agent (called by user via CLI)."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "message": text,
        "read": False,
    }
    with open(INBOX, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_notifications(n: int = 10, unread_only: bool = False) -> list[dict]:
    """Read recent notifications from outbox file."""
    if not OUTBOX.exists():
        return []

    entries = []
    for line in OUTBOX.read_text().strip().splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries[-n:]


# --- Activity Logging ---

def log_activity(event_type: str, summary: str, details: str = "") -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] [{event_type}] {summary}"
    if details:
        detail_lines = details.strip().splitlines()
        entry += "\n" + "\n".join(f"  {line}" for line in detail_lines[:10])
    with open(ACTIVITY_LOG, "a") as f:
        f.write(entry + "\n")


# --- State Management ---

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# --- GChat Inbox (read user messages from the AI Coworker space) ---

# Prefixes/phrases the agent uses — skip these when reading the space
_AGENT_PHRASES = [
    "AI coworker is online",
    "AI coworker going offline",
    "Re: ",
    "*URGENT*:",
    "*Note*:",
    "Sorry, I hit an error:",
    "Completed:",
    "Proactively completed:",
]


def is_agent_message(body: str) -> bool:
    """Check if a message was likely sent by the agent (not the user)."""
    for phrase in _AGENT_PHRASES:
        if body.startswith(phrase):
            return True
    return False


def check_gchat_inbox(state: dict) -> list[dict]:
    """Check the AI Coworker GChat space for new user messages.

    Returns list of user messages that need responses.
    """
    if not _gchat_space:
        return []

    messages = gchat.read_messages(_gchat_space, count=5, since="1h")
    if not messages:
        return []

    last_seen_ts = state.get("last_gchat_msg_ts", 0)
    new_messages = []

    for msg in messages:
        ts = msg.get("creation_timestamp", 0)
        body = msg.get("message_body", "").strip()

        if not body or ts <= last_seen_ts:
            continue

        # Skip agent's own messages (sent as bot or matching known phrases)
        sender = msg.get("sender_name", "")
        if sender in ("Meta Bot", "LLM Coworker") or is_agent_message(body):
            continue

        new_messages.append({
            "timestamp": ts,
            "body": body,
            "sender": msg.get("sender_name", "unknown"),
            "thread": msg.get("google_thread_name", ""),
        })

    # Update last seen timestamp
    if new_messages:
        state["last_gchat_msg_ts"] = max(m["timestamp"] for m in new_messages)

    return new_messages


# --- Event Detection ---

def detect_code_changes(repo_path: str, state: dict) -> list[dict]:
    events = []

    status = run_cmd(f"cd {repo_path} && (sl status 2>/dev/null || git status --short 2>/dev/null)")
    status_hash = hash(status)
    if status and status_hash != state.get("last_status_hash"):
        state["last_status_hash"] = status_hash
        events.append({"type": "code_change", "summary": "Working copy changed", "data": status})

    recent_log = run_cmd(
        f"cd {repo_path} && (sl log -l 3 --template '{{node|short}} {{desc|firstline}}\\n' 2>/dev/null "
        f"|| git log --oneline -3 2>/dev/null)"
    )
    log_hash = hash(recent_log)
    if recent_log and log_hash != state.get("last_log_hash"):
        state["last_log_hash"] = log_hash
        events.append({"type": "new_commits", "summary": "New commits detected", "data": recent_log})

    return events


def detect_task_changes(state: dict) -> list[dict]:
    events = []
    raw = run_cmd("meta tasks.task list --owner=$(whoami) --is-open -o json -l 20", timeout=60)
    if not raw:
        return events

    try:
        data = json.loads(raw)
        tasks_list = data if isinstance(data, list) else data.get("data", [])
        if isinstance(tasks_list, list) and tasks_list:
            task_hash = hash(json.dumps(tasks_list, sort_keys=True))
            if task_hash != state.get("last_task_hash"):
                state["last_task_hash"] = task_hash
                events.append({
                    "type": "task_update",
                    "summary": f"Task board updated ({len(tasks_list)} open tasks)",
                    "data": raw[:2000],
                })
    except (json.JSONDecodeError, TypeError):
        pass

    return events


def ingest_gchat_context(state: dict) -> list[dict]:
    """Read recent GChat activity and update context memory.

    Returns events if significant chat activity detected.
    """
    events = []

    # Get recent chat context
    chat_context = gchat.get_recent_chat_context(_owner_username or "liangwang", hours=4)

    if not chat_context or chat_context == "(No recent chat activity)":
        return events

    chat_hash = hash(chat_context)
    if chat_hash == state.get("last_chat_hash"):
        return events

    state["last_chat_hash"] = chat_hash

    # Use LLM to understand what the user is discussing and update memory
    understanding = llm.understand(
        chat_context,
        """Analyze these recent GChat conversations and extract:
- What topics/projects is the user actively discussing?
- Any action items or requests directed at the user?
- Any urgent issues or blockers mentioned?
- Key decisions being made?

Be concise — bullet points only. Skip small talk and trivial messages.""",
        model="haiku",
    )

    if understanding and "[Error:" not in understanding:
        # Update the current_work memory with chat insights
        update_memory("work/focus.md", f"## Recent Chat Activity\n{understanding}")
        events.append({
            "type": "chat_update",
            "summary": "New chat context ingested",
            "data": understanding[:500],
        })
        log_activity("GCHAT", "Ingested chat context", understanding[:300])

    return events


# --- Decision Engine ---

def decide_action(events: list[dict]) -> dict | None:
    if not events:
        return None

    event_summary = "\n".join(
        f"- [{e['type']}] {e['summary']}: {e['data'][:300]}" for e in events
    )

    context = load_context()

    prompt = f"""## Your Current Context
{context}

## Recent Events Detected
{event_summary}

## Decision Required
Should you take proactive action or notify the user?

Options:
1. ACT: Do something useful (investigate, fix, prepare)
2. NOTIFY: Tell the user about something important they should know
3. SKIP: Nothing worth acting on

Rules:
- Only ACT on things that are genuinely useful and within your permissions
- NOTIFY for important events the user should know about (failures, blockers, urgent items)
- SKIP trivial changes (minor edits, routine updates)
- You can send notifications via GChat DM — the user will see them on their phone

Respond with EXACTLY one of:
ACT: <what you'll do>
NOTIFY: <message for the user>
SKIP: <reason>"""

    result = llm.run(prompt, system_prompt=load_system_prompt(), model="haiku")

    if not result.success:
        return None

    text = result.text.strip()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("ACT:"):
            return {"action": "work", "task": line[4:].strip(), "triggered_by": events}
        elif line.startswith("NOTIFY:"):
            return {"action": "notify", "message": line[7:].strip(), "triggered_by": events}

    return None


# --- Main Daemon Loop ---

def run_daemon(repo_path: str, owner: str = "liangwang", gchat_space: str = "AAQAF8E6ba8") -> None:
    """Main daemon loop — runs forever, watches, acts, notifies via GChat."""
    global _running, _owner_username, _gchat_space
    _owner_username = owner
    _gchat_space = gchat_space

    def handle_signal(signum, frame):
        global _running
        _running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    state = load_state()
    # Set last seen timestamp to now so we don't respond to old messages
    state["last_gchat_msg_ts"] = int(time.time())
    save_state(state)
    log_activity("DAEMON", f"Started — watching {repo_path}, notifying {owner} via GChat space")
    notify("Hey! I'm online and ready. Talk to me here anytime — I'll respond.", "info")

    timers = {"code": 0, "tasks": 0, "inbox": 0, "context": 0, "gchat_context": 0, "gchat_inbox": 0}

    while _running:
        try:
            now = time.time()

            # --- Check GChat space for user messages (highest priority) ---
            if now - timers["gchat_inbox"] >= POLL_GCHAT_INBOX:
                timers["gchat_inbox"] = now
                gchat_messages = check_gchat_inbox(state)
                for msg in gchat_messages:
                    user_text = msg["body"]
                    log_activity("GCHAT_MSG", f"User says: {user_text[:100]}")

                    result = execute_task(user_text)
                    log_work(user_text, result)

                    if result.success:
                        notify(result.text, "info")
                    else:
                        notify(f"Sorry, I hit an error: {result.error}", "important")

            # --- Check file inbox (fallback) ---
            if now - timers["inbox"] >= POLL_INBOX:
                timers["inbox"] = now
                messages = check_inbox()
                for msg in messages:
                    user_text = msg["message"]
                    log_activity("INBOX", f"User message: {user_text[:100]}")

                    result = execute_task(user_text)
                    log_work(user_text, result)

                    if result.success:
                        notify(f"Re: {user_text[:50]}...\n{result.text}", "info")
                    else:
                        notify(f"Failed on: {user_text[:50]}... Error: {result.error}", "important")

            # --- Detect events ---
            events = []

            if now - timers["code"] >= POLL_CODE:
                timers["code"] = now
                events.extend(detect_code_changes(repo_path, state))

            if now - timers["tasks"] >= POLL_TASKS:
                timers["tasks"] = now
                events.extend(detect_task_changes(state))

            # --- Ingest GChat for context ---
            if now - timers["gchat_context"] >= POLL_GCHAT_CONTEXT:
                timers["gchat_context"] = now
                events.extend(ingest_gchat_context(state))

            # --- Decide and act ---
            if events:
                for e in events:
                    log_activity("DETECT", e["summary"])

                decision = decide_action(events)

                if decision:
                    if decision["action"] == "work":
                        task = decision["task"]
                        log_activity("ACTION", task)
                        result = execute_task(task)
                        log_work(task, result)

                        if result.success:
                            notify(f"Completed: {task}\n{result.text}", "info")
                        else:
                            log_activity("ERROR", f"Failed: {task}", result.error or "")

                    elif decision["action"] == "notify":
                        notify(decision["message"], "important")

            # --- Periodic context refresh ---
            if now - timers["context"] >= POLL_CONTEXT_REFRESH:
                timers["context"] = now
                repo_context = ingest_repo(repo_path)
                update_memory("work/context.md", repo_context)
                log_activity("REFRESH", "Context refreshed")

            save_state(state)
            time.sleep(5)

        except Exception as e:
            logger.error(f"Daemon error: {e}")
            log_activity("ERROR", str(e))
            time.sleep(30)

    log_activity("DAEMON", "Stopped")
    notify("AI coworker going offline.", "info")
    save_state(state)
