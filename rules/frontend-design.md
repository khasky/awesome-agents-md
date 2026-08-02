# Frontend design and UI craft

Read this when building, styling, or reviewing UI: pages, components, dashboards.

<!-- Distilled from vercel-labs/web-interface-guidelines, nextlevelbuilder/ui-ux-pro-max-skill, anthropics/skills frontend-design, and khasky/marketing-and-seo-playbook (permission prompts, layout reservation). -->

## Direction before code

- Commit to one clear aesthetic direction before writing code: purpose, tone, and what makes this design distinctive. Refined minimalism and bold maximalism both work — timid middle ground doesn't.
- Never default to the generic AI look: Inter/Roboto/Arial/system fonts, purple-gradient-on-white, identical card layouts. Vary fonts, palettes, and layout between projects.
- Pair a distinctive display font with a refined body font. Dominant color with sharp accents beats an evenly-distributed timid palette.
- One well-orchestrated page-load reveal (staggered `animation-delay`) beats scattered micro-interactions.
- Match implementation complexity to the vision: maximalism needs elaborate code; minimalism needs restraint and precise spacing.
- When a design system exists, use its tokens and components — no hardcoded hex/pixel values, no ad-hoc restyling; flag deviations instead of silently inventing them.

## Numbers agents get wrong

- Contrast: 4.5:1 body text, 3:1 large text and UI components against adjacent colors. Test dark mode separately — desaturated tonal variants, never inverted colors.
- Touch targets ≥44×44px with ≥8px gaps; extend the hit area beyond a smaller visual icon.
- Body text ≥16px (avoids iOS auto-zoom), line-height ~1.5, 65–75 characters per line.
- Spacing on a 4/8px scale; z-index from a defined scale (0/10/20/40/100); no arbitrary values.
- Motion: 150–300ms micro-interactions, ≤400ms transitions; ease-out on enter, ease-in on exit (exit ~70% of enter); stagger lists 30–50ms per item; animate `transform`/`opacity` only; honor `prefers-reduced-motion`; animations interruptible, never input-blocking; no `transition: all`.
- Icons: SVG from one family with one stroke width (Lucide, Heroicons) — never emoji; don't mix filled and outline at the same hierarchy level.
- `tabular-nums` for numbers in columns (prices, timers, data).

## Interaction correctness

- `<button>` for actions, `<a>` for navigation — never `<div onClick>`; icon-only buttons need `aria-label`; semantic HTML before ARIA.
- Never remove focus outline without a `:focus-visible` replacement. No `tabindex` greater than 0.
- Core task completable in ≤3 interactions; one primary action per view — no competing primary buttons.
- Dialogs: trap focus inside, set initial focus, Escape closes, focus returns to the trigger on close.
- Link field errors to inputs with `aria-describedby` + `aria-invalid`; toasts are never the only notification (pair with `aria-live`).
- `dvh` over `vh` for full-height layouts.
- Forms: never block paste; correct `type`/`inputmode` per field; labels clickable; validate on blur, not keystroke; errors inline naming the fix, focus the first invalid field; submit stays enabled until the request starts, then shows progress; warn before navigating away with unsaved changes.
- Destructive actions need confirm or undo — never immediate.
- URL reflects state: filters, tabs, pagination deep-linkable; back restores scroll and state.
- Loading: skeleton for operations >1s; visible tap feedback within 100ms.
- Content resilience: design for short, average, and very long content; `truncate`/`line-clamp`/`break-words`; flex children need `min-width: 0`; handle empty states.
- Images get explicit width/height; reserve layout space for any injected UI (banners, consent bars, embeds) — nothing shifts content when it loads. Lazy-load below the fold; virtualize lists >50 items.
- Never trigger browser permission prompts (notifications, geolocation) on page load — request after a user action that shows the value.
- Typography micro-craft: `…` not `...`; curly quotes; non-breaking spaces inside `10 MB` and brand names; `text-wrap: balance` on headings, `pretty` on body.
- Locale: `Intl.DateTimeFormat`/`Intl.NumberFormat`, never hand-formatted dates/numbers.
- Copy: active voice; specific button labels ("Save API key", not "Continue"); error messages state the fix.
- Flag on sight: `user-scalable=no`, `maximum-scale=1`, paste blocking, unlabeled icon buttons, images without dimensions, `outline: none`.

## Animation performance

- Cost ladder: composite (`transform`/`opacity`) < paint (color/shadow/filter) < layout (size/position). Pick the cheapest that matches the intent; animate paint/layout only on small isolated surfaces.
- Never interleave layout reads and writes in the same frame: measure once, then animate via transform (FLIP); batch reads before writes.
- Don't drive animation from scroll events or `scrollTop` — use Scroll/View Timelines or IntersectionObserver; pause animations off-screen; no rAF loops without a stop condition.
- `will-change` is temporary and surgical — never applied outside an active animation. Don't animate CSS variables.
- Blur ≤8px, one-shot, never continuous or on large surfaces. View transitions for navigation-level changes only.
- Never migrate or mix animation libraries unless asked.

## Review output

When reviewing UI against these rules, use the comment format from `rules/code-review.md` (`file:line: <severity>: problem. fix.`); "✓ pass" when clean. Each finding names the violated rule and proof it applies to that surface; try to falsify each before reporting; order by impact.
