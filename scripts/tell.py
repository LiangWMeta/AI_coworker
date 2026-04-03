#!/usr/bin/env python3
"""Talk to the AI coworker daemon — send messages and read notifications."""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.daemon import send_message, get_notifications

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PID_FILE = MEMORY_DIR / "daemon.pid"


def is_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        os.kill(int(PID_FILE.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tell.py 'your message'     — send a message to the agent")
        print("  python tell.py --read              — read recent notifications")
        print("  python tell.py --read N            — read last N notifications")
        print("  python tell.py --log               — show activity log")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--read":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        notifications = get_notifications(n)
        if not notifications:
            print("No notifications yet.")
            return
        for entry in notifications:
            ts = entry.get("timestamp", "?")[:19]
            pri = entry.get("priority", "info")
            msg = entry.get("message", "")
            marker = {"urgent": "!!!", "important": "!!", "info": " "}[pri]
            print(f"[{ts}] {marker} {msg}")
        return

    if arg == "--log":
        log_path = MEMORY_DIR / "activity.log"
        if not log_path.exists():
            print("No activity log yet.")
            return
        lines = log_path.read_text().strip().splitlines()
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        for line in lines[-n:]:
            print(line)
        return

    # Send a message
    if not is_running():
        print("Warning: AI coworker daemon is not running. Message saved to inbox.")
        print("Start with: python scripts/start.py <repo_path>")

    message = " ".join(sys.argv[1:])
    send_message(message)
    print(f"Message sent: {message}")
    print("Check for response: python scripts/tell.py --read")


if __name__ == "__main__":
    main()
