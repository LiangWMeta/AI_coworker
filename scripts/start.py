#!/usr/bin/env python3
"""Start the AI coworker daemon in the background."""

import sys
import os
import subprocess
import logging
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

MEMORY_DIR = Path(__file__).parent.parent / "memory"
PID_FILE = MEMORY_DIR / "daemon.pid"
ACTIVITY_LOG = MEMORY_DIR / "activity.log"


def is_running() -> bool:
    """Check if daemon is already running."""
    if not PID_FILE.exists():
        return False
    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 0)  # Check if process exists
        return True
    except OSError:
        PID_FILE.unlink(missing_ok=True)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python start.py <repo_path>")
        print("       python start.py status")
        print("       python start.py stop")
        sys.exit(1)

    action = sys.argv[1]

    if action == "status":
        if is_running():
            pid = PID_FILE.read_text().strip()
            print(f"AI coworker is running (PID {pid})")
            # Show last few activity entries
            if ACTIVITY_LOG.exists():
                lines = ACTIVITY_LOG.read_text().strip().splitlines()
                print("\nRecent activity:")
                for line in lines[-5:]:
                    print(f"  {line}")
        else:
            print("AI coworker is not running")
        return

    if action == "stop":
        if not is_running():
            print("AI coworker is not running")
            return
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 15)  # SIGTERM
        PID_FILE.unlink(missing_ok=True)
        print(f"AI coworker stopped (was PID {pid})")
        return

    # Start the daemon
    repo_path = action
    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory")
        sys.exit(1)

    if is_running():
        pid = PID_FILE.read_text().strip()
        print(f"AI coworker is already running (PID {pid})")
        return

    # Parse optional args
    owner = "liangwang"
    gchat_space = "AAQAF8E6ba8"  # "AI Coworker" space
    for i, a in enumerate(sys.argv):
        if a == "--owner" and i + 1 < len(sys.argv):
            owner = sys.argv[i + 1]
        elif a == "--gchat-space" and i + 1 < len(sys.argv):
            gchat_space = sys.argv[i + 1]

    # Run the daemon in background
    daemon_script = os.path.join(os.path.dirname(__file__), "_daemon_entry.py")
    proc = subprocess.Popen(
        [sys.executable, daemon_script, repo_path, owner, gchat_space],
        stdout=open(MEMORY_DIR / "daemon.stdout.log", "a"),
        stderr=open(MEMORY_DIR / "daemon.stderr.log", "a"),
        start_new_session=True,  # Detach from terminal
    )

    PID_FILE.write_text(str(proc.pid))
    print(f"AI coworker started (PID {proc.pid})")
    print(f"  Watching: {repo_path}")
    print(f"  Notifying: {owner} via GChat DM")
    print(f"  Reading: {owner}'s recent GChat for context")
    print(f"  Activity log: {ACTIVITY_LOG}")
    print(f"  Talk to it: python scripts/tell.py 'your message'")
    print(f"  Read updates: python scripts/tell.py --read")
    print(f"  Stop: python scripts/start.py stop")


if __name__ == "__main__":
    main()
