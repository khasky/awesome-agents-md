# Next.js (App Router)

Read this when working in a Next.js App Router codebase: Server Components, Server Actions, Route Handlers, and the server/client boundary.

<!-- Distilled from the Next.js App Router docs (Server Components, Server Actions, Route Handlers, rendering/caching, `server-only`) and the React Server Components model; cross-checked against reference implementations. -->

- Default to Server Components; add `'use client'` only at the leaf that needs interactivity or browser APIs, kept as far down the tree as possible so most of the page stays server-rendered and ships no JS.
- Mark every secret-touching module `import 'server-only'` (db client, auth, payment SDK, env loader) so an accidental client import is a build error, not a runtime leak.
- Split env into two modules: a server loader validating all secrets (imported by server code only) and a separate client loader validating only `NEXT_PUBLIC_*`. A secret then has no path into the client bundle.
- Validate env at boot against a schema and fail loud — format guards (key prefixes, minimum lengths), no silent defaults (core Security rule; `rules/observability.md`).
- Re-authorize inside every Server Action and Route Handler — never rely on middleware alone. Middleware can be bypassed by direct invocation; the mutation itself checks the acting user and resource ownership (`rules/backend-security.md`).
- Server Actions validate their `FormData`/args with a schema at the boundary (`safeParse`) before touching data, and return a typed error state on failure — an action is a public endpoint, not an internal function.
- Routes needing the raw request body (webhooks, signature verification) or that must never be cached set `export const runtime = 'nodejs'` and `export const dynamic = 'force-dynamic'`; read the body with `req.text()` before parsing (`rules/payments.md`, `rules/messaging.md`).
- DB client/pool as a `globalThis` singleton so serverless invocations and dev hot-reload reuse one connection instead of exhausting the pool (`rules/database.md`).
- Use the framework's data primitives instead of hand-rolling: `fetch` caching/revalidation, `generateStaticParams` for static routes, `revalidatePath`/`revalidateTag` after a mutation — don't bolt a client-side data layer onto Server Components.
- Never pass secrets or server-only objects as props into Client Components; pass plain serializable data only.
