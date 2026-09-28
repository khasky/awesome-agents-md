#!/usr/bin/env python3
"""Runs each eval task through headless Claude Code with and without AGENTS.md.

Every run gets a fresh fixture repository in a temp directory, the agent's
stream-json transcript is saved outside the repository (--out), and the task's own score()
reads the transcript and the repository the agent left behind.
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "tasks"))

from _fixture import remove_tree  # noqa: E402

EVALS = pathlib.Path(__file__).resolve().parent
CORE = EVALS.parent / "AGENTS.md"
# Run results stay out of the repository: transcripts are large, machine-specific
# and dated, and the repository ships the harness only.
DEFAULT_OUT = pathlib.Path(tempfile.gettempdir()) / "awesome-agents-md-evals"
VARIANTS = ("without", "with", "import", "plugin")

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


def agent_command(claude: str, variant: str, prompt: str, model: str | None) -> list[str]:
    # Neither variant may inherit the machine owner's setup: user-level settings
    # (plugins, hooks) are left out, and the global CLAUDE.md, which
    # --setting-sources alone still loads, is excluded by path. The "with"
    # variant then gets the core as an appended system prompt and nothing else;
    # "import" finds it as a CLAUDE.md in the fixture's parent directory, the
    # channel an @import in a global CLAUDE.md uses; "plugin" loads this
    # repository as a plugin, with the SessionStart hook and both guard hooks.
    # The plugin's Stop hook reads the session transcript, so only that variant
    # keeps session persistence on.
    global_memory = (pathlib.Path.home() / ".claude" / "CLAUDE.md").as_posix()
    isolation = json.dumps({"claudeMdExcludes": [global_memory, "**/.claude/CLAUDE.md"]})
    command = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose",
               "--setting-sources", "project,local", "--settings", isolation,
               "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "PowerShell"]
    if variant != "plugin":
        command.append("--no-session-persistence")
    if model:
        command += ["--model", model]
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


def run_once(claude: str, task, variant: str, model: str | None, run_dir: pathlib.Path,
             repeat: int) -> dict:
    scratch = pathlib.Path(tempfile.mkdtemp(prefix=f"eval-{task.NAME}-"))
    try:
        workdir = scratch / "repo"
        task.setup(workdir)
        if variant == "import":
            (scratch / "CLAUDE.md").write_text(CORE.read_text(encoding="utf-8"), encoding="utf-8")
        started = time.monotonic()
        try:
            run = subprocess.run(agent_command(claude, variant, task.PROMPT, model), cwd=workdir,
                                 env=agent_env(task), capture_output=True, text=True,
                                 encoding="utf-8", timeout=900)
        except subprocess.TimeoutExpired as expired:
            stdout = expired.stdout or b""
            run = subprocess.CompletedProcess(expired.cmd, -1, stdout if isinstance(stdout, str)
                                              else stdout.decode("utf-8", "replace"), "")
        seconds = round(time.monotonic() - started)
        out = run_dir / f"{task.NAME}.{variant}.{repeat}.jsonl"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(redact(run.stdout, scratch), encoding="utf-8")
        events = read_events(run.stdout)
        init = next((e for e in events if e.get("subtype") == "init"), {})
        result = next((e for e in reversed(events) if e.get("type") == "result"), {})
        usage = result.get("usage", {})
        score = task.score(workdir, events)
    finally:
        remove_tree(scratch)
        # The plugin variant's saved session, named after the working directory.
        session_dir = pathlib.Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(workdir))
        if "eval-" in session_dir.name and session_dir.is_dir():
            remove_tree(session_dir)
    return {
        "task": task.NAME, "variant": variant, "repeat": repeat,
        "model": init.get("model"), "claude_code": init.get("claude_code_version"),
        "passed": score["passed"], "detail": score["detail"],
        "input_tokens": usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": result.get("total_cost_usd"), "seconds": seconds,
        "agent_exit": run.returncode, "transcript": out.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", help="task names (default: all)")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--model")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT,
                        help=f"directory for run results (default: {DEFAULT_OUT})")
    parser.add_argument("--variants", default="without,with",
                        help=f"comma-separated subset of {','.join(VARIANTS)}")
    args = parser.parse_args()
    variants = args.variants.split(",")
    if not set(variants) <= set(VARIANTS):
        parser.error(f"unknown variant in {args.variants}")

    claude = shutil.which("claude")
    if not claude:
        print("claude not found on PATH", file=sys.stderr)
        return 1
    stamp = time.strftime("%Y%m%d-%H%M%S") + (f"-{args.model}" if args.model else "")
    run_dir = args.out.resolve() / stamp
    if EVALS.parent in run_dir.parents:
        parser.error("--out points inside the repository; results are kept outside it")
    rows = []
    for task in load_tasks(args.tasks):
        for repeat in range(1, args.repeats + 1):
            for variant in variants:
                row = run_once(claude, task, variant, args.model, run_dir, repeat)
                rows.append(row)
                print(f"{row['task']:<18} {variant:<8} #{repeat}  "
                      f"{'PASS' if row['passed'] else 'FAIL'}  {row['detail']}", flush=True)
                # Rewritten after every attempt, so a crash or an interrupt
                # keeps the runs already paid for.
                (run_dir / "summary.json").write_text(json.dumps(rows, indent=2),
                                                              encoding="utf-8")

    print(f"\n{'task':<18} {'variant':<8} {'passed':>7} {'avg input tokens':>17}")
    for task in sorted({r["task"] for r in rows}):
        for variant in variants:
            runs = [r for r in rows if r["task"] == task and r["variant"] == variant]
            passed = sum(r["passed"] for r in runs)
            tokens = sum(r["input_tokens"] for r in runs) // max(len(runs), 1)
            print(f"{task:<18} {variant:<8} {passed:>3}/{len(runs):<3} {tokens:>17}")
    print(f"\ntranscripts and summary.json: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
