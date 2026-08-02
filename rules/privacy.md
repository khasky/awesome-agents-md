# Personal data and retention

Read this when code stores, copies, or deletes personal data — user deletion, retention policies, PII handling, data export. Legal scope is the user's call; these are the engineering invariants under any privacy regime.

<!-- Distilled from GDPR/CCPA engineering practice: deletion propagation, retention enforcement, data mapping. -->

- Deletion propagates to every copy or it isn't deletion: primary rows, caches, search indexes, analytics/warehouse, queues and DLQs, logs, and backups each need an explicit answer — delete now, expire by retention, or crypto-shred (destroy a per-user key). "Deleted from the users table" alone is a compliance bug (`rules/caching.md`, `rules/messaging.md`).
- Backups are append-only by design, so deletion there is policy, not a row operation: bounded retention plus re-deletion after any restore (replay the deletion log), or per-user encryption with key destruction.
- Collect at the minimum: a field is stored only when the feature in front of you reads it, and the purpose is recorded where the schema lives — data never collected needs no deletion path, no retention window, and no breach disclosure.
- Classify personal-data columns at the schema level, and default every new sink — log field, event, export — to excluding them: PII spreads through copies, never through the original (`rules/observability.md` redaction).
- Retention is per data class with an enforced purge job, not a policy document: name the window, implement the purge, alert if it stops running (`rules/jobs.md`).
- Soft delete is not deletion: `deleted_at` keeps the data. Decide per table whether soft-deleted rows get hard-purged on a schedule, and exclude them by a default scope, not per call-site.
- Data export (portability) carries the same authorization rigor as deletion: verified identity, rate-limited, audit-logged — an export endpoint is an exfiltration endpoint with paperwork (`rules/backend-security.md`).
- Anonymization keeps no reversible link: a mapping table back to identity is the data with extra steps. Aggregates built before deletion may stand only if the individual can't be re-derived from them.
