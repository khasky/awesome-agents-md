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

  python evals/benchmark/run.py --selftest          scorers only, no agent, no spend
  python evals/benchmark/run.py --repeats 3 --budget 20
  python evals/benchmark/run.py --resume <run dir>
"""

from __future__ import annotations

import argparse
import concurrent.futures
import importlib.util
import json
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


def import_coding_tasks():
    spec = importlib.util.spec_from_file_location("coding_tasks", BENCH / "coding_tasks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TASKS


class Job:
    """One task, whichever family it comes from, behind one interface."""

    def __init__(self, name: str, kind: str, turns: list[str], module=None, spec=None):
        self.name, self.kind, self.turns = name, kind, turns
        self.module, self.spec = module, spec
        self.ENV = getattr(module, "ENV", {}) if module else {}

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
        probe = ("import json, pathlib, sys; sys.path.insert(0, sys.argv[1]); import coding_tasks; "
                 "print(json.dumps(coding_tasks.TASKS[sys.argv[2]]['score'](pathlib.Path(sys.argv[3]))))")
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


def load_jobs(names: list[str]) -> list[Job]:
    jobs = [Job(name, "coding", [spec["prompt"]], spec=spec)
            for name, spec in import_coding_tasks().items()]
    jobs += [Job(task.NAME, "trap", getattr(task, "TURNS", None) or [task.PROMPT], module=task)
             for task in load_tasks([])]
    return [job for job in jobs if not names or job.name in names]


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
        row["unasked_commit"] = row["task"] != "commit_trailer" and any(
            COMMIT_RUN.search(command) for command in shell_commands(events))


def summarize(rows: list[dict], arms: list[str]) -> None:
    def mean(values):
        values = [v for v in values if v is not None]
        return sum(values) / len(values) if values else None

    def fmt(value, pattern):
        return "n/a" if value is None else pattern.format(value)

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

    print(f"\n{'task':<18}" + "".join(f"{arm[:14]:>15}" for arm in arms))
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
        print(f"{task:<18}" + "".join(f"{cell:>15}" for cell in cells))


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
        rows = json.loads((args.summary / "summary.json").read_text(encoding="utf-8"))
        fill_reply_metrics(rows, args.summary)
        summarize(rows, arms)
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
             for job in load_jobs(args.tasks) for arm in arms
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
