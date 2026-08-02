# Astro and static-site generators

Read this when building an Astro site — the same architecture principles apply to other islands/SSG frameworks (Eleventy, Hugo, a static Next.js export).

<!-- Distilled from the Astro docs (islands architecture, content collections, i18n, view transitions, astro:assets), Jason Miller / Katie Sylor-Miller's "islands architecture", and build-time-data practice; cross-checked against reference implementations. -->

- SSG-first: render everything possible to static HTML at build time; ship JavaScript only for interactive parts. A page with no interactivity ships zero client JS.
- Islands, minimally hydrated: wrap each interactive region in its own component and pick the least-eager directive — `client:idle`/`client:visible` over `client:load`; reserve `client:load` for above-the-fold interactivity. Don't hydrate a whole page to make one widget interactive.
- Keep content in content collections with a typed schema (`src/content/config.ts`) so frontmatter is validated at build and queried type-safely — don't hand-glob Markdown.
- Fetch data at build time (in component frontmatter / `getStaticPaths`); handle fetch errors so a bad response fails the build deterministically instead of shipping a broken page. Reserve SSR / server islands for genuinely per-request data.
- Determinism: build output must be reproducible — seed any randomness, don't depend on wall-clock or network state that varies between builds.
- i18n only if the project actually localizes: use the framework's i18n routing with one translation source of truth; don't scaffold locale machinery a single-language site doesn't need (YAGNI).
- Namespace ids inside inline SVG/`<defs>` before injecting many onto one page — duplicate `id="…"`/`url(#…)` across instances collide and break gradients/filters.
- Optimize images through the framework's pipeline (`astro:assets` / `<Image>`): explicit dimensions to prevent CLS, modern formats, responsive `srcset` (`rules/web-seo.md`).
- Keep runtime and type-resolution path aliases (`@/…`) in sync across the build config and `tsconfig.json`.
