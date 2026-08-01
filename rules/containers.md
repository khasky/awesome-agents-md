# Containers and images

Read this when writing a Dockerfile, a Compose file, or container build/run configuration.

<!-- Distilled from Docker's official build best-practices, the OWASP Docker Top 10, distroless/non-root guidance, and multi-stage build practice; cross-checked against production reference implementations. -->

- Multi-stage build with named stages (deps → builder → runner); the final image carries only the built artifact and production dependencies — no source, dev deps, or build toolchain.
- Order layers by change frequency for cache reuse: copy manifests + lockfile first, install with the frozen lockfile (`npm ci`, `pnpm install --frozen-lockfile`), then copy source. A source edit then doesn't bust the dependency layer.
- Run as a non-root user: create a system user/group, `--chown` copied artifacts to it, `USER` before `CMD`. Root in the container is root after a container escape.
- `.dockerignore` excludes `node_modules`, `.git`, build output, and every `.env*` — shrinks the build context and keeps secrets out of image layers.
- Pin base images to a major + slim/distro variant (`node:20-alpine`, `postgres:16-alpine`); avoid `latest`. Prefer slim/distroless to shrink attack surface.
- Never bake a runtime secret into an image to satisfy a build step: use a throwaway placeholder for build-time codegen and inject the real secret at runtime from the orchestrator/secret manager. A secret in a layer is recoverable from the image.
- Compose gates dependent startup on real readiness: a `healthcheck` (`pg_isready`, an HTTP probe) plus `depends_on: condition: service_healthy` — not bare `depends_on`, which only waits for start, not ready.
- Run schema migrations as a start step before the app process (`migrate deploy && start`) or as a separate init job — not lazily inside request handling.
- One process concern per container; log to stdout; keep the container stateless (uploads/sessions/cache go to external stores).
- Reproducible builds pin the base image by digest (`node:20-alpine@sha256:…`), not by tag alone — a tag is remutable upstream.
- Scan the built image in CI (Trivy, Grype) and fail the build on fixable critical/high findings; publish an SBOM alongside the image so a later CVE can be matched to what actually shipped (`rules/dependencies.md`).
- Run with a read-only root filesystem plus explicit writable mounts (`tmpfs` for scratch), drop all Linux capabilities and add back only what the process needs, and set `no-new-privileges`.
- Never mount the Docker socket into an application container: socket access is root on the host.
