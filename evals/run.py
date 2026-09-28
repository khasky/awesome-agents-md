#!/usr/bin/env python3
"""Runs each eval task through headless Claude Code with and without AGENTS.md.

Every run gets a fresh fixture repository in a temp directory, the agent's
stream-json transcript is saved outside the repository (--out), and the task's own score()
reads the transcript and the repository the agent left behind. A task with TURNS
instead of PROMPT is a scenario: one session, resumed for every turn, where a
"/compact" turn compacts it.
"""

from __future__ import annotations

import argparse
import getpass
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "tasks"))

from _fixture import remove_tree  # noqa: E402

EVALS = pathlib.Path(__file__).resolve().parent
CORE = EVALS.parent / "AGENTS.md"
# Run results stay out of the repository: transcripts are large, machine-specific
# and dated, and the repository ships the harness only.
DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "awesome-agents-md-evals"
VARIANTS = ("without", "with", "import", "plugin")
# Pinned so that two runs compare the ruleset, not whatever the CLI's default
# model was that week. --model overrides it and the run directory records it.
DEFAULT_MODEL = "claude-sonnet-5"
# A runaway attempt stops here instead of draining the run's budget.
CALL_BUDGET_USD = 1.0

# What the agent process inherits. Everything else in the owner's environment
# stays out, because a task that tempts the agent to print the environment must
# not put real credentials into a transcript that gets published.
INHERITED_ENV = {
    "PATH", "PATHEXT", "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR", "COMSPEC", "TEMP", "TMP",
    "TMPDIR", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "HOME", "APPDATA", "LOCALAPPDATA",
    "PROGRAMDATA", "PROGRAMFILES", "PROGRAMFILES(X86)", "PROGRAMW6432", "COMMONPROGRAMFILES",
    "NUMBER_OF_PROCESSORS", "OS", "PROCESSOR_ARCHITECTURE", "USERNAME", "USER", "LOGNAME",
    "LANG", "LC_ALL", "TERM", "SHELL", "CLAUDE_CODE_GIT_BASH_PATH",
    "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
}


def agent_env(task) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key.upper() in INHERITED_ENV}
    env.update(getattr(task, "ENV", {}))
    return env


def load_tasks(names: list[str]) -> list:
    tasks = []
    for path in sorted((EVALS / "tasks").glob("[!_]*.py")):
        if names and path.stem not in names:
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.NAME = path.stem
        tasks.append(module)
    return tasks


def agent_command(claude: str, variant: str, prompt: str, model: str, call_budget: float,
                  session: tuple[str, str] | None = None) -> list[str]:
    # Neither variant may inherit the machine owner's setup: user-level settings
    # (plugins, hooks) are left out, and the global CLAUDE.md, which
    # --setting-sources alone still loads, is excluded by path. The "with"
    # variant then gets the core as an appended system prompt and nothing else;
    # "import" finds it as a CLAUDE.md in the fixture's parent directory, the
    # channel an @import in a global CLAUDE.md uses; "plugin" loads this
    # repository as a plugin, with the SessionStart hook and both guard hooks.
    # The plugin's Stop hook reads the session transcript, and a scenario
    # resumes its session every turn, so only those keep session persistence on.
    # session is ("--session-id", id) for a scenario's first turn and
    # ("--resume", id) for the rest.
    global_memory = (pathlib.Path.home() / ".claude" / "CLAUDE.md").as_posix()
    isolation = json.dumps({"claudeMdExcludes": [global_memory, "**/.claude/CLAUDE.md"]})
    command = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--setting-sources", "project,local", "--settings", isolation,
               "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "PowerShell",
               "--model", model, "--max-budget-usd", str(call_budget)]
    if session:
        command += list(session)
    elif variant != "plugin":
        command.append("--no-session-persistence")
    if variant == "with":
        command += ["--append-system-prompt-file", str(CORE)]
    elif variant == "plugin":
        command += ["--plugin-dir", str(CORE.parent)]
    return command


def read_events(transcript: str) -> list[dict]:
    events = []
    for line in transcript.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def path_spellings(path: pathlib.Path) -> set[str]:
    """How one directory shows up in a transcript: native, forward slashes,
    JSON-escaped, the Git Bash /c/... form, and with the separators gone, which
    is what an unquoted Windows path looks like after bash strips backslashes."""
    native = str(path)
    forms = {native, path.as_posix(), native.replace("\\", "\\\\"), native.replace("\\", "")}
    if path.drive:
        forms.add("/" + path.drive[0].lower() + path.as_posix()[len(path.drive):])
        forms |= {form[0].swapcase() + form[1:] for form in list(forms) if form[1:2] == ":"}
    return forms


def redact(transcript: str, scratch: pathlib.Path) -> str:
    # Transcripts are meant to be published, so the machine's paths and user
    # name are replaced, and the init event, which lists the local setup
    # (skills, MCP servers, pipe names), is dropped; its model and version go to
    # the summary instead.
    lines = [line for line in transcript.splitlines()
             if '"subtype":"init"' not in line.replace(" ", "")]
    text = "\n".join(lines)
    replacements = [(form, "<scratch>") for form in path_spellings(scratch)]
    replacements += [(form, "<home>") for form in path_spellings(pathlib.Path.home())]
    for form, label in sorted(replacements, key=lambda pair: -len(pair[0])):
        text = text.replace(form, label)
    user = getpass.getuser()
    text = re.sub(rf"(?<![A-Za-z0-9]){re.escape(user)}(?![A-Za-z0-9])", "<user>", text,
                  flags=re.IGNORECASE)
    return text


def run_agent(command: list[str], workdir: pathlib.Path, env: dict[str, str]) -> tuple[str, int]:
    try:
        run = subprocess.run(command, cwd=workdir, env=env, capture_output=True, text=True,
                             encoding="utf-8", timeout=900)
        return run.stdout, run.returncode
    except subprocess.TimeoutExpired as expired:
        stdout = expired.stdout or b""
        return stdout if isinstance(stdout, str) else stdout.decode("utf-8", "replace"), -1


def total(results: list[dict], read) -> int | float | None:
    # None, not 0, when no turn reported the number: a missing cost is unknown,
    # and averaging it as free would flatter the variant that lost it.
    values = [read(result) for result in results]
    values = [value for value in values if value is not None]
    return sum(values) if values else None


def run_once(claude: str, task, variant: str, model: str, call_budget: float,
             run_dir: pathlib.Path, repeat: int) -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"eval-{task.NAME}-"))
    turns = getattr(task, "TURNS", None) or [task.PROMPT]
    session_id = str(uuid.uuid4()) if len(turns) > 1 else None
    try:
        workdir = scratch / "repo"
        task.setup(workdir)
        if variant == "import":
            (scratch / "CLAUDE.md").write_text(CORE.read_text(encoding="utf-8"), encoding="utf-8")
        started = time.monotonic()
        stdout, exit_code = "", 0
        for index, prompt in enumerate(turns):
            if index and hasattr(task, "between_turns"):
                task.between_turns(workdir, index)
            session = None if not session_id else (
                ("--session-id" if index == 0 else "--resume"), session_id)
            # A marker line per turn, so a scenario's score can tell which turn
            # a tool call belongs to.
            if session_id:
                stdout += json.dumps({"type": "eval_turn", "turn": index, "prompt": prompt}) + "\n"
            out_text, exit_code = run_agent(
                agent_command(claude, variant, prompt, model, call_budget, session),
                workdir, agent_env(task))
            stdout += out_text if out_text.endswith("\n") or not out_text else out_text + "\n"
            if exit_code:
                break
        seconds = round(time.monotonic() - started)
        out = run_dir / f"{task.NAME}.{variant}.{repeat}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(redact(stdout, scratch), encoding="utf-8")
        events = read_events(stdout)
        init = next((e for e in events if e.get("subtype") == "init"), {})
        results = [e for e in events if e.get("type") == "result"]
        score = task.score(workdir, events)
    finally:
        remove_tree(scratch)
        # The saved session, named after the working directory.
        session_dir = pathlib.Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(workdir))
        if "eval-" in session_dir.name and session_dir.is_dir():
            remove_tree(session_dir)
    return {
        "task": task.NAME, "variant": variant, "repeat": repeat,
        "model": init.get("model"), "claude_code": init.get("claude_code_version"),
        "passed": score["passed"], "detail": score["detail"],
        "input_tokens": total(results, lambda r: None if "usage" not in r else
                              r["usage"].get("input_tokens", 0)
                              + r["usage"].get("cache_creation_input_tokens", 0)
                              + r["usage"].get("cache_read_input_tokens", 0)),
        "output_tokens": total(results, lambda r: r.get("usage", {}).get("output_tokens")),
        "cost_usd": total(results, lambda r: r.get("total_cost_usd")), "seconds": seconds,
        "turns": len(turns), "agent_exit": exit_code, "transcript": out.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", help="task names (default: all)")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"model for every attempt (default: {DEFAULT_MODEL})")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT,
                        help=f"directory for run results (default: {DEFAULT_OUT})")
    parser.add_argument("--variants", default="without,with",
                        help=f"comma-separated subset of {','.join(VARIANTS)}")
    parser.add_argument("--call-budget", type=float, default=CALL_BUDGET_USD,
                        help=f"USD cap per agent call, passed as --max-budget-usd "
                             f"(default: {CALL_BUDGET_USD})")
    parser.add_argument("--budget", type=float,
                        help="USD cap for the whole run: no new attempt starts past it")
    parser.add_argument("--resume", type=pathlib.Path, metavar="RUN_DIR",
                        help="continue an interrupted run: attempts already in its "
                             "summary.json are skipped")
    args = parser.parse_args()
    variants = args.variants.split(",")
    if not set(variants) <= set(VARIANTS):
        parser.error(f"unknown variant in {args.variants}")

    claude = shutil.which("claude")
    if not claude:
        print("claude not found on PATH", file=sys.stderr)
        return 1
    if args.resume:
        run_dir = args.resume.resolve()
        rows = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        models = {row["model"] for row in rows if row.get("model")}
        if models and not any(args.model in model for model in models):
            parser.error(f"{run_dir} was run on {', '.join(sorted(models))}, not {args.model}")
    else:
        run_dir = args.out.resolve() / f"{time.strftime('%Y%m%d-%H%M%S')}-{args.model}"
        rows = []
    if EVALS.parent in run_dir.parents:
        parser.error("--out points inside the repository; results are kept outside it")
    done = {(row["task"], row["variant"], row["repeat"]) for row in rows}
    spent = sum(row.get("cost_usd") or 0 for row in rows)
    stopped = False
    for task in load_tasks(args.tasks):
        for repeat in range(1, args.repeats + 1):
            for variant in variants:
                if (task.NAME, variant, repeat) in done:
                    continue
                if args.budget is not None and spent >= args.budget:
                    stopped = True
                    break
                row = run_once(claude, task, variant, args.model, args.call_budget, run_dir, repeat)
                rows.append(row)
                spent += row["cost_usd"] or 0
                print(f"{row['task']:<18} {variant:<8} #{repeat}  "
                      f"{'PASS' if row['passed'] else 'FAIL'}  {row['detail']}", flush=True)
                # Rewritten after every attempt, so a crash or an interrupt
                # keeps the runs already paid for, and --resume picks up there.
                (run_dir / "summary.json").write_text(json.dumps(rows, indent=2),
                                                      encoding="utf-8")

    print(f"\n{'task':<18} {'variant':<8} {'passed':>7} {'avg input tokens':>17} {'avg cost':>9}")
    for task in sorted({r["task"] for r in rows}):
        for variant in variants:
            runs = [r for r in rows if r["task"] == task and r["variant"] == variant]
            if not runs:
                continue
            passed = sum(r["passed"] for r in runs)
            tokens = [r["input_tokens"] for r in runs if r["input_tokens"] is not None]
            costs = [r["cost_usd"] for r in runs if r["cost_usd"] is not None]
            avg_tokens = str(sum(tokens) // len(tokens)) if tokens else "n/a"
            avg_cost = f"${sum(costs) / len(costs):.3f}" if costs else "n/a"
            print(f"{task:<18} {variant:<8} {passed:>3}/{len(runs):<3} {avg_tokens:>17} {avg_cost:>9}")
    if stopped:
        print(f"\nstopped at the ${args.budget:.2f} budget after ${spent:.2f}; "
              f"continue with --resume {run_dir}")
    print(f"\ntranscripts and summary.json: {run_dir}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
