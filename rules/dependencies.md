# Dependencies and supply chain

Read this when adding, upgrading, or auditing third-party packages in any ecosystem (npm, PyPI, Go modules, Cargo, Maven).

<!-- Distilled from TupleType/awesome-cicd-attacks (dependency confusion, typosquatting), lirantal/awesome-nodejs-security, npm/PyPI provenance documentation, and trickest/cve automation practice. -->

- Adding a dependency is an "ask first" decision (core Boundaries rule). Before proposing one, walk the coding ladder: stdlib, a native platform feature, or an already-installed package usually covers it.
- One lockfile per repo, committed, matching the declared package manager; CI installs frozen (`npm ci`, `pnpm install --frozen-lockfile`, `pip install -r requirements.txt --require-hashes`) — never a resolving install.
- Prefer `--ignore-scripts` on install; a package's postinstall script runs with your shell's privileges before any code is imported.
- Dependency confusion: internal package names are scoped (`@company/pkg`) and the registry is pinned in `.npmrc`/`pip.conf`/equivalent with no implicit fallback to the public index. An internal name that resolves publicly is a takeover waiting to happen.
- Check a new name for typosquats before installing it: transposed characters, hyphen/underscore swaps, and a plausible-but-wrong scope are the standard trick.
- Verify provenance where the registry supports it (`npm audit signatures`, sigstore attestations); prefer packages that publish from a traceable build.
- Maintenance status is a security property: an unmaintained package with zero CVEs is still a finding — no upstream means no patch on the day one lands.
- Report a vulnerability with its dependency path and whether it is direct or transitive (`express > send > mime`); the fix differs.
- No fix available → check whether the vulnerable code path is reachable from your code before escalating or accepting; an unreachable CVE in a dev-only dependency is not a release blocker, and saying so is part of the finding.
- Automated advisory and PoC feeds are leads, not verdicts — confirm against the actual installed version and call path before acting.
- Pin exact versions for anything that executes at build time (build plugins, codegen, CI tooling); ranges are acceptable only where a lockfile freezes them.
- Upgrades land as their own commit, separate from feature work, so a regression bisects cleanly (`rules/code-review.md`).
