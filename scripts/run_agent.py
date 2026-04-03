#!/usr/bin/env python3
"""Run the AI coworker agent on a single task."""

import sys
import os
import logging

# Add parent dir to path so we can import src as a package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src import llm
from src.agent import execute_task, log_work

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py 'your task description'")
        print("Example: python run_agent.py 'analyze the project structure and suggest improvements'")
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    print(f"Task: {task}\n")
    print("=" * 60)

    result = execute_task(task)

    if result.success:
        print(result.text)
    else:
        print(f"ERROR: {result.error}")
        if result.text:
            print(f"Output: {result.text}")

    log_work(task, result)
    print("\n" + "=" * 60)
    print(f"[Work logged. Success: {result.success}]")


if __name__ == "__main__":
    main()
