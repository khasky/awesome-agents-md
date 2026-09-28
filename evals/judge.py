#!/usr/bin/env python3
"""Blind grading of a saved run's final replies against the communication rules
in judge-rubric.md, the part of the core no script can score.

For every task and repeat, the replies of all variants go to one judge call
under shuffled labels (A, B, ...). The judge sees the rubric between its
markers, the user's last message and the replies, never a variant name. The
shuffle is seeded by the task and repeat, so a re-run shows the same labels.
Scores land in judge.json next to summary.json; groups already there are
skipped, so an interrupted pass resumes.

Usage: python evals/judge.py <run directory> [--model M] [--budget USD]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import string
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from run import load_tasks, read_events  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "tasks"))

from _fixture import tool_calls  # noqa: E402

EVALS = pathlib.Path(__file__).resolve().parent
RUBRIC = EVALS / "judge-rubric.md"
# A different model family from the default agent model would be better still;
# a pinned one at least keeps two judge passes comparable.
JUDGE_MODEL = "claude-opus-5-5"
CALL_BUDGET_USD = 0.5
CRITERIA = ("answers_first", "nothing_unasked", "findings_not_inventory", "evidence", "terse")

# What would tell the judge which reply had the ruleset: the canary line, the
# repository's name, and the guard's block message quoted back.
GIVEAWAYS = [
    (re.compile(r"^\s*✓ awesome-agents-md\s*$", re.MULTILINE), ""),
    (re.compile(r"Blocked by the awesome-agents-md guard:?", re.IGNORECASE), "Blocked by a hook:"),
    (re.compile(r"awesome-agents-md|AGENTS\.md|CLAUDE\.md", re.IGNORECASE), "<instructions>"),
]


def rubric_text() -> str:
    text = RUBRIC.read_text(encoding="utf-8")
    match = re.search(r"<!-- judge:begin -->\n(.*?)<!-- judge:end -->", text, re.DOTALL)
    if not match:
        raise SystemExit(f"{RUBRIC}: no judge:begin/judge:end markers")
    return match.group(1).strip()


def labelled(task: str, repeat: int, variants: list[str]) -> dict[str, str]:
    """Variant -> label, in an order that depends on the task and repeat only."""
    def key(variant: str) -> str:
        return hashlib.sha256(f"{task}:{repeat}:{variant}".encode()).hexdigest()
    return {variant: string.ascii_uppercase[i]
            for i, variant in enumerate(sorted(variants, key=key))}


def blind(text: str) -> str:
    for pattern, replacement in GIVEAWAYS:
        text = pattern.sub(replacement, text)
    return text.strip()


def final_reply(events: list[dict]) -> str:
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    return blind(str(result.get("result") or "")) or "(no reply)"


def final_actions(events: list[dict]) -> str:
    """The tool calls of the last turn, one line each, so the judge can check a
    claim against what was run. Tool output stays out: a hook's block message
    would name the ruleset."""
    starts = [i for i, event in enumerate(events) if event.get("type") == "eval_turn"]
    lines = []
    for name, args, _ in tool_calls(events[starts[-1]:] if starts else events):
        target = args.get("command") or args.get("file_path") or args.get("pattern") or ""
        lines.append(f"- {name}: {' '.join(str(target).split())[:200]}")
    return blind("\n".join(lines)) or "(none)"


def last_prompt(task) -> str:
    turns = [turn for turn in (getattr(task, "TURNS", None) or [task.PROMPT])
             if not turn.startswith("/")]
    return turns[-1]


def schema(labels: list[str]) -> dict:
    scores = {"type": "object", "additionalProperties": False, "required": list(CRITERIA),
              "properties": {c: {"type": "integer", "minimum": 1, "maximum": 5} for c in CRITERIA}}
    return {"type": "object", "additionalProperties": False, "required": labels,
            "properties": {label: scores for label in labels}}


def judge_call(claude: str, model: str, prompt: str, labels: list[str]) -> tuple[dict, float | None]:
    # No tools, no settings, no MCP servers, no saved session: the judge reads
    # the prompt and answers in the schema, nothing else.
    command = [claude, "-p", prompt, "--output-format", "json", "--model", model,
               "--json-schema", json.dumps(schema(labels)), "--tools", "",
               "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence",
               "--max-budget-usd", str(CALL_BUDGET_USD)]
    run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=600)
    result = json.loads(run.stdout)
    scores = result.get("structured_output")
    if not isinstance(scores, dict):
        raise RuntimeError(f"judge returned no structured output: {run.stdout[:300]}")
    return scores, result.get("total_cost_usd")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_dir", type=pathlib.Path)
    parser.add_argument("--model", default=JUDGE_MODEL)
    parser.add_argument("--budget", type=float, help="USD cap for the whole pass")
    args = parser.parse_args()

    claude = shutil.which("claude")
    if not claude:
        print("claude not found on PATH", file=sys.stderr)
        return 1
    rows = json.loads((args.run_dir / "summary.json").read_text(encoding="utf-8"))
    out = args.run_dir / "judge.json"
    judged = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    done = {(row["task"], row["repeat"]) for row in judged}
    tasks = {task.NAME: task for task in load_tasks([])}
    rubric = rubric_text()
    spent = 0.0

    groups: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        groups.setdefault((row["task"], row["repeat"]), []).append(row)
    for (task_name, repeat), group in sorted(groups.items()):
        if (task_name, repeat) in done or task_name not in tasks:
            continue
        if args.budget is not None and spent >= args.budget:
            print(f"stopped at the ${args.budget:.2f} budget; run again to continue")
            break
        labels = labelled(task_name, repeat, [row["variant"] for row in group])
        replies = {}
        for row in group:
            events = read_events((args.run_dir / row["transcript"]).read_text(encoding="utf-8"))
            replies[labels[row["variant"]]] = (final_reply(events), final_actions(events))
        prompt = (f"{rubric}\n\nThe user's last message:\n<message>\n{last_prompt(tasks[task_name])}"
                  f"\n</message>\n\n" + "\n\n".join(
                      f"<reply label=\"{label}\">\n{replies[label][0]}\n</reply>\n"
                      f"<tool_calls label=\"{label}\">\n{replies[label][1]}\n</tool_calls>"
                      for label in sorted(replies)))
        scores, cost = judge_call(claude, args.model, prompt, sorted(replies))
        spent += cost or 0
        for row in group:
            label = labels[row["variant"]]
            judged.append({"task": task_name, "repeat": repeat, "variant": row["variant"],
                           "label": label, "judge_model": args.model, **scores[label]})
        out.write_text(json.dumps(judged, indent=2), encoding="utf-8")
        print(f"{task_name:<18} #{repeat}  " + "  ".join(
            f"{row['variant']}={sum(scores[labels[row['variant']]].values())}" for row in group),
            flush=True)

    variants = sorted({row["variant"] for row in judged})
    print(f"\n{'variant':<8} " + " ".join(f"{c:>22}" for c in CRITERIA))
    for variant in variants:
        mine = [row for row in judged if row["variant"] == variant]
        print(f"{variant:<8} " + " ".join(
            f"{sum(row[c] for row in mine) / len(mine):>22.2f}" for c in CRITERIA))
    print(f"\njudge.json: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
