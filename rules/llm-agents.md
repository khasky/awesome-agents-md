# Building LLM and agent features

Read this when the code you write calls an LLM, builds an agent, exposes tools to a model, or ingests retrieved content (RAG, MCP servers, tool-using assistants).

<!-- Distilled from OWASP LLM01:2025 (prompt injection), Meta's "Agents Rule of Two", the SoK on the prompt-injection landscape and "The Attacker Moves Second" (adaptive breaks of 12 published defenses), and MCP tool-poisoning research. -->

- **Rule of Two.** In one agent run, allow at most two of: untrusted input, access to sensitive data or credentials, the ability to change state or communicate outward. All three at once needs a human approval gate in the path — not a stronger prompt.
- The dangerous injection class is indirect, not direct: retrieved documents, tool and API responses, RAG chunks, web pages, file contents, and MCP tool descriptions all carry text an attacker wrote. Every one of them is data at every layer; none of them can grant permissions, change the task, or name a new tool to call.
- No single filter is a defense. Classifiers, delimiter tags, and "ignore previous instructions" guards were adaptively broken in published work — the mitigation that holds is a sandbox plus information-flow control (what this agent may read cannot reach what it may send).
- Model output is untrusted input the moment it reaches a sink: SQL, shell, `eval`, the DOM, a file path, or a tool call. Validate and constrain it at that boundary exactly as you would a request body (`rules/backend-security.md`).
- Tools follow least privilege: scoped short-lived credentials per tool, destructive tools behind explicit approval, no admin token in agent context, and a kill switch that stops a running loop.
- Isolate per user and tenant: prompt caches, embeddings, vector stores, and conversation memory are keyed by user+tenant so one user's content cannot surface in another's retrieval or context (`rules/database.md` for the cache-key rule).
- Cost is an attack surface: per-user token and request caps, a hard timeout per completion, and a global circuit breaker. An unauthenticated endpoint that triggers a model call is a denial-of-wallet primitive.
- Never place credentials, authorization logic, or private business rules in a system prompt — assume it is extractable verbatim.
- Pin and allowlist MCP servers, plugins, and tool manifests by version; re-read a tool description on update as you would review a dependency bump (`rules/dependencies.md`).
- Model-generated code executes only in a sandbox with no ambient credentials and no network by default; agent-to-agent messages are authenticated, since a compromised agent otherwise propagates instructions across the fleet.
- Log the prompt/response pair with secrets and PII redacted, plus a correlation id, so an incident can be reconstructed (`rules/observability.md`).
- Evaluate with adversarial cases, not happy paths: a fixture set of injection payloads that must fail closed, run in CI like any other regression suite (`rules/testing.md`).
