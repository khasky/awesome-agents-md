![Awesome AGENTS.md](.github/banner.jpg)

# Awesome AGENTS.md

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Emojery](https://api.emojery.app/badge/github/khasky/awesome-agents-md.svg)](https://emojery.app/react?t=github/khasky/awesome-agents-md)

A ruleset written in the [AGENTS.md](https://agents.md) format, with shared rules for AI coding agents: Claude Code, OpenAI Codex, Gemini, Cursor, plus optional rule modules in `rules/` that load on demand. Clone once, import it globally into every agent you use.

The always-loaded core covers: concise token-efficient communication, a coding discipline that stops at the first rung that holds (smallest correct diff, no speculative abstractions), a hard verification gate before any "done" claim, and a commit-proposal habit with no assistant traces. The procedure for larger work (assumptions, plans, the last pass before "done", debugging) loads from `rules/workflow.md` when the task calls for it, so the always-loaded part stays under 10 KB. On-demand modules in `rules/` extend it — commit messages that inherit the target repo's own convention, backend security, databases, caching, resilience, deployment and infrastructure definitions, payments, and more.

No hard dependencies and nothing tool-specific. The ruleset is framework- and project-agnostic — it holds for any stack and any of the four agents, with nothing extra to install.

## Contents

- [Awesome AGENTS.md](#awesome-agentsmd)
  - [Contents](#contents)
  - [Repository layout](#repository-layout)
  - [Prerequisites](#prerequisites)
  - [Install as a plugin](#install-as-a-plugin)
  - [Install manually (import)](#install-manually-import)
  - [How modules load](#how-modules-load)
  - [Checking that it loaded](#checking-that-it-loaded)
  - [Benchmark](#benchmark)
  - [Related](#related)
  - [Contributing](#contributing)
  - [Sources](#sources)
  - [License](#license)

## Repository layout

```text
AGENTS.md        # the core ruleset — always loaded, under 200 instruction lines and 32 KiB (CI-enforced)
rules/           # on-demand modules, read only when the task matches; rules/INDEX.md lists
                 # them with their triggers, and CI fails if a module there is missing
                 # or a module here is unlisted
README.md        # setup and optional tooling (this file)
llms.txt         # index of the core and every module for LLM consumption —
                 # CI keeps it two-way synced with rules/
hooks/           # plugin-hooks.json and load-core — the SessionStart hooks that print AGENTS.md
                 # into a Claude Code or Codex session when the repo is installed as a plugin,
                 # and guard and verify, the PreToolUse and Stop hooks that enforce what the
                 # core forbids outright; each ships as .sh (Claude Code) and .ps1 (Codex on Windows)
.claude-plugin/  # plugin.json and marketplace.json for the Claude Code plugin; Codex reads the
                 # marketplace too
.codex-plugin/   # plugin.json for the Codex plugin
gemini-extension.json  # the Gemini CLI extension: loads AGENTS.md as a context file, no hooks
qwen-extension.json    # the same for Qwen Code
scripts/         # lint.py — every gate above, run by CI and by the optional
                 # pre-commit hook that install-hooks.py sets up
evals/           # benchmark/ runs this ruleset, caveman, ponytail and i-have-adhd on the same
                 # tasks (Benchmark below); tasks/ holds the trap tasks it scores
```

The core is self-sufficient. Agents read `rules/*.md` only when the task matches (editing Markdown, styling UI, a dedicated refactor, ...) and skip them if the clone can't be located — so importing the single `AGENTS.md` is always enough.

The 200-instruction cap is not cosmetic: frontier models follow roughly 150–200 instructions reliably (measured by [IFScale](https://arxiv.org/abs/2507.11538)), and the agent's own system prompt already spends ~50 of them. Everything past that budget degrades adherence to the rules that matter. The file also stays under 32 KiB, the default `project_doc_max_bytes` past which Codex silently truncates project instructions.

## Prerequisites

One of the agents, installed by its own instructions:

- [Claude Code](https://code.claude.com/docs/en/setup)
- [Codex](https://developers.openai.com/codex/cli)
- [Gemini CLI](https://geminicli.com/docs/get-started/installation/)
- [Qwen Code](https://qwenlm.github.io/qwen-code-docs/en/users/quickstart/)
- [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/set-up/install-copilot-cli)
- [Kilo Code CLI](https://kilo.ai/docs/cli)
- [Antigravity CLI](https://antigravity.google/docs/cli/install)
- [Cursor](https://cursor.com/downloads)
- [Windsurf](https://windsurf.com/download)
- [opencode](https://opencode.ai/docs/)

## Install as a plugin

The plugin loads `AGENTS.md` at session start and adds the hooks that turn the rules an agent most often breaks into hard checks. Pick the plugin or the manual import, not both: both put the core in context twice.

| Agent | Install | Update | Uninstall |
|---|---|---|---|
| Claude Code | `/plugin marketplace add khasky/awesome-agents-md`, then `/plugin install awesome-agents-md@awesome-agents-md` | `/plugin marketplace update awesome-agents-md`, or turn on auto-update under `/plugin` → Marketplaces | `/plugin uninstall awesome-agents-md@awesome-agents-md` |
| Codex | `codex plugin marketplace add khasky/awesome-agents-md`, then `codex plugin add awesome-agents-md@awesome-agents-md` | `codex plugin marketplace upgrade awesome-agents-md`, then the `add` again | `codex plugin remove awesome-agents-md@awesome-agents-md` |
| Gemini CLI | `gemini extensions install https://github.com/khasky/awesome-agents-md` (add `--auto-update` to follow the repository) | `gemini extensions update awesome-agents-md` | `gemini extensions uninstall awesome-agents-md` |
| Qwen Code | `qwen extensions install https://github.com/khasky/awesome-agents-md` | `qwen extensions update awesome-agents-md` | `qwen extensions uninstall awesome-agents-md` |

What the hooks do:

- `guard` (before every shell command) blocks skipping git hooks (`--no-verify`, a `core.hooksPath` override), force-pushing, printing the environment or a secret variable, a `git commit` in a session where you never asked for one, and a commit carrying a `Co-Authored-By` or session trailer. When you do want one of these, run it yourself in a terminal.
- `shape` (after a file is written or edited) adds one line in the flow of the work: a source file just created is kept under 60 lines unless the request names more and proved with one run; a code edit in a repository with tests is proved with them, named with a command that runs there.
- `facts` (at session start) states how the repository's tests run here and, on Windows, which syntax each shell tool takes, so no command fails once to find out.
- `verify` (when the agent finishes) sends it back once, for the first of: an assistant trailer in its reply; an edit to code no command followed.
- `remind` (with every prompt) adds one line: answer in at most 35 words unless an explanation is asked for. Length is held by this line, not by sending an answer back, so no answer is paid for twice.

Codex runs the hooks only after you trust them: the next interactive `codex` start lists them under "Hooks need review". Codex passes no session transcript to the `Stop` hook, so `verify` does nothing there. Gemini CLI and Qwen Code get the core only, without hooks.

Every other agent takes the manual import below. GitHub Copilot CLI installs the plugin, but it reads only a JSON `additionalContext` from a session-start hook and `load-core` prints plain text, so the core would not reach the session. Antigravity CLI installs the repository from a clone (`agy plugin install <clone>` reads `gemini-extension.json`), but loads nothing from it: no context file, no hooks. Its own plugin format would read `rules/` as always-on rules, so it is not offered. Cursor's Agent Plugins format carries only skills and MCP servers. Kilo Code's plugins are npm code modules.

## Install manually (import)

Clone the repository once:

```powershell
git clone https://github.com/khasky/awesome-agents-md.git
```

Then add one import line to the agent's global instructions file (create it if it does not exist). The examples assume the clone is at `C:\repos\awesome-agents-md`; on macOS or Linux use `~/.claude/...` and your own path.

| Agent | File | Line |
|---|---|---|
| Claude Code | `%USERPROFILE%\.claude\CLAUDE.md` | `@C:/repos/awesome-agents-md/AGENTS.md` |
| Codex | `%USERPROFILE%\.codex\AGENTS.md` | `@C:/repos/awesome-agents-md/AGENTS.md` |
| Gemini CLI | `%USERPROFILE%\.gemini\GEMINI.md` | `@C:/repos/awesome-agents-md/AGENTS.md` |
| Qwen Code | `%USERPROFILE%\.qwen\QWEN.md` | `@C:/repos/awesome-agents-md/AGENTS.md` |
| GitHub Copilot CLI | `%USERPROFILE%\.copilot\copilot-instructions.md` | paste the contents of `AGENTS.md` |
| Antigravity | `%USERPROFILE%\.gemini\AGENTS.md` | paste the contents of `AGENTS.md` |
| opencode | `%USERPROFILE%\.config\opencode\AGENTS.md` | paste the contents of `AGENTS.md` |
| Kilo Code CLI | `%USERPROFILE%\.config\kilo\kilo.jsonc` | `"instructions": ["C:/repos/awesome-agents-md/AGENTS.md"]` |
| Cursor | Settings → Rules → User Rules | paste the contents of `AGENTS.md` |
| Windsurf | per project only: `AGENTS.md` in the repository root | copy the file |

- Claude Code, Gemini CLI and Qwen Code resolve the `@` import themselves; Claude Code asks once to approve it. Kilo Code reads the file named in `instructions`, so it follows `git pull` too.
- Copilot CLI expands `@` only for files inside its own instructions folder, so it takes the pasted text. Antigravity also reads `~/.gemini/GEMINI.md`: with the Gemini CLI line in place, skip its row, or the core loads twice.
- Windsurf caps global rules at 6,000 characters and `AGENTS.md` is longer, so it goes into each project instead.
- A pasted copy does not follow `git pull`: paste again after an update.
- Codex has no import syntax: it reads the `@` line as text and follows it. For guaranteed loading, paste the file itself (Codex reads up to 32 KiB of instructions).
- Per project instead of globally: copy `AGENTS.md` into the repository root. For Gemini CLI, add `"contextFileName": ["GEMINI.md", "AGENTS.md"]` to `~/.gemini/settings.json`.
- Never copy `rules/` into `.claude/rules/`: Claude Code loads every file there at session start, which turns the on-demand modules into always-on tokens.
- The import gets no hooks. In Claude Code, `"attribution": { "commit": "", "pr": "" }` in `settings.json` stops the default commit trailer.
- Update with `git pull` in the clone; uninstall by deleting the line.

## How modules load

Nothing loads a module automatically. The core points at `rules/INDEX.md`, one line per module naming the task that should open it; the agent reads the index when a task leaves the core, then the module whose line matches. The index stays out of the always-loaded core, so a turn that needs no module does not pay for it. Loading is therefore the agent's judgment call, the same as any other instruction it follows. To check that a module was read, ask the agent which `rules/` files it opened for the task, or watch for the file read in the tool log.

Conflicts resolve in a fixed order: the user's message, then the nearest project `AGENTS.md`/`CLAUDE.md`, then this core and the modules it indexes.

## Checking that it loaded

In Claude Code, `/context` shows the core in the session and how many tokens it takes, and `/doctor` suggests trims. In any agent, prompt "Summarize the instructions you loaded"; to check that the whole file arrived, ask about a rule near its end, such as the Commits section. If a specific rule keeps being ignored, the usual cause is file length: prune before rephrasing.

## Benchmark

Claude Code 2.1.284 runs the same seeded tasks with no plugin (baseline), with this ruleset, and with [caveman](https://github.com/JuliusBrussee/caveman), [ponytail](https://github.com/DietrichGebert/ponytail) and [i-have-adhd](https://github.com/ayghri/i-have-adhd), one plugin per session, the latest model of each tier at `--effort low`, 5 attempts per task. A script scores what each session leaves behind: trap tasks where the tempting move is the wrong one, source lines written for open requests, words in the final answer, and cost.

**Train split**, the tasks the ruleset was tuned against:

| | baseline | this ruleset | caveman | ponytail | i-have-adhd |
|---|--:|--:|--:|--:|--:|
| **Trap tasks passed, of 40** | | | | | |
| `claude-haiku-4-5` | 14 | **33** | 13 | 14 | 13 |
| `claude-sonnet-5` | 18 | **40** | 18 | 16 | 16 |
| `claude-opus-5-5` | 30 | **40** | 29 | 29 | 29 |
| **Source lines on open requests** | | | | | |
| `claude-haiku-4-5` | 116 | 76 | 101 | **64** | 81 |
| `claude-sonnet-5` | 103 | **63** | 100 | 73 | 102 |
| `claude-opus-5-5` | 144 | **36** | 144 | 48 | 113 |
| **Words in the answer** | | | | | |
| `claude-haiku-4-5` | 55 | 29 | **25** | 36 | 32 |
| `claude-sonnet-5` | 46 | **21** | 27 | 40 | 38 |
| `claude-opus-5-5` | 142 | **41** | 119 | 109 | 127 |
| **Cost per task** | | | | | |
| `claude-haiku-4-5` | **$0.050** | $0.064 | $0.054 | $0.054 | $0.055 |
| `claude-sonnet-5` | **$0.098** | $0.120 | $0.120 | $0.118 | $0.109 |
| `claude-opus-5-5` | **$0.142** | $0.159 | $0.185 | $0.161 | $0.164 |

**Test split**, written afterwards and never used to shape the ruleset; brackets are 95% intervals:

| | baseline | this ruleset | caveman | ponytail | i-have-adhd |
|---|--:|--:|--:|--:|--:|
| **Trap tasks passed, of 40** | | | | | |
| `claude-haiku-4-5` | 22 [40-69%] | **30** [60-86%] | 21 [37-67%] | 22 [40-69%] | 21 [37-67%] |
| `claude-sonnet-5` | 21 [37-67%] | **39** [87-100%] | 20 [35-65%] | 18 [31-60%] | 20 [35-65%] |
| `claude-opus-5-5` | 36 [77-96%] | **40** [91-100%] | 37 [80-97%] | 39 [87-100%] | 37 [80-97%] |
| **Source lines on open requests** | | | | | |
| `claude-haiku-4-5` | 64 | 44 | 45 | **25** | 48 |
| `claude-sonnet-5` | 39 | **31** | 42 | 34 | 40 |
| `claude-opus-5-5` | 49 | **24** | 58 | 28 | 45 |
| **Words in the answer** | | | | | |
| `claude-haiku-4-5` | 47 | 20 | **19** | 23 | 32 |
| `claude-sonnet-5` | 32 | 19 | **15** | 22 | 27 |
| `claude-opus-5-5` | 99 | **41** | 85 | 85 | 96 |
| **Cost per task** | | | | | |
| `claude-haiku-4-5` | **$0.036** | $0.049 | $0.039 | $0.039 | $0.041 |
| `claude-sonnet-5` | **$0.074** | $0.094 | $0.090 | $0.087 | $0.083 |
| `claude-opus-5-5` | **$0.094** | $0.125 | $0.128 | $0.115 | $0.117 |

Reproduce (run results stay outside the checkout):

```bash
python evals/benchmark/run.py --selftest                     # every scorer tells good from bad, no agent
python evals/benchmark/run.py --split test --repeats 5 --model claude-sonnet-5 --effort low --budget 30
python evals/benchmark/run.py --summary <run directory>      # totals with 95% intervals
```

## Related

Companion repositories, each a separate layer; pick the ones you need:

- **Awesome Agents MD** — *this repo:* the base, tool-agnostic ruleset every agent imports (one `AGENTS.md`). Start here; the layers below are optional on top.
- [Awesome Agent Skills](https://github.com/khasky/awesome-agent-skills) — portable `SKILL.md` skills every agent loads: code review, debugging, security and leak audits, code and text cleanup.
- [Agent MCP Integrations](https://github.com/khasky/agent-mcp-integrations) — MCP servers that connect agents to browsers, cloud, databases, infra, and domain APIs.
- [Claude Code Token Optimization](https://github.com/khasky/claude-code-token-optimization) — the token-efficiency layer (LSP, `codebase-memory-mcp`, ast-grep, Context7, Caveman, Ponytail).
- [Claude Code Security Audit](https://github.com/khasky/claude-code-security-audit) — the layered security-audit workflow (deep audit, continuous guardrails, scanners).

**A rule or a skill?** A rule is a standing constraint the agent honors without being asked; a skill is a procedure you invoke, with phases and an output contract. The two layers overlap: `rules/code-review.md` here sets the bar every review must meet, and the `awesome-code-review` skill runs the review and produces the report. Install both — rules keep everyday work in line, skills handle the jobs you name.

## Contributing

A rule earns its line only if an agent would get it wrong without it, and the core `AGENTS.md` stays under 200 instruction lines and 32 KiB — see [CONTRIBUTING.md](CONTRIBUTING.md) for the format of a new `rules/` module and the checks CI runs.

## Sources

Where the rules were distilled from, per file.

- `AGENTS.md`: the coding ladder, the root-cause fix and the output cap adapted from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (MIT); the compression mechanics, also in `rules/workflow.md`, from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) (MIT); non-interactive commands from a shell template widely copied across public AGENTS.md files; the proving command copied from CI from wxMaxima-developers/wxmaxima; scripted arithmetic from Anthropic's skill-authoring best practices.
- `rules/api-contracts.md`: Distilled from khasky/backend-architecture-playbook and khasky/frontend-architecture-playbook; deterministic generator output from JuliusBrussee/caveman.
- `rules/backend-security.md`: Distilled in own words from goldbergyoni/nodebestpractices (CC BY-SA 4.0), jesusprubio/strong-node (archived), ryanmcdermott/clean-code-javascript and airbnb/javascript; auth, caching, error-envelope, and runtime additions from the khasky/*-playbook suite; shipped-client rules from OWASP MASVS.
- `rules/caching.md`: Distilled from the Azure Cache-Aside pattern, Redis's own anti-patterns guidance (redis.io/learn/howtos/antipatterns), and production Redis practice; cache layers and per-family metrics from khasky/caching-playbook.
- `rules/ci-cd-security.md`: Distilled from TupleType/awesome-cicd-attacks (poisoned pipeline execution, dependency confusion, runner compromise), GitHub's hardening guide for Actions, zizmor/actionlint rule sets, and Trail of Bits' research on auditing AI-agent workflows in CI.
- `rules/code-review.md`: Style left to tooling follows Google's engineering practices; self-refuting findings follow khasky/ai-assisted-engineering-playbook; deterministic checks before model review from chrille0313/agentic-monorepo-template and PrimeIntellect-ai/verifiers.
- `rules/crypto.md`: Distilled from sobolevn/awesome-cryptography, paragonie/awesome-appsec, the OWASP Password Storage and Cryptographic Storage cheat sheets, and libsodium's design guidance; the bcrypt input limit from Okta's 2024 cache-key advisory.
- `rules/database.md`: Distilled from the Twelve-Factor App (config, backing services), Prisma and Drizzle docs, use-the-index-luke.com, the expand/contract migration pattern, GitHub's replication-lag throttling practice (freno), the sqlcheck SQL anti-pattern catalog (jarulraj), and Azure's SaaS tenancy pattern matrix; cross-checked against production reference implementations.
- `rules/debugging.md`: The reload check is distilled from khasky/sysadmin-operations-playbook.
- `rules/dependencies.md`: Distilled from TupleType/awesome-cicd-attacks (dependency confusion, typosquatting), lirantal/awesome-nodejs-security, npm/PyPI provenance documentation, and trickest/cve automation practice; lockfile conflicts from the npm package-lock documentation; update grouping from Renovate's group presets.
- `rules/deployment.md`: Distilled from continuous-delivery practice (deploy/release separation, progressive delivery), the expand/contract pattern, and feature-flag lifecycle guidance; cross-checked against production reference implementations; upstream-first backports from the Linux kernel, systemd and OpenStack stable-branch policies; infrastructure state from Terraform's state and backend documentation.
- `rules/design-patterns.md`: Distilled from python-patterns.guide (Brandon Rhodes), rust-unofficial/patterns, refactoring.guru, Martin Fowler's P of EAA and GUI Architectures, faif/python-patterns, and Game Programming Patterns (Nystrom); coupling kinds from Myers and Constantine's structured design; acyclic dependencies from Robert C. Martin; ports and adapters from Alistair Cockburn.
- `rules/evidence-gates.md`: Distilled from the artifact-contract gate in MaxMiksa/Auto-Company (run-identity binding, placeholder rejection, derived-flag recomputation) and from provenance practice for build attestations; hooks over prose from Claude Code's best practices.
- `rules/frontend-design.md`: Distilled from vercel-labs/web-interface-guidelines, nextlevelbuilder/ui-ux-pro-max-skill, anthropics/skills frontend-design, Anthropic's Opus 5.5 prompting guide (frontend design defaults), and khasky/marketing-and-seo-playbook (permission prompts, layout reservation); automated accessibility coverage from Deque's axe coverage study.
- `rules/git-hooks.md`: Distilled from the husky and lint-staged docs and pre-commit-hook practice; cross-checked against production reference implementations.
- `rules/i18n.md`: Distilled from ICU MessageFormat guidance, CLDR plural rules, and i18n review practice.
- `rules/incident-response.md`: Distilled from meirwah/awesome-incident-response, OTRF/ThreatHunter-Playbook (hypothesis-driven hunts), Cugu/awesome-forensics (evidence preservation), and Google SRE incident practice.
- `rules/jobs.md`: Distilled from Google SRE (distributed periodic scheduling), job-runner practice, and the idempotent-rerun pattern; cross-checked against production reference implementations.
- `rules/llm-agents.md`: Distilled from OWASP LLM01:2025 (prompt injection), Meta's "Agents Rule of Two", the SoK on the prompt-injection landscape and "The Attacker Moves Second" (adaptive breaks of 12 published defenses), MCP tool-poisoning research, and the Snyk agent-scan issue taxonomy (tool shadowing, toxic flows, hidden-Unicode payloads), and Anthropic's Opus 5.5 prompting guide (pasted-text marking, effort, reasoning blocks, time signals); remote tool servers from the MCP specification; one tool per capability from Anthropic's tool-writing guidance; sandboxing untrusted targets from khasky/claude-code-security-audit.
- `rules/long-running-agents.md`: Distilled from the loop engine of MaxMiksa/Auto-Company (state validation, soft timeout, quota-vs-error branching, self-mutation guard), standard supervisor practice for restart backoff and log rotation, and Anthropic's Opus 5.5 prompting guide (text-only turn ends, continuation caps, named early stops).
- `rules/messaging.md`: Distilled from Enterprise Integration Patterns (Hohpe & Woolf), microservices.io (Transactional Outbox, Idempotent Consumer), Stripe's webhook/signing docs, and at-least-once delivery practice; cross-checked against production reference implementations; consumer error classification from khasky/messaging-and-async-playbook.
- `rules/monorepo.md`: Distilled from khasky/monorepo-architecture-playbook; phantom dependencies from the pnpm and Rush documentation.
- `rules/observability.md`: Distilled from the Twelve-Factor App, Google SRE (health checking, graceful degradation), OpenTelemetry, and the RED method (Tom Wilkie); cross-checked against production reference implementations; runbook links from the Google SRE Workbook.
- `rules/payments.md`: Distilled from Stripe's official integration guides (webhook signature verification, idempotency, fulfillment) and PCI-DSS handling basics; cross-checked against production reference implementations.
- `rules/performance.md`: Pool saturation is distilled from khasky/nodejs-runtime-performance-playbook; same-lockfile comparisons from MxIris-Reverse-Engineering/MachOSwiftSection.
- `rules/planning.md`: Distilled from the plan-mode instructions in a public collection of Codex system prompts, and from spec-handoff practice; decision records from Michael Nygard's ADR format.
- `rules/privacy.md`: Distilled from GDPR/CCPA engineering practice: deletion propagation, retention enforcement, data mapping; consent from the ePrivacy Directive, the Planet49 ruling and EDPB guidance; session-replay masking from vendor privacy documentation.
- `rules/public-api-design.md`: Distilled from Stripe's API design, Google AIP, RFC 9457 (Problem Details), RFC 8594 (Sunset), RFC 7232 (conditional requests), RFC 9111 (HTTP caching), and the IETF RateLimit-header draft; cross-checked against production reference implementations; long-running operations from the Microsoft REST API Guidelines; header naming from RFC 6648.
- `rules/rate-limiting.md`: Distilled from Stripe's rate-limiter taxonomy, the standard limiter algorithms, and multi-instance counter practice; cross-checked against production reference implementations.
- `rules/refactoring.md`: The repeated-edit threshold and dry-run-first rewrites are distilled from robotocore/robotocore.
- `rules/resilience.md`: Distilled from the Azure Architecture Center cloud design patterns, microservices.io (Chris Richardson), Reactive Design Patterns (Kuhn), Enterprise Integration Patterns (Hohpe/Woolf), and Mark Richards' "Microservices Antipatterns and Pitfalls".
- `rules/shell-scripts.md`: Distilled from the classic Stack Overflow shell best-practices thread (question 78497), the ShellCheck wiki, and PowerShell strict-mode guidance; non-interactive flags from the same AGENTS.md shell template as the core.
- `rules/testing.md`: Distilled from khasky/testing-strategy-playbook and khasky/backend-architecture-playbook; load-testing practice from Slack engineering's continuous load testing; characterization tests from Michael Feathers.
- `rules/web-seo.md`: Distilled from AgriciDaniel/claude-seo, nowork-studio/NotFair, coreyhaines31/marketingskills, seb1n seo-optimization; corrected against current guidance (INP replaced FID in 2024; keyword-density advice dropped as dated). hreflang, redirect, and interstitial rules from khasky/marketing-and-seo-playbook; robots.txt, noindex and faceted navigation from Google Search Central documentation.

## License

Released under the [MIT license](LICENSE). Third-party material is credited under [Sources](#sources).
