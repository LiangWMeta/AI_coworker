#!/usr/bin/env python3
"""Internal entry point for the daemon process. Don't call directly — use start.py."""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.daemon import run_daemon

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

if __name__ == "__main__":
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    owner = sys.argv[2] if len(sys.argv) > 2 else "liangwang"
    gchat_space = sys.argv[3] if len(sys.argv) > 3 else "AAQAF8E6ba8"
    run_daemon(repo_path, owner=owner, gchat_space=gchat_space)
