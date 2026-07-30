# RTK usage details

Read this when RTK is installed (`rtk --version` succeeds).

RTK re-runs a command and prints a compressed summary of its output: `rtk <command>`. It saves tokens on noisy commands.

- Prefer wrapping: `rtk git status`, `rtk git diff`, `rtk git log`, `rtk npm test`, `rtk npm run build`, `rtk pytest`, `rtk tsc`.
- If RTK does not support a command, run the normal command and summarize only the important output.
- Agent hooks (e.g. a Claude Code `PreToolUse` hook running `rtk hook claude`) may auto-rewrite shell commands through RTK — so RTK can be in the loop even when not typed. With the hook active, type plain commands; manual prefixing adds nothing.
- The hook rewrite is idempotent: an already-prefixed `rtk …` command is not double-wrapped (`rtk hook check "rtk git status"` → `rtk git status`).
- Meta commands, always run directly: `rtk gain` (savings analytics, `--history` for per-command log), `rtk proxy <cmd>` (raw passthrough, for debugging a suspect filter).

Trust rules — a filter can fabricate a clean summary over real errors:

- Known incident: RTK's generic lint filter printed "Lint: No issues found" over 4 real biome errors. Never route biome (or the lint/format package scripts that run it) through RTK; keep them listed in `[hooks].exclude_commands` of the RTK config (`%APPDATA%\rtk\config.toml` on Windows), and keep that list in sync when adding new biome-backed scripts.
- Exit code beats summary. If a command exits non-zero but the filtered output looks clean, the filter lied — re-run the raw command (or via a shell the hook doesn't touch) and read the real output before concluding anything.
- Verify before trusting a new tool through RTK: `rtk hook check "<command>"` shows the rewrite dry-run; if it rewrites a tool RTK has no dedicated filter for, add it to `exclude_commands`.
