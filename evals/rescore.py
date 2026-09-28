#!/usr/bin/env python3
"""Re-scores saved runs after a scorer fix, for the tasks whose score reads only
the transcript (TRANSCRIPT_ONLY = True). Tasks that inspect the repository the
agent left behind cannot be re-scored: that repository is gone.

Usage: python evals/rescore.py <run directory> [...]
"""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from run import load_tasks, read_events  # noqa: E402


def main(runs: list[str]) -> int:
    tasks = {task.NAME: task for task in load_tasks([]) if getattr(task, "TRANSCRIPT_ONLY", False)}
    for run in runs:
        summary_path = pathlib.Path(run) / "summary.json"
        rows = json.loads(summary_path.read_text(encoding="utf-8"))
        changed = 0
        for row in rows:
            task = tasks.get(row["task"])
            if not task:
                continue
            transcript = pathlib.Path(run) / pathlib.PurePosixPath(row["transcript"]).name
            events = read_events(transcript.read_text(encoding="utf-8"))
            score = task.score(pathlib.Path(), events)
            if (score["passed"], score["detail"]) != (row["passed"], row["detail"]):
                print(f"{run}: {row['task']} {row['variant']} #{row['repeat']}: "
                      f"{row['detail']} -> {score['detail']}")
                row["passed"], row["detail"] = score["passed"], score["detail"]
                changed += 1
        summary_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"{run}: {changed} rows changed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
