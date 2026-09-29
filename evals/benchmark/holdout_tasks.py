"""Held-out open requests: the same kind of task as the vibe-* tasks in
coding_tasks.py, never used to tune the ruleset, so the published code size and
cost do not rest only on tasks the changes were made against. Scored the same
way: the file compiles, and source lines are the measure."""

from coding_tasks import score_vibe

TASKS = {
    "vibe-wordfreq": {"prompt": "Make me a Python script that counts word frequencies in a text file. "
                                "Write it to wordfreq.py.",
                      "score": score_vibe, "open": True, "split": "test"},
    "vibe-jsondiff": {"prompt": "Write me a Python tool that compares two JSON files and shows the "
                                "differences. Write it to jsondiff.py.",
                      "score": score_vibe, "open": True, "split": "test"},
}
