# Containers and images

Read this when writing a Dockerfile, a Compose file, Kubernetes manifests, or container build/run configuration.

<!-- Distilled from Docker's official build best-practices, the OWASP Docker Top 10, distroless/non-root guidance, multi-stage build practice, and the Kubernetes production patterns workshop (gravitational) plus the Kubernetes Patterns book (Ibryam/Huß); cross-checked against production reference implementations. -->

- Multi-stage build with named stages (deps → builder → runner); the final image carries only the built artifact and production dependencies — no source, dev deps, or build toolchain.
- Order layers by change frequency for cache reuse: copy manifests + lockfile first, install with the frozen lockfile (`rules/dependencies.md`), then copy source. A source edit then doesn't bust the dependency layer.
- Run as a non-root user: create a system user/group, `--chown` copied artifacts to it, `USER` before `CMD`. Root in the container is root after a container escape.
- `.dockerignore` excludes `node_modules`, `.git`, build output, and every `.env*` — shrinks the build context and keeps secrets out of image layers.
- Pin base images to a major + slim/distro variant (`node:24-alpine`, `postgres:16-alpine`); avoid `latest`, and check the major is still in LTS/support before pinning it. Prefer slim/distroless to shrink attack surface.
- Never bake a runtime secret into an image to satisfy a build step: use a throwaway placeholder for build-time codegen and inject the real secret at runtime from the orchestrator/secret manager. A secret in a layer is recoverable from the image.
- Compose gates dependent startup on real readiness: a `healthcheck` (`pg_isready`, an HTTP probe) plus `depends_on: condition: service_healthy` — not bare `depends_on`, which only waits for start, not ready.
- Run schema migrations as a start step before the app process (`migrate deploy && start`) or as a separate init job — not lazily inside request handling.
- One process concern per container; logs go to stdout for the runtime to collect (`rules/observability.md`); keep the container stateless (uploads/sessions/cache go to external stores).
- Reproducible builds pin the base image by digest (`node:24-alpine@sha256:…`), not by tag alone — a tag is remutable upstream.
- Scan the built image in CI (Trivy, Grype) and fail the build on fixable critical/high findings; publish an SBOM alongside the image so a later CVE can be matched to what actually shipped (`rules/dependencies.md`).
- Run with a read-only root filesystem plus explicit writable mounts (`tmpfs` for scratch), drop all Linux capabilities and add back only what the process needs, and set `no-new-privileges`.
- Never mount the Docker socket into an application container: socket access is root on the host.
- PID 1 must handle signals: run the process in exec form (or under an init like `tini`) — a shell-form entrypoint swallows `SIGTERM`, so every stop is a 30s hang plus `SIGKILL` and orphaned children (`rules/observability.md` graceful shutdown).
- Kubernetes: no bare pods — a Deployment/StatefulSet/Job owns every container so restart, rollout, and placement stay declarative; change by manifest, never `kubectl edit`.
- Every k8s workload declares resource requests and limits and both probes: readiness gates traffic, liveness restarts. Point liveness at the process's own health only, never at downstream dependencies — or a slow dependency restart-loops healthy pods.
- k8s Jobs/CronJobs set `backoffLimit` and `activeDeadlineSeconds`: a fast-failing Job without limits is a restart hot loop that floods logs and bills (`rules/jobs.md` for scheduling semantics).
- A safe rollout needs a PodDisruptionBudget and `maxUnavailable`/`maxSurge` tuned to real capacity — the defaults evict enough replicas to brown out a small deployment during a node drain.
- Autoscale on the signal that actually saturates: queue depth or consumer lag for workers, in-flight requests or a latency percentile for services — CPU only when CPU is the real ceiling (`rules/resilience.md` load leveling).
- Per-environment config comes from ConfigMaps/Secrets injected at deploy, not per-environment images — one image is built once and promoted through environments.
