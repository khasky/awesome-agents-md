#!/usr/bin/env python3
"""Runs the same tasks through headless Claude Code with no plugin and with each
plugin under comparison, one plugin per session, and scores what each session
leaves behind.

Two task families share one table:
- coding tasks (coding_tasks.py, ported from ponytail's agentic benchmark): a
  seeded file to implement or fix, scored by executing the result for
  correctness and against adversarial input; open "build me" tasks measure
  source lines only;
- trap tasks (../tasks/*.py): the repository's own discipline evals, scored by
  their score().

Every task belongs to a split. The train split is what changes to the ruleset
are tuned against; the test split is held out and read only to accept or reject
a change, so a gain that holds on train alone is overfitting, not progress.

  python evals/benchmark/run.py --selftest          scorers only, no agent, no spend
  python evals/benchmark/run.py --split train --repeats 3 --budget 20
  python evals/benchmark/run.py --resume <run dir>
  python evals/benchmark/run.py --summary <run dir>       tables with 95% intervals
  python evals/benchmark/run.py --compare <before> <after> --arms awesome-agents-md
  python evals/benchmark/run.py --review <run dir>        scored transcripts, condensed
  python evals/benchmark/run.py --rescore <run dir>       re-score transcript-only traps
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid

BENCH = pathlib.Path(__file__).resolve().parent
EVALS = BENCH.parent
REPO = EVALS.parent
sys.path.insert(0, str(EVALS / "tasks"))
sys.path.insert(0, str(BENCH))

from _fixture import git, remove_tree, shell_commands  # noqa: E402
from harness import DEFAULT_MODEL, agent_env, load_tasks, read_events, redact, run_agent, total  # noqa: E402

DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "awesome-agents-md-benchmark"
CALL_BUDGET_USD = 1.0

# Each plugin arm is loaded from a clone pinned to one commit, so a rerun next
# month compares the same code. Every arm is installed the way its README
# installs it and runs with its default always-on behavior; i-have-adhd is
# always-on only behind a flag file, which the run creates (see claude_flags).
ARMS = {
    "baseline": None,
    "awesome-agents-md": {"path": REPO},
    "caveman": {"url": "https://github.com/JuliusBrussee/caveman.git",
                "commit": "2fd153c67988e980fb0b2455c90832159a6a5a25"},
    "ponytail": {"url": "https://github.com/DietrichGebert/ponytail.git",
                 "commit": "e3ba2aa6f1e6f0bc4d69eb09c9f0d0a93af56156"},
    "i-have-adhd": {"url": "https://github.com/ayghri/i-have-adhd.git",
                    "commit": "839872f9d1cd634fed642b4589ce7226199cc15f"},
    "superpowers": {"url": "https://github.com/obra/superpowers.git",
                    "commit": "8ca22dba9a94f28898bbce59f2537ff4d87c747d"},
    "karpathy-skills": {"url": "https://github.com/multica-ai/andrej-karpathy-skills.git",
                        "commit": "2c606141936f1eeef17fa3043a72095b4765b9c2"},
}

# The plugins keep mode flags in the Claude config directory, the same one the
# owner's own sessions read. Everything under these names is snapshotted before
# the run and put back after it.
FLAG_PREFIXES = (".caveman", ".ponytail", ".i-have-adhd")
ADHD_FLAG = ".i-have-adhd-always"

CODE_EXT = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
TEST_NAME = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|^tests?\.)")
COMMENT = re.compile(r"^\s*(#|//|/\*|\*)")
# An assistant trace in the final reply: a proposed commit message carrying the
# trailer is the same leak as a commit carrying it, and no shell guard sees it.
# A line that opens the commit proposal: "Commit message:", "**Suggested commit:**",
# "Recommended commit message" and the like, short enough to be a heading.
COMMIT_HEAD = re.compile(r"^\W*(recommended |suggested |proposed )?commit( message)?\b[^.]{0,40}$",
                         re.IGNORECASE)
CANARY = re.compile(r"^\s*✓ awesome-agents-md\s*$", re.MULTILINE)
# A commit the agent made itself; the core asks for a proposal unless the user
# asked for the commit, so a task that does not ask counts it as a breach.
COMMIT_RUN = re.compile(r"git\s[^;&|]*\bcommit\b")
TRACE = re.compile(r"co-authored-by|claude-session|claude\.ai/code/session", re.IGNORECASE)


def import_coding_tasks() -> dict:
    tasks = {}
    for name in ("coding_tasks", "holdout_tasks"):
        spec = importlib.util.spec_from_file_location(name, BENCH / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tasks.update(module.TASKS)
    return tasks


def split_of(task: str, _cache: dict = {}) -> str:
    """The split a task belongs to; saved rows from before splits existed get it
    from the task itself."""
    if not _cache:
        _cache.update({name: spec.get("split", "train") for name, spec in import_coding_tasks().items()})
        _cache.update({module.NAME: getattr(module, "SPLIT", "train") for module in load_tasks([])})
    return _cache.get(task, "train")


def asks_for_commit(task: str, _cache: dict = {}) -> bool:
    if not _cache:
        _cache.update({module.NAME: getattr(module, "ASKS_FOR_COMMIT", False) for module in load_tasks([])})
    return _cache.get(task, False)


class Job:
    """One task, whichever family it comes from, behind one interface."""

    def __init__(self, name: str, kind: str, turns: list[str], module=None, spec=None):
        self.name, self.kind, self.turns = name, kind, turns
        self.module, self.spec = module, spec
        self.ENV = getattr(module, "ENV", {}) if module else {}
        self.split = (getattr(module, "SPLIT", "train") if module is not None
                      else (spec or {}).get("split", "train"))

    def setup(self, workdir: pathlib.Path) -> None:
        if self.kind == "trap":
            self.module.setup(workdir)
            return
        workdir.mkdir(parents=True)
        for name, text in self.spec.get("seed", {}).items():
            (workdir / name).write_text(text, encoding="utf-8")
        git(workdir, "init", "-q", "-b", "main")
        git(workdir, "config", "user.name", "Eval Fixture")
        git(workdir, "config", "user.email", "fixture@example.com")
        git(workdir, "config", "core.hooksPath", ".git/hooks")
        git(workdir, "add", "-A")
        git(workdir, "commit", "-q", "--allow-empty", "-m", "Initial commit")

    def between_turns(self, workdir: pathlib.Path, turn: int) -> None:
        if self.module is not None and hasattr(self.module, "between_turns"):
            self.module.between_turns(workdir, turn)

    def score(self, workdir: pathlib.Path, events: list[dict]) -> dict:
        if self.kind == "trap":
            result = self.module.score(workdir, events)
            return {"passed": result["passed"], "detail": result["detail"]}
        # The produced code runs in a child process: it is the agent's code, it
        # may hang or exit, and one cell's module must not leak into the next.
        probe = ("import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); "
                 "import coding_tasks, holdout_tasks; "
                 "tasks = {**coding_tasks.TASKS, **holdout_tasks.TASKS}; "
                 "print(json.dumps(tasks[sys.argv[2]]['score'](pathlib.Path(sys.argv[3]))))")
        try:
            run = subprocess.run([sys.executable, "-c", probe, str(BENCH), self.name, str(workdir)],
                                 capture_output=True, text=True, encoding="utf-8", timeout=120,
                                 cwd=workdir)
            result = json.loads(run.stdout.strip().splitlines()[-1])
        except (subprocess.TimeoutExpired, IndexError, json.JSONDecodeError) as error:
            result = {"correct": 0, "safe": 0, "reason": f"scorer failed: {type(error).__name__}"}
        passed = bool(result["correct"] and result["safe"])
        return {"passed": passed, "correct": result["correct"], "safe": result["safe"],
                "detail": result["reason"], **code_stats(workdir)}


def load_jobs(names: list[str], split: str = "all") -> list[Job]:
    jobs = [Job(name, "coding", [spec["prompt"]], spec=spec)
            for name, spec in import_coding_tasks().items()]
    jobs += [Job(task.NAME, "trap", getattr(task, "TURNS", None) or [task.PROMPT], module=task)
             for task in load_tasks([])]
    return [job for job in jobs if (not names or job.name in names)
            and (split == "all" or job.split == split)]


def code_stats(workdir: pathlib.Path) -> dict:
    """Lines the agent added to source files, from git, against the seeded
    commit: tests are counted apart, since a test is not bloat, and comment
    lines apart from code."""
    # Against the seeded commit, not HEAD: an agent that commits its own work
    # would otherwise hide every line it wrote.
    git(workdir, "add", "-A")
    base = git(workdir, "rev-list", "--max-parents=0", "HEAD").split()[0]
    numstat = git(workdir, "diff", "--cached", "--numstat", base)
    added = git(workdir, "diff", "--cached", "--unified=0", "--no-color", base)
    src = comments = tests = 0
    current = ""
    for line in added.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else ""
            continue
        if not line.startswith("+") or not current.strip():
            continue
        path = pathlib.PurePosixPath(current)
        text = line[1:]
        if path.suffix not in CODE_EXT or "__pycache__" in path.parts or not text.strip():
            continue
        if TEST_NAME.search(path.name) or "tests" in path.parts:
            tests += 1
        elif COMMENT.match(text):
            comments += 1
        else:
            src += 1
    files = [row.split("\t")[-1] for row in numstat.splitlines() if row.strip()]
    return {"src_loc": src, "comment_loc": comments, "test_loc": tests,
            "files_touched": len([f for f in files if pathlib.PurePosixPath(f).suffix in CODE_EXT
                                  and "__pycache__" not in f])}


def plugin_dir(arm: str, cache: pathlib.Path) -> pathlib.Path | None:
    source = ARMS[arm]
    if source is None:
        return None
    if "path" in source:
        return source["path"]
    target = cache / f"{arm}-{source['commit'][:12]}"
    if not (target / ".claude-plugin" / "plugin.json").is_file():
        if target.exists():
            remove_tree(target)
        subprocess.run(["git", "clone", "-q", source["url"], str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "checkout", "-q", source["commit"]], check=True)
    head = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()
    if head != source["commit"]:
        raise SystemExit(f"{target} is at {head}, expected {source['commit']}")
    return target


def agent_command(claude: str, prompt: str, model: str, call_budget: float,
                  plugin: pathlib.Path | None, session: tuple[str, str],
                  effort: str | None = None) -> list[str]:
    # No user-level settings, plugins or hooks, no global CLAUDE.md, and
    # exactly one plugin per arm. Every arm keeps its session on disk, because
    # a Stop hook reads the transcript and a scenario resumes it; the runner
    # deletes it afterwards.
    global_memory = (pathlib.Path.home() / ".claude" / "CLAUDE.md").as_posix()
    isolation = json.dumps({"claudeMdExcludes": [global_memory, "**/.claude/CLAUDE.md"]})
    command = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--setting-sources", "project,local", "--settings", isolation,
               "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "PowerShell",
               "--model", model, "--max-budget-usd", str(call_budget), *session]
    if effort:
        command += ["--effort", effort]
    if plugin is not None:
        command += ["--plugin-dir", str(plugin)]
    return command


def run_cell(claude: str, job: Job, arm: str, plugin: pathlib.Path | None, model: str,
             call_budget: float, run_dir: pathlib.Path, repeat: int,
             effort: str | None = None) -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"bench-{job.name}-"))
    workdir = scratch / "repo"
    session_id = str(uuid.uuid4())
    out = run_dir / f"{job.name}.{arm}.{repeat}.jsonl"
    try:
        job.setup(workdir)
        started = time.monotonic()
        stdout, exit_code = "", 0
        for index, prompt in enumerate(job.turns):
            if index:
                job.between_turns(workdir, index)
            session = ("--session-id" if index == 0 else "--resume", session_id)
            if len(job.turns) > 1:
                stdout += json.dumps({"type": "eval_turn", "turn": index, "prompt": prompt}) + "\n"
            text, exit_code = run_agent(agent_command(claude, prompt, model, call_budget, plugin,
                                                      session, effort), workdir, agent_env(job))
            stdout += text if text.endswith("\n") or not text else text + "\n"
            if exit_code:
                break
        seconds = round(time.monotonic() - started)
        out.write_text(redact(stdout, scratch), encoding="utf-8")
        events = read_events(stdout)
        init = next((e for e in events if e.get("subtype") == "init"), {})
        results = [e for e in events if e.get("type") == "result"]
        score = job.score(workdir, events)
    finally:
        session_dir = (pathlib.Path.home() / ".claude" / "projects"
                       / re.sub(r"[^A-Za-z0-9]", "-", str(workdir)))
        for path in (scratch, session_dir if "bench-" in session_dir.name else None):
            if path is not None and path.is_dir():
                discard(path)
    reply = str(results[-1].get("result") or "") if results else ""
    return {
        "task": job.name, "kind": job.kind, "arm": arm, "repeat": repeat,
        "model": init.get("model"), "effort": effort, "claude_code": init.get("claude_code_version"),
        "plugins": [p.get("name") for p in init.get("plugins", []) if isinstance(p, dict)],
        **score,
        "cost_usd": total(results, lambda r: r.get("total_cost_usd")),
        "input_tokens": total(results, lambda r: None if "usage" not in r else
                              r["usage"].get("input_tokens", 0)
                              + r["usage"].get("cache_creation_input_tokens", 0)
                              + r["usage"].get("cache_read_input_tokens", 0)),
        "output_tokens": total(results, lambda r: r.get("usage", {}).get("output_tokens")),
        "agent_turns": total(results, lambda r: r.get("num_turns")),
        "split": job.split,
        "unasked_commit": not getattr(job.module, "ASKS_FOR_COMMIT", False) and any(
            COMMIT_RUN.search(command) for command in shell_commands(events)),
        "reply_words": len(reply.split()), "prose_words": prose_words(reply), "reply_trace": bool(TRACE.search(reply)),
        "seconds": seconds, "agent_exit": exit_code,
        "transcript": out.name,
    }


def discard(path: pathlib.Path) -> None:
    # A process the agent started and left running (a dev server) keeps its
    # working directory open on Windows. The cell's score is already taken, so
    # a directory that will not go away is reported and left for the OS temp
    # cleanup instead of failing the run.
    for attempt in range(5):
        try:
            remove_tree(path)
            return
        except OSError:
            time.sleep(2 * (attempt + 1))
    print(f"warning: could not remove {path}; a process the agent started may still hold it",
          file=sys.stderr, flush=True)


class claude_flags:
    """Snapshot the plugins' flag files in the Claude config directory, create
    the i-have-adhd always-on flag for the run, and restore the snapshot after,
    so the run leaves the owner's own sessions as it found them."""

    def __init__(self, adhd: bool):
        self.root = pathlib.Path.home() / ".claude"
        self.adhd = adhd

    def entries(self) -> dict[pathlib.Path, bytes | None]:
        found = {}
        for top in self.root.iterdir() if self.root.is_dir() else []:
            if not top.name.startswith(FLAG_PREFIXES):
                continue
            for path in [top, *top.rglob("*")] if top.is_dir() else [top]:
                found[path] = path.read_bytes() if path.is_file() else None
        return found

    def __enter__(self):
        self.before = self.entries()
        if self.adhd:
            (self.root / ADHD_FLAG).write_text("", encoding="utf-8")
        return self

    def __exit__(self, *_):
        after = self.entries()
        for path in sorted(after, key=lambda p: len(p.parts), reverse=True):
            if path not in self.before:
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
        for path, content in self.before.items():
            if content is not None and (not path.is_file() or path.read_bytes() != content):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)


def selftest() -> int:
    """Every coding task's good reference must score correct and safe, and its
    bad reference must fail on the axis the task tests; every trap task's score
    must tell a scripted good outcome from a bad one (check_traps.py). An
    instrument that cannot tell them apart would report noise as a result."""
    failures = 0
    for name, spec in import_coding_tasks().items():
        if spec.get("open"):
            continue
        axis = spec.get("axis", "safe")
        for kind in ("good", "bad"):
            with tempfile.TemporaryDirectory() as scratch:
                job = Job(name, "coding", [spec["prompt"]], spec=spec)
                workdir = pathlib.Path(scratch) / "repo"
                job.setup(workdir)
                (workdir / spec["file"]).write_text(spec[kind], encoding="utf-8")
                result = job.score(workdir, [])
            ok = result["passed"] if kind == "good" else not result[axis]
            failures += not ok
            print(f"{'ok' if ok else 'XX'}  {name:<15} {kind:<4} correct={result['correct']} "
                  f"safe={result['safe']} src_loc={result['src_loc']}  {result['detail']}")
    import check_traps
    failures += check_traps.main()
    print(f"\nselftest: {'all scorers valid' if not failures else f'{failures} broken'}")
    return failures


def prose_words(reply: str) -> int:
    """Words of the answer itself: the commit proposal that ends a reply (from
    its heading line on) and the canary line are not counted, since the ruleset
    asks for both and neither is prose the user reads for the answer."""
    lines = reply.splitlines()
    cut = next((i for i, line in enumerate(lines) if COMMIT_HEAD.match(line)), len(lines))
    return len(CANARY.sub("", "\n".join(lines[:cut])).split())


def fill_reply_metrics(rows: list[dict], run_dir: pathlib.Path) -> None:
    """Rows from runs made before a reply metric existed get it from their transcript."""
    for row in rows:
        if all(key in row for key in ("reply_trace", "prose_words", "unasked_commit")):
            continue
        events = read_events((run_dir / row["transcript"]).read_text(encoding="utf-8"))
        results = [e for e in events if e.get("type") == "result"]
        reply = str(results[-1].get("result") or "") if results else ""
        row["reply_trace"] = bool(TRACE.search(reply))
        row["prose_words"] = prose_words(reply)
        row["unasked_commit"] = not asks_for_commit(row["task"]) and any(
            COMMIT_RUN.search(command) for command in shell_commands(events))


def wilson(passes: int, total: int) -> tuple[float, float]:
    """95% Wilson interval for a pass rate: honest at the small counts a
    benchmark cell has, where passes/total +- 2 sigma would leave [0, 1]."""
    if not total:
        return 0.0, 0.0
    z, p = 1.96, passes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return centre - half, centre + half


def mean_interval(values: list[float]) -> tuple[float, float, float] | None:
    values = [v for v in values if v is not None]
    if not values:
        return None
    centre = sum(values) / len(values)
    if len(values) < 2:
        return centre, centre, centre
    sd = math.sqrt(sum((v - centre) ** 2 for v in values) / (len(values) - 1))
    half = 1.96 * sd / math.sqrt(len(values))
    return centre, centre - half, centre + half


def infra_failures(rows: list[dict]) -> list[dict]:
    """Cells whose score says nothing about the ruleset: the agent process
    failed, timed out, or left no result event."""
    return [r for r in rows if r.get("agent_exit") not in (0, None) or r.get("cost_usd") is None]


def summarize(rows: list[dict], arms: list[str]) -> None:
    def mean(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    def fmt(value, pattern):
        return "n/a" if value is None else pattern.format(value)

    for row in rows:
        row.setdefault("split", split_of(row["task"]))
    splits = sorted({r["split"] for r in rows})
    for split in splits:
        part = [r for r in rows if r["split"] == split]
        print(f"\n{split} split, 95% intervals")
        print(f"{'arm':<18} {'traps':>17} {'cost per task':>26}")
        for arm in arms:
            mine = [r for r in part if r["arm"] == arm]
            traps = [r for r in mine if r["kind"] == "trap"]
            if not mine:
                continue
            passes = sum(r["passed"] for r in traps)
            low, high = wilson(passes, len(traps))
            cost = mean_interval([r["cost_usd"] for r in mine])
            cost_text = "n/a" if cost is None else f"${cost[0]:.3f} [{cost[1]:.3f}-{cost[2]:.3f}]"
            trap_text = f"{passes}/{len(traps)} [{low:.0%}-{high:.0%}]" if traps else "-"
            print(f"{arm:<18} {trap_text:>17} {cost_text:>26}")
    broken = infra_failures(rows)
    if broken:
        print(f"\ninfrastructure: {len(broken)} cells failed outside the agent's control "
              f"(non-zero exit, timeout or no result): "
              + ", ".join(f"{r['task']}/{r['arm']}#{r['repeat']}" for r in broken[:8])
              + (" ..." if len(broken) > 8 else ""))

    print(f"\n{'arm':<18} {'traps':>7} {'coding':>7} {'safe':>6} {'open loc':>9} "
          f"{'coding loc':>11} {'words':>6} {'prose':>6} {'trace':>6} {'commit':>7} {'$/cell':>7} {'s/cell':>7}")
    for arm in arms:
        mine = [r for r in rows if r["arm"] == arm]
        if not mine:
            continue
        traps = [r for r in mine if r["kind"] == "trap"]
        coding = [r for r in mine if r["kind"] == "coding" and not r["task"].startswith("vibe-")]
        open_tasks = [r for r in mine if r["task"].startswith("vibe-")]
        print(f"{arm:<18} {sum(r['passed'] for r in traps):>3}/{len(traps):<3} "
              f"{sum(r['passed'] for r in coding):>3}/{len(coding):<3} "
              f"{fmt(mean([r['safe'] for r in coding]), '{:.0%}'):>6} "
              f"{fmt(mean([r['src_loc'] for r in open_tasks]), '{:.0f}'):>9} "
              f"{fmt(mean([r['src_loc'] for r in coding]), '{:.1f}'):>11} "
              f"{fmt(mean([r['reply_words'] for r in mine]), '{:.0f}'):>6} "
              f"{fmt(mean([r['prose_words'] for r in mine]), '{:.0f}'):>6} "
              f"{sum(bool(r.get('reply_trace')) for r in mine):>6} "
              f"{sum(bool(r.get('unasked_commit')) for r in mine):>3}/{len(mine):<3} "
              f"{fmt(mean([r['cost_usd'] for r in mine]), '${:.3f}'):>7} "
              f"{fmt(mean([r['seconds'] for r in mine]), '{:.0f}'):>7}")

    print(f"\n{'task':<18}{'split':>6}" + "".join(f"{arm[:14]:>15}" for arm in arms))
    for task in sorted({r["task"] for r in rows}):
        cells = []
        for arm in arms:
            mine = [r for r in rows if r["task"] == task and r["arm"] == arm]
            if not mine:
                cells.append("-")
                continue
            cell = f"{sum(r['passed'] for r in mine)}/{len(mine)}"
            if mine[0]["kind"] == "coding":
                cell += f" {mean([r['src_loc'] for r in mine]):.0f}L"
            cells.append(cell)
        print(f"{task:<18}{split_of(task):>6}" + "".join(f"{cell:>15}" for cell in cells))


def load_rows(run_dir: pathlib.Path) -> list[dict]:
    rows = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    fill_reply_metrics(rows, run_dir)
    for row in rows:
        row.setdefault("split", split_of(row["task"]))
    return rows


def compare(before: pathlib.Path, after: pathlib.Path, arms: list[str], split: str) -> None:
    """Two runs of the same tasks, metric by metric, with a 95% interval on the
    difference. A change whose interval straddles zero is within the noise and
    is not evidence either way."""
    rows_a, rows_b = load_rows(before), load_rows(after)
    tasks = ({r["task"] for r in rows_a} & {r["task"] for r in rows_b})
    for arm in arms:
        a = [r for r in rows_a if r["arm"] == arm and r["task"] in tasks and (split == "all" or r["split"] == split)]
        b = [r for r in rows_b if r["arm"] == arm and r["task"] in tasks and (split == "all" or r["split"] == split)]
        if not a or not b:
            continue
        print(f"\n{arm}: {len(a)} cells before, {len(b)} after, {len(tasks)} shared tasks, split {split}")
        ta, tb = [r for r in a if r["kind"] == "trap"], [r for r in b if r["kind"] == "trap"]
        if ta and tb:
            pa, pb = sum(r["passed"] for r in ta) / len(ta), sum(r["passed"] for r in tb) / len(tb)
            half = 1.96 * math.sqrt(pa * (1 - pa) / len(ta) + pb * (1 - pb) / len(tb))
            verdict = "within noise" if abs(pb - pa) <= half else ("better" if pb > pa else "worse")
            print(f"  trap pass rate  {pa:6.1%} -> {pb:6.1%}  diff {pb - pa:+.1%} +- {half:.1%}  {verdict}")
        # Paired by task: cost and length differ far more between tasks than
        # between two versions on one task, so each task is compared with
        # itself and the interval is taken over the per-task differences.
        for key, label, lower_is_better in (("cost_usd", "cost per task", True),
                                            ("prose_words", "words in answer", True)):
            diffs, before_means, after_means = [], [], []
            for task in sorted(tasks):
                va = [r[key] for r in a if r["task"] == task and r[key] is not None]
                vb = [r[key] for r in b if r["task"] == task and r[key] is not None]
                if va and vb:
                    before_means.append(sum(va) / len(va))
                    after_means.append(sum(vb) / len(vb))
                    diffs.append(after_means[-1] - before_means[-1])
            interval = mean_interval(diffs)
            if not interval or len(diffs) < 2:
                continue
            diff, low, high = interval
            verdict = ("within noise" if low <= 0 <= high
                       else ("better" if (diff < 0) == lower_is_better else "worse"))
            before_mean = sum(before_means) / len(before_means)
            print(f"  {label:<15} {before_mean:8.3f} -> {before_mean + diff:8.3f}  diff {diff:+.3f} "
                  f"[{low:+.3f}, {high:+.3f}] over {len(diffs)} tasks  {verdict}")


def discrimination(run_dirs: list[pathlib.Path], arms: list[str]) -> None:
    """A task earns its place when it separates the arms and gets easier for a
    stronger model. Runs on several models, ordered from the weakest, give each
    task's pass rate per arm and model, and flag a task every arm passes on
    every model (it measures nothing) or one the baseline passes less often on
    a stronger model (ambiguous, or scored wrongly)."""
    runs = [(run_dir.name, load_rows(run_dir)) for run_dir in run_dirs]
    tasks = sorted({r["task"] for _, rows in runs for r in rows})
    def model_of(name: str) -> str:
        found = re.search(r"(claude-[a-z0-9-]+?)(-(low|medium|high|xhigh|max))?(-[a-z0-9-]+)?$", name)
        return found.group(1).replace("claude-", "") if found else name[-14:]
    header = "".join(f"{model_of(name)[:15]:>16}" for name, _ in runs)
    print(f"{'task':<18}{'split':>6}{header}   flag  (each cell: baseline / this ruleset / best other plugin)")
    for task in tasks:
        cells, rates, baseline = [], [], []
        for _, rows in runs:
            def rate(arm):
                mine = [r["passed"] for r in rows if r["task"] == task and r["arm"] == arm]
                return sum(mine) / len(mine) if mine else None
            per_arm = {arm: rate(arm) for arm in arms}
            others = [v for arm, v in per_arm.items() if arm not in ("baseline", "awesome-agents-md") and v is not None]
            best = max(others) if others else None
            fmt = lambda v: "-" if v is None else f"{v:.0%}"
            cells.append(f"{fmt(per_arm.get('baseline'))}/{fmt(per_arm.get('awesome-agents-md'))}/{fmt(best)}")
            rates += [v for v in per_arm.values() if v is not None]
            baseline.append(per_arm.get("baseline"))
        flags = []
        # An open request passes when its file compiles; code size is its
        # measure, so a full pass there says nothing about discrimination.
        if rates and min(rates) >= 0.9 and not task.startswith("vibe-"):
            flags.append("saturated")
        known = [v for v in baseline if v is not None]
        if len(known) >= 2 and any(later + 0.2 < earlier for earlier, later in zip(known, known[1:])):
            flags.append("baseline falls on a stronger model")
        print(f"{task:<18}{split_of(task):>6}" + "".join(f"{c:>16}" for c in cells) + "   " + ", ".join(flags))


def review(run_dir: pathlib.Path, per_task: int, arms: list[str]) -> None:
    """Scored transcripts, condensed to the tool calls, errors and final reply,
    for reading a sample before trusting a scorer's verdicts."""
    rows = load_rows(run_dir)
    for task in sorted({r["task"] for r in rows}):
        for arm in arms:
            for row in [r for r in rows if r["task"] == task and r["arm"] == arm][:per_task]:
                events = read_events((run_dir / row["transcript"]).read_text(encoding="utf-8"))
                steps = []
                for event in events:
                    if event.get("type") == "eval_turn":
                        steps.append(f"[turn {event['turn']}]")
                    if event.get("type") == "assistant":
                        for block in event["message"]["content"]:
                            if block.get("type") == "tool_use":
                                target = (block["input"].get("command") or block["input"].get("file_path") or "")
                                steps.append(f"{block['name']}: {' '.join(str(target).split())[:90]}")
                    if event.get("type") == "user":
                        for block in event["message"].get("content") or []:
                            if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
                                content = block.get("content")
                                text = content if isinstance(content, str) else json.dumps(content)
                                steps.append(f"  error: {' '.join(text.split())[:90]}")
                results = [e for e in events if e.get("type") == "result"]
                reply = " ".join(str(results[-1].get("result") or "").split()) if results else ""
                print(f"\n== {task} / {arm} #{row['repeat']}: {'PASS' if row['passed'] else 'FAIL'}, {row['detail']}")
                for step in steps:
                    print(f"   {step}")
                print(f"   reply: {reply[:300]}")


def rescore(run_dir: pathlib.Path) -> None:
    """Re-score the trap tasks whose verdict reads only the transcript, after a
    scorer fix; the repository a cell left behind is gone."""
    tasks = {task.NAME: task for task in load_tasks([]) if getattr(task, "TRANSCRIPT_ONLY", False)}
    rows = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    changed = 0
    for row in rows:
        task = tasks.get(row["task"])
        if not task:
            continue
        events = read_events((run_dir / row["transcript"]).read_text(encoding="utf-8"))
        score = task.score(pathlib.Path(), events)
        if (score["passed"], score["detail"]) != (row["passed"], row["detail"]):
            print(f"{row['task']} {row['arm']} #{row['repeat']}: {row['detail']} -> {score['detail']}")
            row["passed"], row["detail"] = score["passed"], score["detail"]
            changed += 1
    (run_dir / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"{run_dir.name}: {changed} rows changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("tasks", nargs="*", help="task names (default: all)")
    parser.add_argument("--arms", default=",".join(ARMS), help=f"subset of {','.join(ARMS)}")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"),
                        help="passed to every agent session as --effort")
    parser.add_argument("--workers", type=int, default=4, help="cells run in parallel")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--call-budget", type=float, default=CALL_BUDGET_USD)
    parser.add_argument("--budget", type=float, help="USD cap: no new cell starts past it")
    parser.add_argument("--resume", type=pathlib.Path, metavar="RUN_DIR")
    parser.add_argument("--plugin-path", action="append", default=[], metavar="ARM=PATH",
                        help="load an arm's plugin from PATH instead of its pinned source, "
                             "to measure a candidate change before it lands")
    parser.add_argument("--label", help="suffix for the run directory, naming the candidate")
    parser.add_argument("--split", choices=("train", "test", "all"), default="all",
                        help="tasks to run: train is tuned against, test is held out")
    parser.add_argument("--compare", nargs=2, type=pathlib.Path, metavar=("BEFORE", "AFTER"),
                        help="difference between two runs, with 95%% intervals")
    parser.add_argument("--review", type=pathlib.Path, metavar="RUN_DIR",
                        help="print condensed scored transcripts to audit the scorers")
    parser.add_argument("--per-task", type=int, default=1, help="transcripts per task and arm for --review")
    parser.add_argument("--rescore", type=pathlib.Path, metavar="RUN_DIR",
                        help="re-score transcript-only trap tasks of a saved run")
    parser.add_argument("--discrimination", nargs="+", type=pathlib.Path, metavar="RUN_DIR",
                        help="per-task pass rates across runs on several models, weakest first")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--summary", type=pathlib.Path, metavar="RUN_DIR",
                        help="print the tables of a saved run and exit")
    args = parser.parse_args()

    if args.selftest:
        return 1 if selftest() else 0
    arms = args.arms.split(",")
    if not set(arms) <= set(ARMS):
        parser.error(f"unknown arm in {args.arms}")
    if args.summary:
        summarize(load_rows(args.summary), arms)
        return 0
    if args.compare:
        compare(*args.compare, arms, args.split)
        return 0
    if args.discrimination:
        discrimination(args.discrimination, arms)
        return 0
    if args.review:
        review(args.review, args.per_task, arms)
        return 0
    if args.rescore:
        rescore(args.rescore)
        return 0
    claude = shutil.which("claude")
    if not claude:
        print("claude not found on PATH", file=sys.stderr)
        return 1

    if args.resume:
        run_dir = args.resume.resolve()
        rows = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    else:
        suffix = f"-{args.label}" if args.label else ""
        effort = f"-{args.effort}" if args.effort else ""
        run_dir = args.out.resolve() / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.model}{effort}{suffix}"
        rows = []
    if REPO in run_dir.parents:
        parser.error("--out points inside the repository; results are kept outside it")
    run_dir.mkdir(parents=True, exist_ok=True)
    plugins = {arm: plugin_dir(arm, args.out.resolve() / "plugins") for arm in arms}
    for override in args.plugin_path:
        arm, _, path = override.partition("=")
        if arm not in plugins or not (pathlib.Path(path) / ".claude-plugin" / "plugin.json").is_file():
            parser.error(f"--plugin-path {override}: unknown arm or no .claude-plugin/plugin.json there")
        plugins[arm] = pathlib.Path(path).resolve()
    done = {(r["task"], r["arm"], r["repeat"]) for r in rows}
    cells = [(job, arm, repeat) for repeat in range(1, args.repeats + 1)
             for job in load_jobs(args.tasks, args.split) for arm in arms
             if (job.name, arm, repeat) not in done]
    lock = threading.Lock()
    spent = [sum(r.get("cost_usd") or 0 for r in rows)]
    stopped = threading.Event()

    def one(cell):
        job, arm, repeat = cell
        if stopped.is_set() or (args.budget is not None and spent[0] >= args.budget):
            stopped.set()
            return
        row = run_cell(claude, job, arm, plugins[arm], args.model, args.call_budget, run_dir, repeat,
                       args.effort)
        with lock:
            rows.append(row)
            spent[0] += row["cost_usd"] or 0
            print(f"{row['task']:<16} {arm:<18} #{repeat}  {'PASS' if row['passed'] else 'FAIL'}  "
                  f"{row.get('src_loc', '')!s:>4}  {row['detail']}", flush=True)
            (run_dir / "summary.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    with claude_flags(adhd="i-have-adhd" in arms):
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(one, cells))
    summarize(rows, arms)
    if stopped.is_set():
        print(f"\nstopped at the ${args.budget:.2f} budget after ${spent[0]:.2f}; "
              f"continue with --resume {run_dir}")
    print(f"\ntranscripts and summary.json: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
