# Backend and API security

Read this when writing or reviewing server-side code: HTTP APIs, auth, database access, background jobs.

<!-- Distilled in own words from goldbergyoni/nodebestpractices (CC BY-SA 4.0), jesusprubio/strong-node (archived), ryanmcdermott/clean-code-javascript and airbnb/javascript; auth, caching, error-envelope, and runtime additions from the khasky/*-playbook suite. -->

## Any language

- Error responses: never send `err.message`, stack traces, or internal details to the client — log them server-side, return a generic message (with a correlation ID if the stack has one).
- One global error handler maps domain errors to statuses — services never speak HTTP codes. Stable error JSON (`code`, `message`, `request_id`); pick 400 vs 422 once per API.
- Crash policy: operational errors (bad input, timeouts, unavailable dependencies) → handle, respond, stay up. Programmer errors (unknown state) → log and exit; let the runtime restart the process. Don't catch-all-and-continue, and don't crash on malformed user input.
- Authorization data comes from trusted sources only: take the acting user's ID from the session or token claims, never from `req.params`/body (IDOR).
- Authentication is not authorization: a handler over a specific resource verifies the acting principal's access to that resource and tenant — a valid session or role alone is not enough.
- Auth responses are uniform ("Invalid login", not "User not found") and constant-time (`crypto.timingSafeEqual` or equivalent) — no user enumeration, no timing oracle.
- Rate-limit auth endpoints: consecutive failures per user+IP, plus per-IP volume over time. Regenerate the session ID after login or privilege change.
- Browser auth default: httpOnly-cookie session; access/refresh tokens in `localStorage` only as an explicit, documented architecture decision — never as the reflex.
- CORS is an allowlist of exact origins — never a reflected `Origin`, and never `*` together with credentials. Enumerate the allowed methods and headers instead of wildcarding them; a reflected origin plus `Allow-Credentials` is a cross-origin read of authenticated responses.
- Never introduce permissive security config unprompted: no CORS headers, wildcard origins, disabled TLS verification, relaxed CSP, or auth bypasses added to "make it work" — name the blocked call and let the user decide (core Boundaries spirit: loosening a control is an ask-first change).
- Cookie-authenticated state changes need CSRF defense: `SameSite=Lax` or `Strict` as the baseline plus a per-session token verified on unsafe methods — `SameSite` alone does not cover sibling subdomains or non-browser clients. A pure `Authorization`-header API needs no CSRF token; state which of the two models this API is, because assuming the wrong one leaves the gap.
- Response security headers come from one middleware or the edge, never per route: `Strict-Transport-Security`, a `Content-Security-Policy` without `unsafe-inline`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, and a restrictive `Permissions-Policy`. A CSP that grades as "present" while allowing inline script buys nothing.
- Escape at the sink, not at the door: one string is safe as HTML text, unsafe in an attribute, and different again inside a `<script>` or a URL. Use the template engine's contextual escaping and never bypass it (`dangerouslySetInnerHTML`, `v-html`, `|safe`) without running the value through a maintained sanitizer.
- Credential floors: password length ≥12 with a breached-password check instead of composition rules; session tokens ≥128 bits of CSPRNG entropy (`rules/crypto.md`).
- Refresh tokens rotate on every use and bind to a client context (device, audience). A rotated token presented again is a compromise signal: revoke the whole token family, don't just fail the request. Revoke explicitly on logout, password change, and offboarding — a short access-token TTL is not revocation.
- Sensitive actions (billing changes, admin operations, security-setting edits, data export) require fresh step-up verification with a defined elevated-assurance window; "MFA at login" is not step-up. Account recovery must not silently downgrade to a single factor — that is the standard MFA bypass.
- Support/admin impersonation is time-boxed, scoped, and audited with `actor` recorded separately from `effective_user`; destructive actions stay gated while impersonating.
- Check-then-act on a balance, quota, stock, or rate limit is atomic — a conditional `UPDATE … WHERE`, a lock, or one transaction. A read, then a decision, then a write is a TOCTOU race that parallel requests win.
- Multi-step flows (checkout, onboarding, KYC, approval) enforce order and completion server-side: posting straight to the final endpoint must fail. Client-side sequencing is not enforcement.
- Persist token *hashes*, never raw tokens: store a `sha256`/argon2 hash of reset/verify/session tokens, look them up by `hash + expiresAt > now`, and delete all of a user's tokens in the same transaction that consumes one. A leaked table then yields nothing usable.
- Validate and coerce every request at the trust boundary before the handler — body, query, and path params — with a schema (JSON Schema/Ajv, zod): reject unknown keys (`additionalProperties: false`, zod strips) to block mass-assignment; require ≥1 field on PATCH so an empty update can't silently no-op; coerce and bound path params (`z.coerce.number().int().positive()`).
- Whitelist the response too, not just input: serialize responses through an explicit schema/DTO so internal columns (password hashes, internal flags) can't leak by accident.
- Expose opaque public ids (uuid/cuid) for resources in URLs; a sequential primary key leaks row counts and invites enumeration (`rules/database.md`).
- Database: parameterized queries only — never concatenate or template values into SQL.
- Regex on user input: don't hand-roll (nested quantifiers → ReDoS can block the event loop for seconds); use proven validators or vetted patterns.
- Path traversal containment: `path.join(safeRoot, path.join('/', userPath))` or equivalent normalization inside a fixed root.
- An outbound request to a user-supplied URL is SSRF until proven otherwise: resolve the hostname first, then reject loopback, private, link-local, and cloud-metadata ranges *after* resolution, re-check on every redirect hop, refuse scheme changes, and prefer an allowlist of destinations over a denylist of addresses.
- Bound every input dimension explicitly — body size, upload size, field count, array length, JSON nesting depth, multipart parts. A parser with no limit is a denial-of-service primitive that no rate limiter catches.
- Validate uploads by content, not by filename or the client's `Content-Type`: sniff magic bytes, allowlist only the types actually handled, assign a server-side name, store outside the web root or in object storage, and serve back with a fixed content type and `Content-Disposition: attachment`.
- Log hygiene: raw user input never enters logs unsanitized (log injection); secrets and PII never at all. Destination, format, and redaction list are one deployment-level decision, never a hardcoded file transport in a handler (`rules/observability.md`).
- Event/message payloads are objects, not raw values — extensible without touching every handler.
- Keep server processes stateless: no module-level caches, sessions, or uploads held in process memory; externalize to a store.
- Cache keys encode scope — tenant, user, locale, schema version; permission- or billing-sensitive data never under a shared key.
- TTL is a guardrail, not invalidation: name the domain event that makes a cached value wrong and invalidate on it.
- Calling external APIs: never retry 4xx (fix input or credentials); retry 429 per `Retry-After` with jitter, 5xx with capped exponential backoff (3–5 attempts); state-mutating retries need an idempotency key; mid-stream (SSE) errors are terminal — restart, don't resume; log the provider's request ID.

## Node.js specifics

- `return await` inside try blocks — a bare `return promise` skips the surrounding catch and drops the function from stack traces.
- try/catch does not catch EventEmitter or stream errors: subscribe to `'error'`; register `process.on('unhandledRejection')`; async event handlers need `{ captureRejections: true }`.
- Express: an async route handler that throws or rejects never reaches the error middleware unless errors are forwarded (`express-async-errors` or an async wrapper) — otherwise the request hangs. Fastify and most modern frameworks await handlers natively.
- No sync calls in request paths (`fs.*Sync`, `crypto.pbkdf2Sync`, `zlib.*Sync`) — they block the event loop; stream large payloads instead of buffering whole files in memory.
- Bound fan-out: no `Promise.all` over an unbounded collection — batch or cap concurrency.
- Shelling out: `child_process.execFile` over `exec` — no shell expansion; never interpolate input into a command string.
- Builtins via the `node:` prefix (`import http from "node:http"`) — kills builtin-name typosquatting.
