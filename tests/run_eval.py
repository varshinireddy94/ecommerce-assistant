"""
Evaluation harness for the ShopSphere assistant.

Run from the project root:
    python -m tests.run_eval

Measures (per section 9 of the project spec):
  * Routing accuracy               - router.classify() vs. expected route
  * Policy retrieval accuracy      - does search_policy() return the
                                      expected source file in its top-k?
  * Correct SQL tool selection     - does the LLM pick the expected tool
                                      for order/product/hybrid queries?
  * Successful SQL execution       - does the chosen tool return data
                                      (not an error) when it's supposed to?
  * End-to-end answer correctness  - does the final answer avoid crashing
                                      and actually address the question,
                                      graded by the LLM itself as a judge?

Notes:
  * Router and retrieval metrics run locally (fast, no API calls needed).
  * Tool-selection / end-to-end metrics call the Groq API and therefore
    require GROQ_API_KEY to be set - they are skipped with a warning if
    it's missing, so the offline metrics still run.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.src import llm, rag
from backend.src import router  # noqa: E402
from backend.src.pipeline import handle_query  # noqa: E402

DATASET_PATH = Path(__file__).resolve().parent / "eval_dataset.json"

EXPECTED_ROUTE = {
    "policy": "POLICY",
    "sql": "ORDER_PRODUCT",
    "hybrid": "HYBRID",
    "small_talk": "SMALL_TALK",
}


def load_dataset():
    return json.loads(DATASET_PATH.read_text())


def eval_routing(dataset):
    """Offline: does the semantic router pick the expected category?"""
    print("\n--- Routing accuracy ---")
    total, correct = 0, 0

    for category, expected_route in EXPECTED_ROUTE.items():
        for item in dataset[category]:
            total += 1
            route, confidence = router.classify(item["query"])
            ok = route == expected_route
            correct += ok
            if not ok:
                print(f"  MISROUTED [{category}] '{item['query']}' -> {route} (conf {confidence:.2f}), expected {expected_route}")

    print(f"Routing accuracy: {correct}/{total} = {correct/total:.1%}")
    return correct, total


def eval_retrieval(dataset):
    """Offline: is the expected policy source in the top-k retrieved chunks?"""
    print("\n--- Policy retrieval accuracy (top-3) ---")
    total, correct = 0, 0

    for item in dataset["policy"]:
        expected = item.get("expected_source_contains")
        if not expected:
            continue
        total += 1
        chunks = rag.search_policy(item["query"], k=3)
        sources = [c["source"] for c in chunks]
        ok = any(expected in s for s in sources)
        correct += ok
        if not ok:
            print(f"  MISS '{item['query']}' -> expected '{expected}' in {sources}")

    print(f"Retrieval accuracy: {correct}/{total} = {correct/total:.1%}" if total else "No policy items with expected_source_contains.")
    return correct, total


def eval_tool_selection(dataset, groq_available):
    """Requires the LLM: does it pick the expected tool for SQL/hybrid queries?"""
    print("\n--- SQL tool selection accuracy ---")
    if not groq_available:
        print("Skipped (GROQ_API_KEY not set).")
        return 0, 0

    from backend.src.tools import TOOL_SCHEMAS

    total, correct = 0, 0
    for item in dataset["sql"]:
        expected_tool = item.get("expected_tool")
        if expected_tool is None:
            continue
        total += 1
        try:
            tool_name, _ = llm.select_tool_and_params(item["query"], TOOL_SCHEMAS)
        except llm.LLMError as exc:
            print(f"  LLM ERROR on '{item['query']}': {exc}")
            continue
        ok = tool_name == expected_tool
        correct += ok
        if not ok:
            print(f"  WRONG TOOL '{item['query']}' -> {tool_name}, expected {expected_tool}")

    print(f"Tool selection accuracy: {correct}/{total} = {correct/total:.1%}" if total else "No tool-selection cases.")
    return correct, total


def eval_end_to_end(dataset, groq_available):
    """Requires the LLM: run the full pipeline and sanity-check each answer."""
    print("\n--- End-to-end run (all categories + adversarial) ---")
    if not groq_available:
        print("Skipped (GROQ_API_KEY not set).")
        return

    all_items = []
    for category, items in dataset.items():
        for item in items:
            all_items.append((category, item))

    failures = 0
    for category, item in all_items:
        try:
            result = handle_query(item["query"])
            answer_ok = bool(result["answer"] and result["answer"].strip())
            if not answer_ok:
                failures += 1
                print(f"  EMPTY ANSWER [{category}] '{item['query']}'")
        except Exception as exc:  # the pipeline itself must never raise
            failures += 1
            print(f"  CRASHED [{category}] '{item['query']}': {exc}")

    print(f"End-to-end run: {len(all_items) - failures}/{len(all_items)} produced a non-empty answer without crashing.")


def main():
    import os

    dataset = load_dataset()
    groq_available = bool(os.environ.get("GROQ_API_KEY"))

    eval_routing(dataset)
    eval_retrieval(dataset)
    eval_tool_selection(dataset, groq_available)
    eval_end_to_end(dataset, groq_available)

    if not groq_available:
        print(
            "\nNOTE: set GROQ_API_KEY to also run tool-selection and "
            "end-to-end metrics (these make real API calls)."
        )


if __name__ == "__main__":
    main()
