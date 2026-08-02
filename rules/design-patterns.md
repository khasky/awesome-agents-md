# Design patterns and architecture choice

Read this when choosing or reviewing a design pattern, structuring a new module or service, or naming an app architecture (MVC/MVP, layered, hexagonal) — before reaching for a GoF pattern.

<!-- Distilled from python-patterns.guide (Brandon Rhodes), rust-unofficial/patterns, refactoring.guru, Martin Fowler's P of EAA and GUI Architectures, faif/python-patterns, and Game Programming Patterns (Nystrom). -->

- A pattern needs a named recurring problem. Apply one only after the simplest working code has demonstrably recurred as a problem (core coding ladder); a pattern justified by "best practice" instead of a problem is over-engineering.
- Reuse the vocabulary the codebase already speaks: identify the incumbent patterns (Repository, Active Record vs Data Mapper, Unit of Work, MVC/MVP, event bus) and stay consistent with them. A second competing pattern for the same concern is a defect even when it is "better".
- Composition over inheritance. Inheritance only for genuine is-a substitution a caller relies on; a hierarchy deeper than two levels, or a base class that exists only to share code, gets refactored to composition.
- Never implement Singleton: use a module-level instance, DI, or the platform's single-instance mechanism. The real smell is global mutable state — naming it "Singleton" doesn't fix it.
- Replace GoF machinery with the language feature that made it obsolete: first-class functions over Strategy/Command, generators over Iterator, language decorators over Decorator classes, channels/events/signals over hand-rolled Observer plumbing. A pattern class where a closure suffices is noise.
- Present a pattern decision as use-when / avoid-when with the 2–3 trade-offs that matter, and name the trade-off accepted when applying one — never justify by implementation mechanics.
- Name the code smell first, then pick the refactoring or pattern it points to — smell → refactoring → pattern, not pattern-first (`rules/refactoring.md`).
- Architecture weight matches project size, and testability decides layers: a layer earns its place by making logic reachable by a test (humble views — no domain logic in UI components). VIPER/hexagonal ceremony on a small app is a bug, not rigor.
- One interface, one implementation, no concrete second consumer on the roadmap = speculative abstraction (core YAGNI); delete it, or mark it as a deliberate, documented extension point.
- A god object is measured in fused concerns, not lines: a long file cohesive around one hard problem is fine; a short file doing routing + persistence + rendering is not.
- Pattern advice is version-bound: check the installed major before applying framework patterns from articles or training data — pre-hooks React patterns and Vue 2 patterns are anti-patterns in the current majors (core "code against the installed version").
