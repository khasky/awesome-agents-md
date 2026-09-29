"""Shared helpers for building fixture repositories and reading transcripts."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys

GIT_IDENTITY = ["-c", "user.name=Eval Fixture", "-c", "user.email=fixture@example.com"]


def git(repo: pathlib.Path, *args: str) -> str:
    return subprocess.run(["git", *GIT_IDENTITY, *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout


def set_identity(repo: pathlib.Path) -> None:
    # A commit the agent makes would otherwise carry the machine owner's global
    # git identity into the fixture and, through git log output, the transcript.
    git(repo, "config", "user.name", "Eval Fixture")
    git(repo, "config", "user.email", "fixture@example.com")
    # The machine's global core.hooksPath (a hook manager's) would run its hooks
    # on every commit the agent makes; the fixture's own hooks folder wins.
    git(repo, "config", "core.hooksPath", ".git/hooks")


def write_repo(repo: pathlib.Path, files: dict[str, str]) -> None:
    repo.mkdir(parents=True)
    git(repo, "init", "-q", "-b", "main")
    set_identity(repo)
    for name, text in files.items():
        (repo / name).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "Initial commit")


def shell_commands(events: list[dict]) -> list[str]:
    """Every shell command the agent ran, in order."""
    commands = []
    for event in events:
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") in ("Bash", "PowerShell"):
                commands.append(block.get("input", {}).get("command", ""))
    return commands


def tool_calls(events: list[dict]) -> list[tuple[str, dict, str]]:
    return [(block.get("name"), block.get("input", {}), block.get("id", ""))
            for event in events if event.get("type") == "assistant"
            for block in event.get("message", {}).get("content", [])
            if block.get("type") == "tool_use"]


def blocked_calls(events: list[dict]) -> set[str]:
    """Ids of tool calls that never ran: a hook block, a permission denial, a
    tool error. A command that ran and exited non-zero reports "Exit code N"
    and did run, which matters for a test suite that is supposed to fail."""
    blocked = set()
    for event in events:
        if event.get("type") != "user":
            continue
        for block in event.get("message", {}).get("content") or []:
            if not (isinstance(block, dict) and block.get("type") == "tool_result"
                    and block.get("is_error")):
                continue
            content = block.get("content")
            text = content if isinstance(content, str) else json.dumps(content)
            if not (text or "").startswith("Exit code"):
                blocked.add(block.get("tool_use_id"))
    return blocked


def tests_pass(repo: pathlib.Path) -> bool:
    return subprocess.run(["python", "-m", "unittest", "-q"], cwd=repo,
                          capture_output=True, text=True).returncode == 0


def remove_tree(path: pathlib.Path) -> None:
    # git marks object files read-only, and Windows refuses to delete those.
    def make_writable(delete, target, _):
        os.chmod(target, stat.S_IWRITE)
        delete(target)
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable)
    else:
        shutil.rmtree(path, onerror=make_writable)
