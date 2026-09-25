#!/usr/bin/env python3
"""Every gate this repository enforces, in one place.

CI and the pre-commit hook both run this file, so a check cannot pass locally
and fail on the server. Python rather than shell because the hook runs on
whatever machine the contributor is sitting at.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

CORE = "AGENTS.md"
CORE_LINE_LIMIT = 200
CORE_BYTE_LIMIT = 32 * 1024
INDEX_HEADING = "## On-demand rule modules"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def tracked_markdown() -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    return out.split()


def modules() -> list[str]:
    return sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "rules").glob("*.md"))


def strip_comments(line: str) -> str:
    return re.sub(r"<!--.*-->", "", line)


def core_under_line_limit() -> list[str]:
    # The cap is an instruction budget: models follow roughly 150-200
    # instructions reliably, and the module index below the heading is a lookup
    # table, one clause per module, not an instruction. A core that lost the
    # heading has no index, so the whole file counts.
    sections = read(CORE).split(f"\n{INDEX_HEADING}", 1)
    lines = sections[0].rstrip("\n").count("\n") + 1
    if lines <= CORE_LINE_LIMIT:
        return []
    return [f"{CORE}: {lines} instruction lines above the module index, "
            f"{lines - CORE_LINE_LIMIT} over the {CORE_LINE_LIMIT}-line cap"]


def core_under_byte_limit() -> list[str]:
    # Codex reads project instructions up to its default project_doc_max_bytes
    # and truncates the rest without a warning, index included. A Windows
    # checkout with CRLF line endings is the largest form the file takes, so
    # that is the size counted, whatever this checkout uses.
    text = (ROOT / CORE).read_bytes().replace(b"\r\n", b"\n")
    size = len(text) + text.count(b"\n")
    if size <= CORE_BYTE_LIMIT:
        return []
    return [f"{CORE}: {size} bytes, {size - CORE_BYTE_LIMIT} over the "
            f"{CORE_BYTE_LIMIT}-byte cap"]


def markdown_has_no_ellipsis_glyph() -> list[str]:
    return [f"{source}:{number}: ellipsis glyph, write three plain dots"
            for source in tracked_markdown()
            for number, line in enumerate(read(source).splitlines(), 1)
            if "…" in line]


# Everything from the module index down is trigger text - that is where tool
# names belong. gitleaks and commitlint are absent from the list on purpose:
# both appear inside an explicit presence check, which CONTRIBUTING allows.
CORE_TOOLS = (r"ripgrep|rg --no-ignore|npm|pnpm|yarn|npx|vitest|jest|playwright|prisma|"
              r"drizzle|zod|eslint|prettier|biome|webpack|django|rails|pytest|ponytail")


def core_names_no_tool() -> list[str]:
    core = re.split(rf"^{re.escape(INDEX_HEADING)}", read(CORE), flags=re.M)[0]
    found = []
    for number, line in enumerate(core.splitlines(), 1):
        for hit in re.findall(rf"\b({CORE_TOOLS})\b", strip_comments(line), re.I):
            found.append(f"{CORE}:{number}: {hit} is named outside a presence check")
    return found


# CONTRIBUTING's stack-agnostic tests, mechanized over every module, trigger
# lines included: no module is gated on a stack. A blocklisted name passes only
# on a line marked as an example (e.g. / or equivalent), or on a line that
# names two or more ecosystems side by side, which gives the advice across
# ecosystems. Curated like the core blocklist: a name that belongs elsewhere
# joins the exception filters here, never waved through.
ECOSYSTEMS = {
    "js": r"TypeScript|Node\.js|npm|pnpm|yarn|npx",
    "python": r"Python|pip|PyPI|uvx|pipx",
    "jvm": r"JVM|Java|Kotlin|Maven|Gradle",
    "ruby": r"Ruby|RubyGems",
    "php": r"PHP|Composer",
    "rust": r"Rust|Cargo",
    "go": r"Go modules",
    "dotnet": r"\.NET|NuGet",
}
STACK_NAMES = (r"Next\.js|Nuxt|React|Vue|Angular|Svelte|Zustand|Pinia|TanStack|SWR|Redis|"
               r"Prisma|Drizzle|husky|lint-staged|Turborepo|Kubernetes|Dockerfile|Docker|"
               r"Terraform|Pulumi|Vitest|Jest|Playwright|Express|Fastify|Stripe|"
               r"GitHub Actions|PostgreSQL|Postgres|SQLite|MySQL|JSX|"
               r"TypeScript|Node\.js|npm|pnpm|yarn|npx|Python|JVM|Java|Kotlin|Ruby|PHP|Rust|\.NET")
STACK_EXAMPLE_MARKERS = re.compile(r"e\.g\.|equivalent")


def names_several_ecosystems(line: str) -> bool:
    return sum(1 for names in ECOSYSTEMS.values()
               if re.search(rf"(?<![\w.])({names})\b", line)) >= 2


def module_descriptions() -> list[tuple[str, int, str]]:
    # Every place a module is described: its own file, its entry in the core
    # index, and its entry in llms.txt. The core above the index has its own
    # gate, so its lines start the count without being scanned.
    lines = [(path, number, raw) for path in modules()
             for number, raw in enumerate(read(path).splitlines(), 1)]
    core = read(CORE).splitlines()
    index_start = next((i for i, line in enumerate(core) if line.startswith(INDEX_HEADING)),
                       len(core))
    lines += [(CORE, number, raw)
              for number, raw in enumerate(core[index_start:], index_start + 1)]
    lines += [("llms.txt", number, raw)
              for number, raw in enumerate(read("llms.txt").splitlines(), 1)]
    return lines


def modules_name_no_stack() -> list[str]:
    found = []
    for path, number, raw in module_descriptions():
        line = strip_comments(raw)
        if STACK_EXAMPLE_MARKERS.search(line) or names_several_ecosystems(line):
            continue
        for hit in re.findall(rf"\b({STACK_NAMES})\b", line):
            found.append(f"{path}:{number}: {hit} is named outside a marked example "
                         "or a cross-ecosystem line")
    return found


def modules_listed_in_index() -> list[str]:
    # Scoped to the index section: a module referenced only in the body of the
    # core is still unlisted for a reader scanning the index. A core that lost
    # the heading has no index at all, so every module is an orphan.
    sections = read(CORE).split(INDEX_HEADING, 1)
    index = sections[1] if len(sections) == 2 else ""
    return [f"orphan: {path} is not in the On-demand module index of {CORE}"
            for path in modules() if path not in index]


def modules_open_with_trigger() -> list[str]:
    return [f"{path}: missing 'Read this when' trigger line in the first 5 lines"
            for path in modules()
            if not any(line.startswith("Read this when ")
                       for line in read(path).splitlines()[:5])]


def llms_in_sync() -> list[str]:
    llms = read("llms.txt")
    found = [f"missing from llms.txt: {path}" for path in modules() if path not in llms]
    for path in sorted(set(re.findall(r"rules/[a-z0-9-]+\.md", llms))):
        if not (ROOT / path).is_file():
            found.append(f"stale llms.txt entry: {path}")
    return found


def llms_links_exist() -> list[str]:
    # llms.txt uses absolute URLs by spec, so the relative-link gate never sees
    # it; map each blob URL back to a repository path instead.
    return [f"llms.txt links to a missing file: {path}"
            for path in sorted(set(re.findall(r"blob/main/([^)]+)", read("llms.txt"))))
            if not (ROOT / path).is_file()]


def referenced_modules_exist() -> list[str]:
    referenced = set()
    for source in tracked_markdown():
        referenced.update(re.findall(r"rules/[a-z0-9-]+\.md", read(source)))
    return [f"dangling reference: {path}" for path in sorted(referenced)
            if not (ROOT / path).is_file()]


def relative_links_resolve() -> list[str]:
    found = []
    for source in tracked_markdown():
        directory = (ROOT / source).parent
        for target in re.findall(r"\]\(([^)]+)\)", read(source)):
            target = target.split("#", 1)[0]
            if not target or target.startswith(("http", "mailto:")):
                continue
            if not (directory / target).exists():
                found.append(f"{source}: broken link -> {target}")
    return found


def code_fences_balanced() -> list[str]:
    found = []
    for source in tracked_markdown():
        fences = sum(1 for line in read(source).splitlines() if line.startswith("```"))
        if fences % 2:
            found.append(f"{source}: unbalanced code fences ({fences})")
    return found


# The ruleset obeys the rule it publishes. The blocklist is read out of
# rules/markdown.md rather than copied here, so adding a phrase there extends
# this gate in the same edit and no second list can drift. markdown.md itself
# is skipped: there the phrases are the list.
#
# Conditional entries a literal search cannot decide: the bans that hold only
# for the figurative sense, and "complete", which markdown.md names as the
# recommended replacement. They stay review checks. Curated like the blocklists
# above: a phrase joins this set only when a search genuinely cannot rule on
# it, never to wave a hit through.
CONDITIONAL = {"navigate", "landscape", "realm", "leverage", "complete"}


def prose_obeys_markdown_rules() -> list[str]:
    source = read("rules/markdown.md")
    block = source.split("Avoid these patterns unless the document's house style requires them:")[1]
    phrases = []
    for line in block.splitlines():
        # The blocklist ends at the first prose line after it - the carve-out
        # block below it is bullets too, and its quoted text names phrases
        # rather than banning them.
        if not line.startswith("- "):
            if line.strip():
                break
            continue
        phrases += [p for p in re.findall(r'"([^"]+)"', line)
                    if p.lower() not in CONDITIONAL and "X but also Y" not in p]
    if not phrases:
        return ["no phrases parsed out of rules/markdown.md - the list moved or changed shape"]

    # markdown.md exempts quoted examples and cited text, so the gate reads
    # prose only: source-citation comments, fences, inline code and quoted
    # spans are where a banned phrase is named rather than used.
    def prose(text: str) -> str:
        text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        text = re.sub(r"```.*?```", " ", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", " ", text)
        return re.sub(r"\"[^\"\n]*\"", " ", text)

    found = []
    for path in tracked_markdown():
        if path == "rules/markdown.md":
            continue
        for number, line in enumerate(prose(read(path)).splitlines(), 1):
            for phrase in phrases:
                if re.search(rf"(?<!\w){re.escape(phrase)}", line, re.I):
                    found.append(f"{path}:{number}: {phrase!r} is on this repo's own blocklist")
            if re.search(r"not only\b.{0,80}?\bbut also\b", line, re.I):
                found.append(f"{path}:{number}: 'not only X but also Y' is on this repo's own blocklist")
    return found


def plugin_manifests_resolve() -> list[str]:
    # The plugin is the Claude Code install path that needs no clone: a
    # SessionStart hook prints the core into the session. Nothing in a session
    # fails loudly when that hook names a file that moved - the ruleset just
    # goes missing - so the gate is that the manifests agree with each other and
    # that every plugin-root path the hook reads still exists.
    manifests = ROOT / ".claude-plugin"
    plugin = json.loads((manifests / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((manifests / "marketplace.json").read_text(encoding="utf-8"))
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    found = []
    if plugin.get("name") != "awesome-agents-md":
        found.append(f"plugin.json name is {plugin.get('name')!r}")
    entries = [p.get("name") for p in market.get("plugins", [])]
    if entries != [plugin.get("name")]:
        found.append(f"marketplace.json lists {entries}, expected [{plugin.get('name')!r}]")
    for key in ("description", "license"):
        if not plugin.get(key):
            found.append(f"plugin.json is missing {key}")
    # version is omitted on purpose: Claude Code then tracks the commit and
    # every push reaches installed users, with no bump to forget.
    if "version" in plugin:
        found.append("plugin.json pins a version - installed users then stay on it until the next bump")

    commands = [hook.get("command", "")
                for event in hooks.get("hooks", {}).values()
                for group in event for hook in group.get("hooks", [])]
    if not any(CORE in command for command in commands):
        found.append(f"no hook reads {CORE} - an installed plugin would load nothing")
    # Trailing punctuation belongs to the sentence the hook prints, not to the
    # path: "${CLAUDE_PLUGIN_ROOT}/rules/." names rules/.
    referenced = {match.rstrip("./") for match in
                  re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9._/-]+)", " ".join(commands))}
    for path in sorted(referenced):
        if not (ROOT / path).exists():
            found.append(f"hooks/hooks.json reads {path}, which is not in the repository")
    return found


GATES = [
    (f"core {CORE} stays under {CORE_LINE_LIMIT} instruction lines", core_under_line_limit),
    (f"core {CORE} stays under {CORE_BYTE_LIMIT} bytes", core_under_byte_limit),
    ("Markdown carries no ellipsis glyph", markdown_has_no_ellipsis_glyph),
    (f"core {CORE} names no framework, library, or non-baseline CLI", core_names_no_tool),
    ("modules name stacks only as marked examples or across ecosystems",
     modules_name_no_stack),
    (f"every rules module is listed in the {CORE} module index", modules_listed_in_index),
    ("every rules module opens with its trigger line", modules_open_with_trigger),
    ("llms.txt stays in sync with rules/", llms_in_sync),
    ("llms.txt links point at files that exist", llms_links_exist),
    ("every referenced rules module exists", referenced_modules_exist),
    ("relative links resolve", relative_links_resolve),
    ("code fences are balanced", code_fences_balanced),
    ("the repo's own prose obeys rules/markdown.md", prose_obeys_markdown_rules),
    ("plugin manifests and the SessionStart hook still resolve", plugin_manifests_resolve),
]


def main() -> int:
    failed = 0
    for title, gate in GATES:
        # A file malformed enough to crash one gate would otherwise hide the
        # verdict of every gate after it.
        try:
            problems = gate()
        except Exception as error:
            problems = [f"the check itself crashed: {error!r}"]
        if not problems:
            continue
        failed += 1
        print(f"FAIL  {title}")
        for problem in problems:
            print(f"      {problem}")
    if failed:
        print(f"\n{failed} of {len(GATES)} gates failed", file=sys.stderr)
        return 1
    print(f"all {len(GATES)} gates pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
