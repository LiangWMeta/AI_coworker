#!/usr/bin/env python3
"""Onboard the AI coworker agent to a repository."""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.context import onboard

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    if len(sys.argv) < 2:
        print("Usage: python onboard.py <repo_path> [--project-id ID] [--username NAME]")
        print("Example: python onboard.py ~/fbsource/fbcode/my_project")
        sys.exit(1)

    repo_path = sys.argv[1]

    # Parse optional args
    project_id = None
    username = None
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--project-id" and i + 1 < len(sys.argv):
            project_id = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--username" and i + 1 < len(sys.argv):
            username = sys.argv[i + 1]
            i += 2
        else:
            i += 1

    if not os.path.isdir(repo_path):
        print(f"Error: {repo_path} is not a directory")
        sys.exit(1)

    print(f"Onboarding from: {repo_path}")
    if project_id:
        print(f"Project ID: {project_id}")
    if username:
        print(f"Username: {username}")
    print("=" * 60)

    results = onboard(repo_path, project_id=project_id, username=username)

    print("\n" + "=" * 60)
    print("Onboarding complete! Memory files created:")
    for filename, content in results.items():
        print(f"  - memory/{filename} ({len(content)} chars)")
    print("\nThe agent now has context. Run: python scripts/run_agent.py 'your task'")


if __name__ == "__main__":
    main()
