#!/usr/bin/env python3
"""Run a calibration session for the AI coworker agent."""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.feedback import run_calibration, update_scaffold_from_calibration

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    reviewer = sys.argv[1] if len(sys.argv) > 1 else "anonymous"

    print("=" * 60)
    print("AI Coworker Calibration Session")
    print(f"Reviewer: {reviewer}")
    print("=" * 60)

    calibration = run_calibration(reviewer_name=reviewer)

    if not calibration:
        return

    print("\n" + "=" * 60)
    print("Calibration Summary:")
    print(f"  Average score: {calibration['avg_score']:.1f}/5")
    for key, val in calibration["ratings"].items():
        print(f"  {key}: {val}/5")

    # Ask if we should update the scaffold
    update = input("\nUpdate agent scaffold with this feedback? (y/n): ").strip().lower()
    if update == "y":
        print("Updating scaffold...")
        update_scaffold_from_calibration(calibration)
        print("Scaffold updated! The agent will incorporate this feedback in future work.")
    else:
        print("Scaffold not updated. Calibration saved for reference.")


if __name__ == "__main__":
    main()
