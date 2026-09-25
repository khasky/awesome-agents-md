# Monorepos

Read this when working in a repository that holds several packages, modules or services built together, in any ecosystem (JS/TS workspaces, Cargo workspaces, Go workspaces, Gradle multi-project, uv workspaces, or equivalent).

- Declare a dependency in the package that uses it, never at the root; the root holds repository-level tooling only.
- Import another package through its public entry point, never by a deep path into its internals.
- No new `shared`/`common`/`utils` dumping-ground packages: extend the package that owns the domain, or propose a named, scoped package.
- Run tasks through the repository's orchestrator or workspace commands so caching and dependency order apply; don't hand-run each package.
- A change to a published package carries the repository's release-note record (a changeset file, a changelog entry) in the same commit; the release tooling skips a change that has none.
- Side-effecting tasks (migrations, seeds, deploys) are never cached, and environment files are part of the task cache key, so an environment change rebuilds instead of serving a stale result.
- Expose operations as named workspace tasks (`db:migrate`, `infra:deploy`), one discoverable entry point instead of raw tool invocations contributors must memorize.
- One lockfile at the repository root covering the whole workspace, never one per package: a per-package lockfile resolves that package's tree in isolation and silently diverges from what the root install produces (`rules/dependencies.md`).
