#!/usr/bin/env python3
"""
NarrativeCare AI — Test Script
Run this to test the pipeline without needing curl or a browser.

Usage:
  python test.py                    # test with default input
  python test.py "your situation"   # test with custom input
  python test.py --all              # test all 5 inputs
  python test.py --quality          # run quality checks on output
"""

import sys
import json
import time
import requests

BASE_URL = "http://localhost:8000"

TEST_INPUTS = [
    "I've been studying for weeks and I just failed my midterm and I feel like all my effort means nothing",
    "My manager never acknowledges my work and I've been here 8 months and I feel completely invisible",
    "I feel like I'm slowly losing my friend group and I don't know how to stop it",
    "I have 4 deadlines this week and I keep starting things and not finishing any of them",
    "I moved to a new city 6 months ago and I still feel like a stranger everywhere I go",
]

DIVIDER = "─" * 60


def check_server():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        health = r.json()
        print(f"✅ Server running")
        for key, status in health.get("keys", {}).items():
            print(f"   {key}: {status}")
        return True
    except Exception:
        print("❌ Server not running. Start it with:")
        print("   uvicorn pipeline:app --reload --port 8000")
        return False


def quality_check(result: dict, input_text: str) -> list:
    """Run quality checks on pipeline output. Returns list of issues."""
    issues = []

    fable = result.get("fable", "")
    character = result.get("character", "")
    insight = result.get("embedded_insight", "")
    true_thing = result.get("specific_true_thing", "")

    # Check word count
    word_count = len(fable.split())
    if word_count < 100 or word_count > 140:
        issues.append(f"⚠️  Fable word count is {word_count} — should be ~120")

    # Check for banned words (must match WRITER_PROMPT)
    banned = ["journey", "path", "weight", "burden", "healing", "strength",
              "purpose", "determined", "resolve", "realize", "understand"]
    fable_lower = fable.lower()
    for word in banned:
        if word in fable_lower:
            issues.append(f"⚠️  Fable contains banned word: '{word}'")

    # Check insight has tension word
    tension_words = ["and", "but", "even though", "while", "despite"]
    has_tension = any(w in insight.lower() for w in tension_words)
    if not has_tension:
        issues.append(f"⚠️  Insight has no tension word: '{insight}'")

    # Check character is not generic
    generic = ["young professional", "student", "worker", "employee", "person"]
    char_lower = character.lower()
    for g in generic:
        if g in char_lower:
            issues.append(f"⚠️  Character may be generic: '{character}'")

    # Check fable doesn't end with a lesson
    last_sentence = fable.split(".")[-2] if "." in fable else fable[-100:]
    lesson_words = ["remember", "you should", "it is okay", "never forget", "learn"]
    for w in lesson_words:
        if w in last_sentence.lower():
            issues.append(f"⚠️  Fable may end with a lesson: '...{last_sentence}'")

    # Check scenes have physical objects
    scenes = result.get("scenes", {})
    for i in range(1, 6):
        prompt = scenes.get(f"scene_{i}", {}).get("prompt", "")
        if "face" in prompt.lower() and "no face" not in prompt.lower():
            issues.append(f"⚠️  Scene {i} may show character's face")
        if len(prompt) < 40:
            issues.append(f"⚠️  Scene {i} prompt too short: '{prompt}'")

    return issues


def print_result(result: dict, input_text: str, show_full: bool = True):
    print(f"\n{DIVIDER}")
    print(f"INPUT: {input_text[:80]}")
    print(DIVIDER)

    print(f"\n📋 DIRECTOR ANALYSIS")
    print(f"  Specific true thing: {result.get('specific_true_thing', 'N/A')}")
    print(f"  Why this character:  {result.get('why_this_character', 'N/A')}")
    print(f"  Character:           {result.get('character', 'N/A')}")
    print(f"  Character detail:    {result.get('character_detail', 'N/A')}")
    print(f"  Emotional arc:       {result.get('scene_emotional_arc', 'N/A')}")
    print(f"  Insight:             {result.get('embedded_insight', 'N/A')}")
    print(f"  Narration anchor:    {result.get('narration_anchor', 'N/A')}")

    vd = result.get("visual_direction", {})
    if vd:
        print(f"\n🎨 VISUAL DIRECTION")
        print(f"  Color temp:    {vd.get('color_temperature', 'N/A')}")
        print(f"  Lighting:      {vd.get('lighting_quality', 'N/A')}")
        print(f"  Movement:      {vd.get('movement_style', 'N/A')}")
        print(f"  Atmosphere:    {vd.get('atmosphere', 'N/A')}")

    print(f"\n📽️  5 SCENE PROMPTS (for Kling AI)")
    scenes = result.get("scenes", {})
    for i in range(1, 6):
        scene = scenes.get(f"scene_{i}", {})
        print(f"  Scene {i}: {scene.get('prompt', 'N/A')}")

    if show_full:
        print(f"\n📖 FABLE NARRATION ({len(result.get('fable','').split())} words)")
        print(f"  Voice tone: {result.get('voice_tone', 'N/A')}")
        print(f"\n{result.get('fable', 'N/A')}")
        reflection = result.get("reflection_line", "").strip()
        if reflection:
            print(f"\n💭 REFLECTION (show this to the viewer so the meaning is clearer)")
            print(f"   {reflection}")

    print(f"\n🏷️  ORG INSIGHT TAG: {result.get('insight_tag', 'N/A')} | Severity: {result.get('severity', 'N/A')}")

    # Quality check
    issues = quality_check(result, input_text)
    if issues:
        print(f"\n⚠️  QUALITY ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ QUALITY CHECK PASSED — no issues found")


def run_test(input_text: str, show_full: bool = True):
    print(f"\nCalling /generate-story...")
    start = time.time()

    try:
        r = requests.post(
            f"{BASE_URL}/generate-story",
            json={"user_input": input_text},
            timeout=120
        )

        elapsed = time.time() - start
        print(f"Response time: {elapsed:.1f}s")

        if r.status_code != 200:
            print(f"❌ Error {r.status_code}: {r.text[:300]}")
            return None

        result = r.json()
        print_result(result, input_text, show_full)
        return result

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 120s — server may be processing slowly")
        return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def run_all_tests():
    print(f"\n{'='*60}")
    print("RUNNING ALL 5 TEST INPUTS")
    print("Checking that each produces a completely different character")
    print(f"{'='*60}")

    characters = []
    insights   = []

    for i, input_text in enumerate(TEST_INPUTS, 1):
        print(f"\n[{i}/5] Testing: {input_text[:60]}...")
        result = run_test(input_text, show_full=False)
        if result:
            characters.append(result.get("character", ""))
            insights.append(result.get("embedded_insight", ""))

    print(f"\n{'='*60}")
    print("DIVERSITY CHECK — all characters should be completely different")
    print(f"{'='*60}")
    for i, (char, insight) in enumerate(zip(characters, insights), 1):
        print(f"\nInput {i}: {TEST_INPUTS[i-1][:50]}...")
        print(f"  Character: {char}")
        print(f"  Insight:   {insight}")

    print(f"\n{'='*60}")
    print("If any two characters feel similar, the Director prompt needs tightening.")
    print("Paste the similar outputs back to Claude and ask it to add more specificity constraints.")
    print(f"{'='*60}")


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("NarrativeCare AI — Test Script")
    print(f"{'='*60}")

    if not check_server():
        sys.exit(1)

    args = sys.argv[1:]

    if "--all" in args:
        run_all_tests()
    elif "--quality" in args:
        input_text = " ".join(a for a in args if not a.startswith("--")) or TEST_INPUTS[0]
        run_test(input_text, show_full=True)
    elif args:
        input_text = " ".join(args)
        run_test(input_text, show_full=True)
    else:
        print(f"\nUsing default test input...")
        run_test(TEST_INPUTS[0], show_full=True)

    print(f"\n{'='*60}")
    print("Test complete. To test with your own input:")
    print('  python test.py "describe your situation here"')
    print("To test all 5 inputs for diversity:")
    print("  python test.py --all")
    print(f"{'='*60}")
