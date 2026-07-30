# Public API design

Read this when designing or evolving an HTTP API that external clients consume: versioning, pagination, idempotency, concurrency, deprecation. Pairs with `rules/api-contracts.md` (schemas and generated clients).

<!-- Distilled from Stripe's API design, Google AIP, RFC 9457 (Problem Details), RFC 8594 (Sunset), RFC 7232 (conditional requests), and the IETF RateLimit-header draft; cross-checked against production reference implementations. -->

- Version in the URL path (`/v1`, `/v2`) as independent route trees with their own schemas. Additive changes go in place; a breaking change only ever creates a new version — an existing version's response shape never changes under clients.
- Publish a breaking-vs-non-breaking taxonomy so consumers know what's safe: adding a field or optional param is non-breaking; removing/renaming a field, tightening validation, or changing a type is breaking.
- Paginate with opaque cursors, not offset: base64url-encode the `(sort_key, id)` tuple over a covering index — stable under concurrent inserts, no skipped or duplicated rows. Return a `{ object: "list", data, has_more, next_cursor }` envelope.
- Idempotency for unsafe methods: accept an `Idempotency-Key`, store the first response keyed by it, replay the stored response on repeat, and 409 if the same key arrives with a different body. Never cache a 5xx (it must stay retryable).
- Optimistic concurrency with ETags: return a weak ETag; honor `If-None-Match` → 304 on reads and `If-Match` → 409 `version_mismatch` on writes, returning the current version so the client can rebase.
- Stable error envelope across the whole API (RFC 9457 `type`/`title`/`status`/`detail`, or a `{ code, message, request_id }` shape) parsed by one shared client helper (`rules/api-contracts.md`).
- Standard rate-limit headers (`RateLimit-Limit`/`Remaining`/`Reset`, `Retry-After`) so clients self-throttle; key limits by API key, then IP.
- Deprecation lifecycle by header: `Deprecation` + `Sunset` + `Link rel="successor-version"`, a minimum removal window (commonly 12 months), then `410 Gone`. Announce; don't silently break.
- Every resource response carries a type discriminator and a stable, sortable id (prefixed ULID / `obj_…`) so clients can route polymorphic payloads.
