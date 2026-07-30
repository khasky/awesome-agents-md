# Monorepo workspaces

Read this when working in a JS/TS workspace monorepo: pnpm/npm workspaces, Turborepo, Nx.

<!-- Distilled from khasky/monorepo-architecture-playbook. -->

- Install a dependency in the package that imports it, never in the root `package.json` — the root holds repo-level tooling only.
- Import other workspace packages through their public entry (`@scope/pkg`), never deep paths into their `src/` internals.
- No new `shared`/`common`/`utils` dumping-ground packages: extend the package that owns the domain, or propose a named, scoped package.
- Run tasks through the repo's orchestrator (`turbo run`, `nx affected`, workspace scripts) so caching and dependency order apply — don't hand-run each package.
- Repo uses Changesets → a change to any published package needs a changeset file in the same commit; without one the release silently skips it.
- Mark side-effecting tasks (`db:migrate`, `db:seed`, deploys) `cache: false` in the orchestrator, and add env files (`**/.env.*local`) to `globalDependencies` so an env change busts the cache instead of serving a stale build.
- Expose operations behind named workspace scripts (`docker:up`, `db:migrate`, `infra:deploy`) as one discoverable entrypoint, instead of contributors memorizing raw docker/prisma/cdk invocations.
- One lockfile per repo matching the declared package manager; committing two (`package-lock.json` + `pnpm-lock.yaml`) makes installs non-reproducible.
