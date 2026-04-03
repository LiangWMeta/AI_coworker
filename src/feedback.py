"""Feedback Collector — work logging + calibration sessions."""

import json
import logging
from datetime import datetime
from pathlib import Path

from . import llm

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent.parent
MEMORY_DIR = ROOT_DIR / "memory"
SCAFFOLD_PATH = Path(__file__).parent / "scaffold.md"
WORK_LOG_PATH = MEMORY_DIR / "work_log.jsonl"
CALIBRATION_DIR = MEMORY_DIR / "calibrations"


def log_work(task: str, result_text: str, success: bool, feedback: str | None = None) -> None:
    """Log a work item to the work log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task,
        "success": success,
        "response_preview": result_text[:500],
        "feedback": feedback,
    }
    with open(WORK_LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_recent_work(n: int = 10) -> list[dict]:
    """Get the N most recent work log entries."""
    if not WORK_LOG_PATH.exists():
        return []

    entries = []
    for line in WORK_LOG_PATH.read_text().strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return entries[-n:]


def run_calibration(reviewer_name: str = "anonymous") -> dict:
    """Run an interactive calibration session.

    Shows recent work and asks 5 quick rating questions.
    Returns calibration result dict.
    """
    recent = get_recent_work(10)

    if not recent:
        print("No work logged yet. Run some tasks first.")
        return {}

    # Show recent work
    print("\n=== Recent Work ===\n")
    for i, entry in enumerate(recent, 1):
        status = "OK" if entry["success"] else "FAIL"
        print(f"{i}. [{status}] {entry['task'][:80]}")
        if entry.get("feedback"):
            print(f"   Feedback: {entry['feedback']}")
    print()

    # Ask calibration questions
    questions = [
        ("impact", "How impactful was the agent's work? (1=no value, 5=high value)"),
        ("judgment", "Did the agent work on the right things and make good decisions? (1=poor, 5=excellent)"),
        ("autonomy", "How independently did the agent work? (1=needed constant guidance, 5=fully autonomous)"),
        ("quality", "How was the quality of the agent's output? (1=poor, 5=excellent)"),
        ("growth", "Compared to before, is the agent improving? (1=no, 3=same, 5=clearly better)"),
    ]

    ratings = {}
    for key, question in questions:
        while True:
            try:
                answer = input(f"{question}: ").strip()
                rating = int(answer)
                if 1 <= rating <= 5:
                    ratings[key] = rating
                    break
                print("Please enter 1-5")
            except (ValueError, EOFError):
                print("Please enter a number 1-5")

    # Free-form feedback
    print()
    strengths = input("What is the agent doing well? (or press Enter to skip): ").strip()
    weaknesses = input("What should the agent improve? (or press Enter to skip): ").strip()

    # Build calibration result
    calibration = {
        "timestamp": datetime.now().isoformat(),
        "reviewer": reviewer_name,
        "ratings": ratings,
        "avg_score": sum(ratings.values()) / len(ratings),
        "strengths": strengths or None,
        "weaknesses": weaknesses or None,
        "work_items_reviewed": len(recent),
    }

    # Save calibration
    CALIBRATION_DIR.mkdir(exist_ok=True)
    cal_file = CALIBRATION_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(cal_file, "w") as f:
        json.dump(calibration, f, indent=2)
    logger.info(f"Calibration saved to {cal_file}")

    return calibration


def update_scaffold_from_calibration(calibration: dict) -> str:
    """Use LLM to update the scaffold based on calibration feedback."""
    scaffold = SCAFFOLD_PATH.read_text()

    feedback_summary = []
    if calibration.get("strengths"):
        feedback_summary.append(f"Strengths: {calibration['strengths']}")
    if calibration.get("weaknesses"):
        feedback_summary.append(f"Areas to improve: {calibration['weaknesses']}")

    ratings = calibration.get("ratings", {})
    for key, val in ratings.items():
        feedback_summary.append(f"{key}: {val}/5")

    if not feedback_summary:
        return scaffold

    feedback_text = "\n".join(feedback_summary)

    updated = llm.understand(
        f"## Current Scaffold\n{scaffold}\n\n## Calibration Feedback\n{feedback_text}",
        """Update the scaffold's "Calibration Notes" section to incorporate this feedback.
Rules:
- Only modify the "## Calibration Notes" section at the bottom
- Keep all other sections exactly as they are
- Add specific, actionable notes based on the feedback
- Reference past calibrations if they exist in the notes
- Output the COMPLETE scaffold document (all sections), not just the changed section""",
    )

    SCAFFOLD_PATH.write_text(updated)
    logger.info("Scaffold updated with calibration feedback")
    return updated
