# Awesome AGENTS.md

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Web Reactions](https://api.webreactions.app/badge/github/khasky/awesome-agents-md.svg)](https://webreactions.app/?utm_source=github&utm_channel=repository&utm_medium=awesome-agents-md)

One `AGENTS.md` to import, with shared rules for AI coding agents: Claude Code, OpenAI Codex CLI, Gemini CLI, Cursor Agent — plus optional rule modules in `rules/` that load on demand. Clone once, import it globally into every agent you use.

The always-loaded core covers: concise token-efficient communication, a "lazy senior dev" coding discipline (smallest correct diff, no speculative abstractions), a hard verification gate before any "done" claim, debug escalation, Conventional Commits. On-demand modules in `rules/` extend it across the stack — backend security, databases, caching, resilience, deployment, infrastructure as code, payments, and more.

No hard dependencies and nothing tool-specific. The ruleset is framework- and project-agnostic — it holds for any stack and any of the four agents, with nothing extra to install. Agent tooling lives in sibling repos: [agent-mcp-integrations](https://github.com/khasky/agent-mcp-integrations) for the MCP integration servers (browsers, cloud, databases, infra, domain APIs) and [claude-code-token-optimization](https://github.com/khasky/claude-code-token-optimization) for the token-efficiency layers (LSP, `codebase-memory-mcp`, ast-grep, Context7, Caveman, Ponytail).

## Contents

- [Awesome AGENTS.md](#awesome-agentsmd)
  - [Contents](#contents)
  - [Repository layout](#repository-layout)
  - [Prerequisites](#prerequisites)
  - [Install](#install)
    - [Claude Code](#claude-code)
    - [OpenAI Codex CLI](#openai-codex-cli)
    - [Gemini CLI](#gemini-cli)
    - [Cursor](#cursor)
    - [Per-project alternative (any agent)](#per-project-alternative-any-agent)
  - [Loaded-rules canary](#loaded-rules-canary)
  - [Related](#related)
  - [Contributing](#contributing)
  - [License](#license)

## Repository layout

```text
AGENTS.md    # the core ruleset — always loaded, kept under 200 lines (CI-enforced)
rules/       # on-demand modules, read only when the task matches — the full list
             # with trigger conditions is the last section of AGENTS.md, and CI
             # fails if a module there is missing or a module here is unlisted
README.md    # setup and optional tooling (this file)
llms.txt     # index of the core and every module for LLM consumption —
             # CI keeps it two-way synced with rules/
```

The core is self-sufficient. Agents read `rules/*.md` only when the task matches (editing Markdown, styling UI, a dedicated refactor, …) and skip them if the clone can't be located — so importing the single `AGENTS.md` is always enough.

The 200-line cap is not cosmetic: frontier models follow roughly 150–200 instructions reliably, and the agent's own system prompt already spends ~50 of them. Everything past that budget degrades adherence to the rules that matter.

## Prerequisites

At minimum you need git and one of the agents. Windows one-liners (skip what you already have):

```powershell
winget install -e --id Git.Git
winget install -e --id OpenJS.NodeJS.LTS   # npx — required by Gemini CLI
```

The agents themselves:

```powershell
winget install -e --id Anthropic.ClaudeCode
$env:CODEX_NON_INTERACTIVE = "1"; irm https://chatgpt.com/codex/install.ps1 | iex
npm install -g @google/gemini-cli
```

Cursor: download from [cursor.com](https://cursor.com).

## Install

```powershell
git clone https://github.com/khasky/awesome-agents-md.git
```

Examples below assume the clone lives at `C:\repos\awesome-agents-md` (Windows) or `~/repos/awesome-agents-md` (macOS/Linux) — adjust the path to yours.

Each agent has a global instructions file. Add one import line to it (create the file if it does not exist). Keep those files thin — all rules live in the shared `AGENTS.md`.

### Claude Code

`%USERPROFILE%\.claude\CLAUDE.md` (macOS/Linux: `~/.claude/CLAUDE.md`):

```markdown
@C:/repos/awesome-agents-md/AGENTS.md
```

Claude Code resolves `@path` imports natively; forward slashes work on Windows. Approve the import when prompted.

Verify inside Claude Code: run `/memory` — the imported `AGENTS.md` should be listed.

Optional but recommended: `"includeCoAuthoredBy": false` in `%USERPROFILE%\.claude\settings.json` stops Claude Code from appending its default `Co-Authored-By` trailer — a mechanical backstop for the ruleset's no-AI-traces commit rule.

### OpenAI Codex CLI

`%USERPROFILE%\.codex\AGENTS.md` (macOS/Linux: `~/.codex/AGENTS.md`):

```markdown
@C:/repos/awesome-agents-md/AGENTS.md
```

Codex loads the global `AGENTS.md` and follows the reference to the shared file. If you prefer zero indirection, paste the full contents of `AGENTS.md` into that file instead.

Verify:

```powershell
codex "Which instruction files did you load? Do not modify anything."
```

### Gemini CLI

`%USERPROFILE%\.gemini\GEMINI.md` (macOS/Linux: `~/.gemini/GEMINI.md`):

```markdown
@C:/repos/awesome-agents-md/AGENTS.md
```

Gemini CLI supports `@file` imports in `GEMINI.md` natively.

Verify inside Gemini CLI: `/memory show`. After editing the files: `/memory refresh`.

### Cursor

Cursor has no global markdown import. Two options:

- Per project: copy `AGENTS.md` into the project root — Cursor Agent reads it.
- Globally: paste the contents of `AGENTS.md` into Cursor Settings → Rules → User Rules.

### Per-project alternative (any agent)

Copy `AGENTS.md` into a repository root. Codex and Claude Code pick up a project-level `AGENTS.md` automatically. For Gemini CLI, add it to the recognized context files in `~/.gemini/settings.json`:

```json
{ "contextFileName": ["GEMINI.md", "AGENTS.md"] }
```

## Loaded-rules canary

The first rule in `AGENTS.md` makes the agent end every response with `✓ awesome-agents-md`. That is deliberate: if you see the marker, the import chain works. Once confirmed (or if you find it noisy), delete that line in your clone.

Beyond the canary: in Claude Code, `/context` confirms the file is actually loaded and `/doctor` suggests trims; a model-agnostic check is prompting "Summarize the instructions you loaded." If a specific rule keeps being ignored, the usual cause is file length — prune before rephrasing.

## Related

Three guides, one split — pick the layer you need:

- **Awesome Agents MD** — *this repo:* the base, tool-agnostic ruleset every agent imports (one `AGENTS.md`). Start here; the layers below are optional on top.
- [Awesome Agent Skills](https://github.com/khasky/awesome-agent-skills) — portable `SKILL.md` skills every agent loads: code review, debugging, security and leak audits, code and text cleanup.
- [Agent MCP Integrations](https://github.com/khasky/agent-mcp-integrations) — MCP servers that connect agents to browsers, cloud, databases, infra, and domain APIs.
- [Claude Code Token Optimization](https://github.com/khasky/claude-code-token-optimization) — the token-efficiency layer (LSP, `codebase-memory-mcp`, ast-grep, Context7, Caveman, Ponytail).
- [Claude Code Security Audit](https://github.com/khasky/claude-code-security-audit) — the layered security-audit workflow (deep audit, continuous guardrails, scanners).

**A rule or a skill?** A rule is a standing constraint the agent honors without being asked; a skill is a procedure you invoke, with phases and an output contract. The two layers overlap on purpose: `rules/code-review.md` here sets the bar every review must meet, and the `awesome-code-review` skill runs the review and produces the report. Install both — rules keep everyday work in line, skills handle the jobs you name.

## Contributing

A rule earns its line only if an agent would get it wrong without it, and the core `AGENTS.md` stays under 200 lines — see [CONTRIBUTING.md](CONTRIBUTING.md) for the format of a new `rules/` module and the checks CI runs.

## License

Released under the [MIT license](LICENSE). `AGENTS.md` adapts MIT-licensed material from two projects — [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (output compression) and [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (lazy senior dev mode) — with credit kept inline where each is used.
