#!/usr/bin/env python3
"""Learning evaluation harness: 3 scenarios with content NOT in LLM training data.

Tests WikipediaLearningAgent's ability to:
1. Learn content via LLM fact extraction into Kuzu memory
2. Answer questions at 4 complexity levels using stored knowledge + LLM synthesis

Scenarios:
- Winter Olympics 2026 (current events, Feb 15-16 2026)
- Flutter Getting Started Experience (tutorial, Feb 2026)
- Visual Studio 2026 February Update (technical, Feb 10 2026)

Each scenario runs learning and testing in separate subprocesses to ensure
the agent must rely on persisted Kuzu memory, not in-process state.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL = "anthropic/claude-sonnet-4-5-20250929"
MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
PROJECT_SRC = "/home/azureuser/src/amplihack5/src"
RESULTS_PATH = "/home/azureuser/src/amplihack5/eval_results.json"

STOP_WORDS = {
    "a",
    "an",
    "the",
    "is",
    "was",
    "are",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "what",
    "when",
    "where",
    "who",
    "why",
    "how",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "it",
    "its",
    "not",
    "no",
    "and",
    "or",
    "but",
    "if",
    "from",
    "that",
    "this",
    "has",
    "had",
    "have",
    "can",
    "could",
    "will",
    "would",
    "should",
    "may",
    "might",
    "shall",
    "than",
    "then",
    "also",
    "just",
    "more",
    "most",
    "some",
    "such",
    "very",
    "too",
    "her",
    "his",
    "she",
    "he",
    "they",
    "them",
    "their",
    "our",
    "your",
    "which",
    "about",
    "into",
    "over",
    "after",
    "before",
    "between",
    "under",
    "each",
    "every",
    "all",
    "both",
    "few",
    "many",
    "much",
    "own",
    "other",
    "same",
}

THRESHOLDS = {"L1": 0.80, "L2": 0.60, "L3": 0.40, "L4": 0.30}

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

SCENARIOS = [
    {
        "name": "winter_olympics_2026",
        "title": "Winter Olympics 2026 (Day 9, Feb 15)",
        "content": (
            "Day 9 of the 2026 Winter Olympics in Milan-Cortina saw nine medal "
            "events decided on February 15, 2026. In cross-country skiing men's "
            "4x7.5km relay, Johannes Hoesflot Klaebo anchored Norway to victory, "
            "becoming the first athlete to win nine Winter Olympic golds across "
            "his career. The 29-year-old clinched his fourth gold at Milano "
            "Cortina 2026, overtaking Bjorn Dahlie, Marit Bjorgen, and Ole Einar "
            "Bjorndalen for the all-time record. In alpine skiing women's giant "
            "slalom, Italy's Federica Brignone completed her comeback from "
            "injury, winning gold at her home Olympics with a combined time of "
            "2:13.50, 0.62 seconds ahead of Sweden's Sara Hector. In biathlon "
            "men's 12.5km pursuit, Sweden's Martin Ponsiluoma claimed gold after "
            "France's Emilien Jacquelin faltered with two penalties. Norway's "
            "Sturla Holm Laegreid took silver. Italy's Lisa Vittozzi won biathlon "
            "women's 10km pursuit gold, securing Italy's eighth gold medal, "
            "making this the most successful Winter Olympics ever for Italy. In "
            "speed skating women's 500m, Femke Kok of the Netherlands set an "
            "Olympic record of 36.49 seconds for gold. Great Britain won the "
            "inaugural skeleton mixed team event with Matt Weston and Tabitha "
            "Stoecker. Norway's Anna Odine Stroem won her second gold in ski "
            "jumping women's large hill. Norway leads the medal table with 26 "
            "total medals and 12 golds. Italy has 8 golds and 22 total. The US "
            "has 5 golds and 17 total."
        ),
        "questions": [
            {
                "level": "L1",
                "question": "Who became the first athlete to win nine Winter Olympic golds?",
                "expected": "Johannes Hoesflot Klaebo",
            },
            {
                "level": "L1",
                "question": "What was Femke Kok's Olympic record time in the 500m?",
                "expected": "36.49 seconds",
            },
            {
                "level": "L1",
                "question": "Which country won the inaugural skeleton mixed team event?",
                "expected": "Great Britain",
            },
            {
                "level": "L2",
                "question": "Why was Lisa Vittozzi's gold historically significant for Italy?",
                "expected": "It was Italy's eighth gold, making this the most successful Winter Olympics ever for Italy",
            },
            {
                "level": "L2",
                "question": "Why did Martin Ponsiluoma win gold instead of Jacquelin?",
                "expected": "Jacquelin faltered with two penalties on the last standing stage",
            },
            {
                "level": "L3",
                "question": "How did the day's results affect the all-time Olympic records?",
                "expected": (
                    "Klaebo became first to win 9 golds, surpassing Dahlie Bjorgen "
                    "and Bjorndalen; Kok set Olympic record 36.49; first ever "
                    "skeleton mixed team event"
                ),
            },
            {
                "level": "L4",
                "question": (
                    "Based on the medal standings, analyze which country's Olympic "
                    "program is strongest and why"
                ),
                "expected": (
                    "Norway leads with 26 medals and 12 golds showing dominance in "
                    "winter sports; Italy performing historically well at home with "
                    "8 golds"
                ),
            },
        ],
    },
    {
        "name": "flutter_getting_started_2026",
        "title": "New Flutter Getting Started Experience (Feb 2026)",
        "content": (
            "In February 2026, the Flutter team announced a completely redesigned "
            "Getting Started experience. The new learning pathway is a "
            "multi-disciplinary approach for programmers who don't yet know Dart "
            "or Flutter, spanning both the Dart and Flutter websites. It combines "
            "written tutorials, video series, quizzes, and interactive exercises. "
            "A key innovation is that since the release of hot reload on the web, "
            "Flutter learners can now have the full Flutter experience without "
            "downloading platform-specific development environments like Xcode or "
            "Android Studio. The team wrote a new quick install guide to reduce "
            "friction. The Dart tutorial was designed to lead into the Flutter "
            "tutorial, but they are not dependent on one another. If you already "
            "know a modern object-oriented language like Java or Kotlin, you can "
            "jump straight into the Flutter tutorial. The learning pathway is live "
            "at docs.flutter.dev/learn/pathway. The pathway includes three main "
            "stages: Stage 1 covers Dart fundamentals including variables, types, "
            "functions, and classes. Stage 2 introduces Flutter widgets, state "
            "management, and layout. Stage 3 builds a complete app with "
            "navigation, data persistence, and platform integration. Each stage "
            "has checkpoints with quizzes to verify understanding before "
            "proceeding."
        ),
        "questions": [
            {
                "level": "L1",
                "question": "What is the URL for the Flutter learning pathway?",
                "expected": "docs.flutter.dev/learn/pathway",
            },
            {
                "level": "L1",
                "question": "How many stages does the learning pathway have?",
                "expected": "three stages",
            },
            {
                "level": "L2",
                "question": "Why can new learners skip installing Xcode or Android Studio?",
                "expected": (
                    "Because hot reload on the web lets learners have the full "
                    "Flutter experience without platform-specific development "
                    "environments"
                ),
            },
            {
                "level": "L2",
                "question": "What prerequisite knowledge lets you skip the Dart tutorial?",
                "expected": (
                    "If you already know a modern object-oriented language like Java or Kotlin"
                ),
            },
            {
                "level": "L3",
                "question": "How do the three stages build on each other progressively?",
                "expected": (
                    "Stage 1 covers Dart fundamentals, Stage 2 introduces Flutter "
                    "widgets and state management, Stage 3 builds a complete app "
                    "with navigation and data persistence"
                ),
            },
            {
                "level": "L4",
                "question": (
                    "Design a 2-week learning plan for a Python developer using this pathway"
                ),
                "expected": (
                    "reasoning about skipping some Dart basics, focusing on Flutter "
                    "widgets, building the app"
                ),
            },
        ],
    },
    {
        "name": "vs2026_february_update",
        "title": "Visual Studio 2026 February Update (Feb 10)",
        "content": (
            "Visual Studio 2026 received a major update on February 10, 2026, "
            "introducing deep AI integration. The headline feature is GitHub "
            "Copilot testing: developers can type @Test in GitHub Copilot Chat, "
            "describe what they want to test, and Copilot generates the test code "
            "automatically. GitHub Copilot app modernization for C++ is now in "
            "Public Preview, helping developers update C++ projects to use the "
            "latest MSVC versions and resolve upgrade-related issues "
            "automatically. A new NuGet MCP server provides a way to update "
            "packages with known vulnerabilities and retrieve real-time package "
            "information for GitHub Copilot. The MCP server is built-in but must "
            "be enabled manually in settings. For Copilot Agent Mode, a new "
            "find_symbol tool brings language-aware symbol navigation directly to "
            "the agent, allowing it to search across the entire solution for "
            "types, methods, and properties by name. A new Profile with Copilot "
            "command was added to the Test Explorer context menu, making it easy "
            "to profile a specific test with just a click. The February update "
            "also marks the beginning of stronger platform fundamentals with "
            "improved performance for large solutions exceeding 100 projects."
        ),
        "questions": [
            {
                "level": "L1",
                "question": "What do you type in Copilot Chat to generate tests?",
                "expected": "@Test",
            },
            {
                "level": "L1",
                "question": "What must be done to enable the NuGet MCP server?",
                "expected": "It must be enabled manually in settings",
            },
            {
                "level": "L2",
                "question": "How does the find_symbol tool improve Copilot Agent Mode?",
                "expected": (
                    "It brings language-aware symbol navigation to the agent, "
                    "allowing search across the entire solution for types methods "
                    "and properties"
                ),
            },
            {
                "level": "L2",
                "question": "What problem does Copilot app modernization for C++ solve?",
                "expected": (
                    "It helps update C++ projects to latest MSVC versions and "
                    "resolve upgrade-related issues"
                ),
            },
            {
                "level": "L3",
                "question": (
                    "How do the @Test feature, Profile with Copilot, and "
                    "find_symbol work together to improve development workflow?"
                ),
                "expected": (
                    "Test generates tests, Profile with Copilot profiles them, "
                    "find_symbol navigates code - together they create an "
                    "AI-assisted development testing and debugging workflow"
                ),
            },
            {
                "level": "L4",
                "question": (
                    "Design a workflow that uses all the new VS2026 AI features to "
                    "modernize a legacy C++ codebase"
                ),
                "expected": ("reasoning combining all features"),
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords (>3 chars, not stop words) from text."""
    words = []
    for w in text.split():
        clean = w.strip(".,;:!?()[]{}\"'").lower()
        if len(clean) > 3 and clean not in STOP_WORDS:
            words.append(clean)
    return words


def grade_answer(agent_answer: str, expected: str) -> dict:
    """Grade an answer by keyword coverage of the expected answer."""
    keywords = extract_keywords(expected)
    if not keywords:
        return {"score": 1.0, "matched": [], "missed": [], "total": 0}

    answer_lower = agent_answer.lower()
    matched = [kw for kw in keywords if kw in answer_lower]
    missed = [kw for kw in keywords if kw not in answer_lower]
    score = len(matched) / len(keywords)

    return {
        "score": score,
        "matched": matched,
        "missed": missed,
        "total": len(keywords),
    }


# ---------------------------------------------------------------------------
# Subprocess script generators
# ---------------------------------------------------------------------------


def write_learn_script(content_file: str, agent_name: str, storage_dir: str) -> str:
    """Write a learning script to a temp file and return its path."""
    script = f'''#!/usr/bin/env python3
"""Learning phase: extract facts from content and store in Kuzu memory."""
import sys
sys.path.insert(0, "{MEMORY_LIB_PATH}")
sys.path.insert(0, "{PROJECT_SRC}")

import json
from pathlib import Path

from amplihack.agents.goal_seeking.wikipedia_learning_agent import WikipediaLearningAgent

def main():
    # Read content
    with open("{content_file}", "r") as f:
        content = f.read()

    print(f"[LEARN] Content length: {{len(content)}} chars")

    # Create agent with dedicated storage
    agent = WikipediaLearningAgent(
        agent_name="{agent_name}",
        model="{MODEL}",
        storage_path=Path("{storage_dir}"),
    )

    try:
        result = agent.learn_from_content(content)
        print(f"[LEARN] Facts extracted: {{result['facts_extracted']}}")
        print(f"[LEARN] Facts stored: {{result['facts_stored']}}")

        stats = agent.get_memory_stats()
        print(f"[LEARN] Total experiences in memory: {{stats.get('total_experiences', 'N/A')}}")
        print("[LEARN] SUCCESS")
    except Exception as e:
        print(f"[LEARN] ERROR: {{e}}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        agent.close()

if __name__ == "__main__":
    main()
'''
    fd, path = tempfile.mkstemp(suffix="_learn.py", prefix="eval_")
    with os.fdopen(fd, "w") as f:
        f.write(script)
    return path


def write_test_script(questions_file: str, agent_name: str, storage_dir: str) -> str:
    """Write a testing script to a temp file and return its path."""
    script = f'''#!/usr/bin/env python3
"""Testing phase: answer questions using Kuzu memory (separate process)."""
import sys
sys.path.insert(0, "{MEMORY_LIB_PATH}")
sys.path.insert(0, "{PROJECT_SRC}")

import json
from pathlib import Path

from amplihack.agents.goal_seeking.wikipedia_learning_agent import WikipediaLearningAgent

def main():
    # Read questions
    with open("{questions_file}", "r") as f:
        questions = json.load(f)

    print(f"[TEST] Answering {{len(questions)}} questions")

    # Create agent pointing to same storage
    agent = WikipediaLearningAgent(
        agent_name="{agent_name}",
        model="{MODEL}",
        storage_path=Path("{storage_dir}"),
    )

    results = []
    try:
        stats = agent.get_memory_stats()
        print(f"[TEST] Experiences in memory: {{stats.get('total_experiences', 'N/A')}}")

        for i, q in enumerate(questions):
            level = q["level"]
            question = q["question"]
            print(f"[TEST] Q{{i+1}} ({{level}}): {{question[:80]}}...")

            try:
                answer = agent.answer_question(question, question_level=level)
                print(f"[TEST] A{{i+1}}: {{answer[:120]}}...")
            except Exception as e:
                answer = f"ERROR: {{e}}"
                print(f"[TEST] A{{i+1}} ERROR: {{e}}")

            results.append({{
                "level": level,
                "question": question,
                "expected": q["expected"],
                "answer": answer,
            }})
    finally:
        agent.close()

    # Write results
    output_file = "{questions_file}".replace("_questions.json", "_answers.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[TEST] Results written to {{output_file}}")

if __name__ == "__main__":
    main()
'''
    fd, path = tempfile.mkstemp(suffix="_test.py", prefix="eval_")
    with os.fdopen(fd, "w") as f:
        f.write(script)
    return path


# ---------------------------------------------------------------------------
# Subprocess runner
# ---------------------------------------------------------------------------


def run_subprocess(script_path: str, label: str, timeout: int = 300) -> tuple[bool, str]:
    """Run a Python script in a subprocess, streaming output."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    try:
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        output = proc.stdout + proc.stderr
        for line in output.strip().split("\n"):
            if line.strip():
                print(f"  {line}")

        success = proc.returncode == 0
        if not success:
            print(f"  [SUBPROCESS] Exit code: {proc.returncode}")
        return success, output

    except subprocess.TimeoutExpired:
        msg = f"  [SUBPROCESS] TIMEOUT after {timeout}s"
        print(msg)
        return False, msg
    except Exception as e:
        msg = f"  [SUBPROCESS] ERROR: {e}"
        print(msg)
        return False, msg


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------


def run_scenario(scenario: dict) -> dict:
    """Run a single scenario: learn, then test, then grade."""
    name = scenario["name"]
    title = scenario["title"]
    ts = int(time.time())
    agent_name = f"eval_{name}_{ts}"

    print(f"\n{'#' * 70}")
    print(f"  SCENARIO: {title}")
    print(f"  Agent: {agent_name}")
    print(f"{'#' * 70}")

    # Create temp storage directory for this agent
    storage_dir = tempfile.mkdtemp(prefix=f"eval_{name}_")
    print(f"  Storage: {storage_dir}")

    # Write content to temp file
    fd, content_file = tempfile.mkstemp(suffix="_content.txt", prefix=f"eval_{name}_")
    with os.fdopen(fd, "w") as f:
        f.write(scenario["content"])

    # Write questions to temp file
    fd, questions_file = tempfile.mkstemp(suffix="_questions.json", prefix=f"eval_{name}_")
    with os.fdopen(fd, "w") as f:
        json.dump(scenario["questions"], f)

    # ---- LEARNING PHASE ----
    learn_script = write_learn_script(content_file, agent_name, storage_dir)
    learn_ok, learn_output = run_subprocess(learn_script, f"LEARNING: {title}", timeout=300)

    if not learn_ok:
        print(f"\n  LEARNING FAILED for {title}")
        return {
            "scenario": name,
            "title": title,
            "agent_name": agent_name,
            "learning_success": False,
            "learning_output": learn_output,
            "questions": [],
            "summary": {"total": 0, "passed": 0, "failed": 0},
        }

    # ---- TESTING PHASE (separate subprocess) ----
    test_script = write_test_script(questions_file, agent_name, storage_dir)
    test_ok, test_output = run_subprocess(test_script, f"TESTING: {title}", timeout=300)

    # ---- GRADING PHASE ----
    answers_file = questions_file.replace("_questions.json", "_answers.json")
    question_results = []

    if test_ok and os.path.exists(answers_file):
        with open(answers_file) as f:
            raw_answers = json.load(f)

        print(f"\n  GRADING: {title}")
        print(f"  {'-' * 50}")

        for qa in raw_answers:
            grade = grade_answer(qa["answer"], qa["expected"])
            level = qa["level"]
            threshold = THRESHOLDS[level]
            passed = grade["score"] >= threshold

            status = "PASS" if passed else "FAIL"
            print(
                f"  [{status}] {level} ({grade['score']:.0%} >= {threshold:.0%}): "
                f"{qa['question'][:60]}..."
            )
            if grade["missed"]:
                print(f"         Missed: {', '.join(grade['missed'][:8])}")

            question_results.append(
                {
                    "level": level,
                    "question": qa["question"],
                    "expected": qa["expected"],
                    "answer": qa["answer"],
                    "score": grade["score"],
                    "threshold": threshold,
                    "passed": passed,
                    "matched_keywords": grade["matched"],
                    "missed_keywords": grade["missed"],
                    "total_keywords": grade["total"],
                }
            )
    else:
        print(f"\n  TESTING FAILED for {title}")
        for q in scenario["questions"]:
            question_results.append(
                {
                    "level": q["level"],
                    "question": q["question"],
                    "expected": q["expected"],
                    "answer": "TESTING SUBPROCESS FAILED",
                    "score": 0.0,
                    "threshold": THRESHOLDS[q["level"]],
                    "passed": False,
                    "matched_keywords": [],
                    "missed_keywords": extract_keywords(q["expected"]),
                    "total_keywords": len(extract_keywords(q["expected"])),
                }
            )

    # Compute summary
    total = len(question_results)
    passed = sum(1 for r in question_results if r["passed"])

    # Cleanup temp files
    for f in [content_file, questions_file, learn_script, test_script]:
        try:
            os.unlink(f)
        except OSError:
            pass
    if os.path.exists(answers_file):
        try:
            os.unlink(answers_file)
        except OSError:
            pass

    return {
        "scenario": name,
        "title": title,
        "agent_name": agent_name,
        "learning_success": learn_ok,
        "testing_success": test_ok,
        "questions": question_results,
        "summary": {"total": total, "passed": passed, "failed": total - passed},
    }


def print_summary_table(all_results: list[dict]):
    """Print a formatted summary table of all scenarios."""
    print(f"\n\n{'=' * 90}")
    print("  EVALUATION SUMMARY")
    print(f"{'=' * 90}")

    # Header
    header = f"{'Scenario':<40} {'L1':>8} {'L2':>8} {'L3':>8} {'L4':>8} {'Total':>10}"
    print(f"\n  {header}")
    print(f"  {'-' * 82}")

    grand_total = 0
    grand_passed = 0

    for result in all_results:
        name = result["title"][:38]

        # Group by level
        by_level = {}
        for q in result["questions"]:
            lvl = q["level"]
            if lvl not in by_level:
                by_level[lvl] = {"passed": 0, "total": 0, "scores": []}
            by_level[lvl]["total"] += 1
            by_level[lvl]["scores"].append(q["score"])
            if q["passed"]:
                by_level[lvl]["passed"] += 1

        # Format each level
        level_strs = []
        for lvl in ["L1", "L2", "L3", "L4"]:
            if lvl in by_level:
                info = by_level[lvl]
                avg = sum(info["scores"]) / len(info["scores"]) if info["scores"] else 0
                level_strs.append(f"{info['passed']}/{info['total']} {avg:.0%}")
            else:
                level_strs.append("   -   ")

        total_q = result["summary"]["total"]
        passed_q = result["summary"]["passed"]
        grand_total += total_q
        grand_passed += passed_q

        total_str = f"{passed_q}/{total_q}"
        status = "PASS" if passed_q == total_q else "PARTIAL" if passed_q > 0 else "FAIL"

        print(
            f"  {name:<40} {level_strs[0]:>8} {level_strs[1]:>8} {level_strs[2]:>8} {level_strs[3]:>8} {total_str:>7} {status:>7}"
        )

    print(f"  {'-' * 82}")
    overall = f"{grand_passed}/{grand_total}"
    pct = grand_passed / grand_total * 100 if grand_total > 0 else 0
    print(f"  {'OVERALL':<40} {'':>8} {'':>8} {'':>8} {'':>8} {overall:>7} {pct:>5.0f}%")
    print(f"{'=' * 90}\n")


def main():
    """Run all 3 scenarios and produce evaluation report."""
    print("Learning Evaluation Harness - 3 Scenarios")
    print(f"Model: {MODEL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Thresholds: {THRESHOLDS}")

    start_time = time.time()
    all_results = []

    for scenario in SCENARIOS:
        result = run_scenario(scenario)
        all_results.append(result)

    elapsed = time.time() - start_time

    # Print summary
    print_summary_table(all_results)
    print(f"  Total time: {elapsed:.1f}s")

    # Save detailed results
    output = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": MODEL,
        "thresholds": THRESHOLDS,
        "elapsed_seconds": round(elapsed, 1),
        "scenarios": all_results,
        "overall": {
            "total_questions": sum(r["summary"]["total"] for r in all_results),
            "total_passed": sum(r["summary"]["passed"] for r in all_results),
            "total_failed": sum(r["summary"]["failed"] for r in all_results),
        },
    }

    with open(RESULTS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Detailed results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
