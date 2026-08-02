# Client state management

Read this when writing or reviewing client-side state in a JS/TS web app that uses a store or server-cache library (TanStack Query, SWR, Zustand, Pinia): component state, global stores, persisted state, route state. The ownership ladder and the persistence rules carry to any client framework; the named hooks and options do not.

<!-- Distilled from the react-zustand, vue-pinia, tanstack-query/router, and nextjs-tanstack-query rule files in PatrickJS/awesome-cursorrules. -->

- Ownership ladder — put state at the lowest rung that holds: ephemeral UI state → component-local; state a user should bookmark, share, or restore (filters, tabs, pagination) → the URL; cross-component client state → one store; server data → the query/cache layer. Escalating a rung is a decision to justify, never the default.
- Never mirror server data into a client store: the query layer already owns caching, staleness, and refetch; a store copy is a second source of truth that is stale the moment the server changes. The only exception is a documented offline or draft-editing requirement.
- URL search params are user input: schema-validate them at the route boundary (the router's `validateSearch` hook or a schema parse), never read raw strings deep in components (core trust-boundary rule).
- Persisted client state is untrusted input on hydration: validate it against a schema and fall back to defaults on mismatch — the user, another tab, or an injected script can edit web storage freely.
- Persist by field allowlist (`partialize`-style), never the whole store; tokens, PII, and authorization decisions never go to web storage (`rules/backend-security.md`). Anything persisted beyond trivial preferences carries a schema `version` and a `migrate` path — silent shape drift after a deploy breaks returning users.
- Represent request state as one union (`idle | loading | success | error`), not independent booleans — `isLoading && isError` must be unrepresentable.
- SSR: stores and query clients are per-request instances created in request scope and hydrated on the client — a module-level singleton on the server leaks one user's data into the next request. In the browser, one instance lives for the session.
- Co-locate each resource's query key and fetch options in one factory module shared by components, prefetch, and route loaders — ad-hoc keys scattered per call site are how a mutation invalidates nothing.
- Distinguish "no data yet" from "refreshing" (`isLoading` vs `isFetching`) and keep previous data while paginating — a full-page spinner on every page change is a regression dressed as loading UX.
