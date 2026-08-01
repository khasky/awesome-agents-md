# Observability and runtime config

Read this when adding logging, health checks, metrics, graceful shutdown, or environment configuration to a running service.

<!-- Distilled from the Twelve-Factor App, Google SRE (health checking, graceful degradation), OpenTelemetry, and the RED method (Tom Wilkie); cross-checked against production reference implementations. -->

- Validate all environment variables at boot against a schema; fail loud listing every missing/invalid key, then expose a typed, cached config object. No scattered `process.env` reads, no silent default for anything that matters (core Security rule).
- Two liveness endpoints, not one: `/healthz` (or `/livez`) returns 200 whenever the process is up and calls no dependencies; `/readyz` probes each dependency and returns 503 with a per-dependency status map. Load balancers poll liveness; orchestrator readiness gates traffic on readiness.
- Structured logs (JSON) to stdout only — the destination is deployment config, never a hardcoded file transport. One log line per request: method, route, status, latency.
- Redaction list on the logger, not per call-site: `authorization`, `cookie`, `x-api-key`, `idempotency-key`, and any `*.password`/`*.token`/`*.secret` field. Treat anything logged as retained and possibly shipped off-host.
- Correlation id per request: honor an inbound `x-request-id`/trace header or generate one (ULID/UUID), attach it to every log line, and echo it in the response header and error body.
- Metrics: RED per route — request Rate, Error count, Duration histogram — emitted from one response hook, plus default process metrics. Keep `/metrics` off the public rate-limit and out of API docs.
- Graceful shutdown on `SIGTERM`/`SIGINT`: stop accepting new work (close the HTTP server), let in-flight requests drain under a timeout, flush telemetry, then close pools/queues/redis via `Promise.allSettled`, then exit. Workers close consumers before the connection.
- Set an explicit shutdown deadline; if drain exceeds it, force-exit rather than hang the orchestrator's termination grace period.
- An unrecoverable dependency loss makes `/readyz` fail so traffic drains — never a fake 200 that keeps routing requests into a broken process.
- Field names follow one canonical schema across every service (pick ECS or OCSF and document the choice) so events from different components join on the same keys during an incident. A per-service field naming convention makes correlation manual work.
- Log the security-relevant events explicitly: authentication failure, authorization denial, privilege or role change, admin and impersonation actions, and credential rotation. Their absence is itself a finding after an incident — you cannot reconstruct what was never recorded (`rules/incident-response.md`).
- Prefer one wide canonical event per request — a single structured line carrying route, actor, tenant, latency, status, and the decision fields — over many thin lines; reconstruction reads one record instead of stitching five.
