# Caching

Read this when adding or reviewing a cache — in-process, a shared cache server, or a cached computation; the server-side examples are Redis. HTTP/CDN response caching lives in `rules/public-api-design.md`.

<!-- Distilled from the Azure Cache-Aside pattern, Redis's own anti-patterns guidance (redis.io/learn/howtos/antipatterns), and production Redis practice. -->

- Cache-aside is the default: read → miss → load from the source of truth → set with TTL. The write path invalidates the key rather than updating the cached value in place — two writers updating a value race; a delete is idempotent.
- Choose the write strategy by read-follows-write distance, before writing code: cache-aside covers most cases; write-through when a read follows its write immediately and staleness is unacceptable; write-behind only for loss-tolerant counters and metrics — it acknowledges before the store write, so a crash loses data.
- Invalidation is designed before the cache is added, not after the first stale bug: every entry gets a TTL as the guardrail, and the domain event that makes the value wrong is named and invalidated on (`rules/backend-security.md`). A cache "invalidated" only by expiry serves known-stale data for the whole window.
- Set the eviction policy and memory ceiling explicitly (in Redis: `maxmemory` plus `allkeys-lru`/`volatile-ttl`) — the unconfigured default either grows until OOM or silently evicts the wrong class of keys.
- Cache keys encode their scope — tenant, user, locale, schema version; permission- or billing-sensitive data never sits under a shared key (`rules/backend-security.md`).
- The cache is disposable: anything that can't be rebuilt from the source of truth doesn't live only in the cache. Ephemeral Redis as the primary store for real state is an outage on a timer.
- Stampede protection on expensive keys: single-flight/lock so one expiry triggers one rebuild, or jittered TTLs so a cohort of keys doesn't expire in the same second.
- Never `KEYS` (or an unbounded `SMEMBERS`) in application code — `SCAN` for ops tooling, a maintained index structure for app lookups. `KEYS` is O(N) over the whole keyspace and blocks the server.
- A hot key melts one shard while the cluster idles: shard the key (bucket suffix, aggregated on read) or put a short-TTL in-process cache in front of it.
- Pipeline or batch (`MGET`/`MSET`) serial round-trips; a per-item network round-trip in a loop is the cache's own N+1.
- Model Redis values for the access pattern: a HASH when fields are read/written independently, a serialized blob only when the value is always read whole.
- An in-process cache is per-instance state: N instances hold N divergent copies and a deploy wipes them all. Anything needing cross-instance coherence goes to the shared cache; in-process caches stay small, bounded (LRU with a max size), and safe to lose (`rules/backend-security.md` stateless-process rule).
- Expose hit/miss counters per cache (`rules/observability.md`): an unmeasured cache can't justify its complexity, and a 5% hit rate is a bug that looks like a feature.
