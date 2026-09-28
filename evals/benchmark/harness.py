"""Shared pieces of the benchmark harness: which environment an agent inherits,
how task modules load, and how a transcript is read and redacted before it is
written anywhere."""

from __future__ import annotations

import getpass
import importlib.util
import json
import os
import pathlib
import re
import subprocess

EVALS = pathlib.Path(__file__).resolve().parent.parent
# Pinned so that two runs compare the rulesets, not whatever the CLI's default
# model was that week. --model overrides it and the run directory records it.
DEFAULT_MODEL = "claude-sonnet-5"

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
