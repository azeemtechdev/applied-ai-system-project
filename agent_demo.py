#!/usr/bin/env python3
"""CLI demo of the PawPal+ agentic Plan-Act-Check loop.

Runs the agent on a sample natural-language request and prints the full
reasoning trace, the self-check verdict, and the final schedule. Works with
or without a GEMINI_API_KEY (falls back to a deterministic parser).

Usage:
    python agent_demo.py
    python agent_demo.py "I have 3 hours; dog needs a walk, two feeds and meds"
"""

import sys

from config import get_settings
from agent import PawPalAgent
from pawpal_system import Owner, Pet

SAMPLE_TEXT = (
    "I have about 5 hours today. My dog Biscuit needs a 30-minute morning walk, "
    "two feedings, and his medication. My cat also needs grooming and some playtime."
)


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else SAMPLE_TEXT
    available_minutes = 300

    settings = get_settings()
    print("=" * 70)
    print("PawPal+ Agentic Planner (Plan -> Act -> Check)")
    print("=" * 70)
    print(f"Model: {settings.model}   |   API key configured: {settings.has_api_key}")
    print(f"Available time: {available_minutes} minutes")
    print(f"\nOwner says:\n  \"{text}\"\n")

    owner = Owner(name="Jordan", available_time_minutes=available_minutes)
    pet = Pet(name="Biscuit", species="dog", breed="Golden Retriever", age=3)

    agent = PawPalAgent(settings=settings)
    result = agent.run(text, pet=pet, owner=owner, available_minutes=available_minutes)

    print("-" * 70)
    print("REASONING TRACE")
    print("-" * 70)
    for step in result.trace:
        print(f"  [iter {step.iteration}] {step.phase:<6} | {step.detail}")

    print()
    print("-" * 70)
    print(f"SELF-CHECK VERDICT: {'ACCEPTABLE' if result.critique.get('ok') else 'NEEDS REVISION'}")
    print("-" * 70)
    if result.critique.get("issues"):
        for issue in result.critique["issues"]:
            print(f"  - issue: {issue}")
    if result.critique.get("suggested_fixes"):
        for fix in result.critique["suggested_fixes"]:
            print(f"  - fix:   {fix}")

    print()
    print("-" * 70)
    print("FINAL SCHEDULE")
    print("-" * 70)
    if result.day_plan:
        print(result.day_plan.explain_plan())

    print()
    print(
        f"[iterations={result.iterations} | used_fallback={result.used_fallback}] "
        "See logs/pawpal.log for the full audit trail."
    )


if __name__ == "__main__":
    main()
