# Dependencies and supply chain

Read this when adding, upgrading, or auditing third-party packages in any ecosystem (npm, PyPI, Go modules, Cargo, Maven).

<!-- Distilled from TupleType/awesome-cicd-attacks (dependency confusion, typosquatting), lirantal/awesome-nodejs-security, npm/PyPI provenance documentation, and trickest/cve automation practice. -->

- Adding a dependency is an "ask first" decision (core Boundaries rule). Before proposing one, walk the coding ladder: stdlib, a native platform feature, or an already-installed package usually covers it.
- One lockfile per repo, committed, matching the declared package manager; CI installs frozen (`npm ci`, `pnpm install --frozen-lockfile`, `pip install -r requirements.txt --require-hashes`) — never a resolving install.
- Prefer `--ignore-scripts` on install; a package's postinstall script runs with your shell's privileges before any code is imported.
- Dependency confusion: internal package names are scoped (`@company/pkg`) and the registry is pinned in `.npmrc`/`pip.conf`/equivalent with no implicit fallback to the public index. An internal name that resolves publicly is a takeover waiting to happen.
- Check a new name for typosquats before installing it: transposed characters, hyphen/underscore swaps, and a plausible-but-wrong scope are the standard trick.
- LLM-suggested package names are hallucination-prone (slopsquatting): before adding one, confirm the package exists under exactly that name and is the canonical one — real age, downloads, linked repo. Plausible inventions (`nestjs-redis` for `@nestjs-modules/ioredis`) are pre-registered by attackers precisely because agents keep suggesting them.
- Verify provenance where the registry supports it (`npm audit signatures`, sigstore attestations); prefer packages that publish from a traceable build.
- License is a shipping constraint, not a preference: check a new package and the transitive packages it drags in against what this project may ship — copyleft in a distributed binary, network-copyleft in a hosted service. A license that changes on upgrade is a breaking change and an "ask first" decision (core Boundaries rule).
- Emit an SBOM as a build artifact (`syft`, CycloneDX, SPDX) and keep it with the release, so "are we affected by this CVE" is a query against a file rather than an archaeology project (`rules/ci-cd-security.md`).
- Maintenance status is a security property: an unmaintained package with zero CVEs is still a finding — no upstream means no patch on the day one lands.
- The maintainer is part of the attack surface: a single anonymous maintainer, no security contact or disclosure policy, and high-risk features (install scripts, FFI, deserialization) compound into takeover risk no CVE scan shows — weigh them when choosing between otherwise-equal packages.
- Report a vulnerability with its dependency path and whether it is direct or transitive (`express > send > mime`); the fix differs.
- No fix available → check whether the vulnerable code path is reachable from your code before escalating or accepting; an unreachable CVE in a dev-only dependency is not a release blocker, and saying so is part of the finding.
- Automated advisory and PoC feeds are leads, not verdicts — confirm against the actual installed version and call path before acting.
- An unpatched transitive vulnerability gets pinned with `overrides`/`resolutions`/`constraints` plus a comment naming the CVE and the condition for removing the pin — never left to a range that quietly resolves back to the vulnerable version.
- Removing a dependency belongs to the change that stopped using it: an import deleted without the package leaves install weight, lockfile entries, and attack surface behind (core Coding rule on orphans).
- Update bots run on a stated cadence with a stated automerge policy — patch and lockfile-only updates may automerge behind green CI, a major version is a human decision. An open bot PR queue nobody reads is worse than no bot: it converts every real advisory into noise.
- Pin exact versions for anything that executes at build time (build plugins, codegen, CI tooling) and for one-off executions (`npx pkg@1.2.3`, `uvx`, `pipx run`) — a bare `npx pkg` resolves and runs whatever is latest at that moment, unreviewed; ranges are acceptable only where a lockfile freezes them.
- Upgrades land as their own commit, separate from feature work, so a regression bisects cleanly (`rules/code-review.md`).
