# Database and ORM

Read this when writing schema, migrations, queries, or data-access code — raw SQL or an ORM (Prisma, Drizzle, TypeORM).

<!-- Distilled from the Twelve-Factor App (config, backing services), Prisma and Drizzle docs, use-the-index-luke.com, and the expand/contract migration pattern; cross-checked against production reference implementations. -->

- Client/pool is one long-lived instance: in dev with hot-reload, cache it on `globalThis` guarded by `NODE_ENV` so reloads don't open a new pool each time and exhaust connections. Serverless: cap the pool (often `max: 1`) and reuse it across invocations.
- Size the pool against the database's connection limit, not the app's concurrency: connections summed across every instance, worker, and migration job stay under `max_connections` with headroom for an admin session. A pool wider than the work the database can actually run in parallel adds queueing, not throughput — put a pooler (PgBouncer, RDS Proxy) in front instead of raising the number.
- One datasource selected by env (`DATABASE_URL`), one documented switch point between local (SQLite/container) and production (Postgres) — no per-file connection strings.
- Multi-row invariants run in one transaction: interactive callback (`tx => …`) for dependent writes that read each other, array/batch form for independent writes. Side-effects (email, queue publish) happen after commit, never inside the transaction.
- Push invariants into the schema, not app code: `NOT NULL`, `UNIQUE`, `CHECK`, foreign keys with `ON DELETE CASCADE`, enums instead of free-text status. A DB constraint can't be bypassed by a new code path; an app-code check can.
- Index every foreign key and every hot query's filter/sort columns; add a composite index for each `(filter, sort)` pair. Unindexed FKs make joins and cascade deletes scan.
- N+1 is a design defect, not a micro-optimization: a loop that queries once per row turns one request into hundreds. Fetch with a join or a batched `IN (…)` (`include`/`with` in an ORM) and assert the query count in a test on the hot paths — the symptom is invisible on seed data and obvious in production.
- Name the isolation level whenever the default is wrong for the invariant: read-committed will not stop the phantom that `SELECT … FOR UPDATE` or a serializable retry loop catches. Acquire locks in one documented order across the codebase — two transactions taking the same rows in opposite order deadlock under load and never in tests — and set `lock_timeout`/`statement_timeout` so a stuck transaction fails fast instead of pinning the pool.
- Reads go to a replica only where staleness is acceptable, and the replication lag is measured rather than assumed. Anything reading its own write — the redirect after a create, a confirmation screen — reads the primary, or the user is shown a row that does not exist yet.
- Parameterize always — bound parameters or the ORM's query builder, never string-concatenated SQL, even for `LIKE`/full-text (`rules/backend-security.md`).
- Migrations are versioned, committed, and forward-only in production (`migrate deploy`); `db push`/schema-sync is for local prototyping only. Never edit an applied migration — add a new one.
- Destructive schema change = expand/contract: add the new shape, backfill, switch reads, then drop the old column in a later migration — never rename-in-place on a live table.
- Before a destructive migration or a bulk data change, confirm the restore path exists and has actually been exercised — a backup nobody has restored is a hypothesis (core Boundaries rule). Know the retention window and the point-in-time-recovery granularity of the environment being touched before, not after.
- Seed data lives in a committed, idempotent script (`… IF NOT EXISTS`, upserts) that can run repeatedly without duplicating rows.
- Run migrations as a deploy step before the app boots (container entrypoint or a release phase), not lazily on first request.
- Type JSON columns to a named shape and write through a builder, not untyped blobs. Give URL-exposed rows an opaque public id (`cuid`/`uuid`) so the sequential primary key never leaks (`rules/backend-security.md`).
- Gate query logging by env (`error`/`warn` in dev, `error` only in prod); never log query parameters that carry PII or secrets.
