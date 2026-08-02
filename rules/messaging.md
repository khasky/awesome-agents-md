# Events, queues, and webhooks

Read this when building async messaging: message queues, event streams, pub/sub, or inbound/outbound webhooks.

<!-- Distilled from Enterprise Integration Patterns (Hohpe & Woolf), microservices.io (Transactional Outbox, Idempotent Consumer), Stripe's webhook/signing docs, and at-least-once delivery practice; cross-checked against production reference implementations. -->

- Never publish to a broker inside the request path or transaction: write the domain change and an outbox row in the same DB transaction, then a separate relay reads the outbox and publishes. The commit is the single source of truth — the message can't exist without the state change or vice versa.
- The relay drains the outbox with `SELECT … FOR UPDATE SKIP LOCKED` plus a `dispatched` flag, so multiple worker instances poll concurrently without double-sending.
- Delivery is at-least-once, so consumers must be idempotent: carry a stable event id, dedupe on it (unique constraint or seen-set), and make the handler safe to run twice. Derive queue job ids deterministically (`endpointId:eventId`) so a re-enqueue can't double-deliver.
- Consumer retry policy: bounded attempts, exponential backoff with jitter, throw to trigger retry; after max attempts move the message to a dead-letter queue and record why. Persist one row per delivery attempt for visibility. A consumer retry budget is not an outbound HTTP retry budget — the broker already redelivers, so counting both without noticing multiplies the attempts (`rules/backend-security.md` for the outbound numbers).
- Inbound webhooks you receive: verify the signature against the raw request body before parsing, reject timestamps outside a tolerance window (replay defense), and respond fast — do the work async. Return 2xx only once the event is durably accepted; return 5xx to make the sender retry (`rules/payments.md` for the payment specifics).
- Outbound webhooks you send: sign `${timestamp}.${rawBody}` with HMAC, ship `t=…,v1=…`, constant-time compare on receipt, reveal the signing secret exactly once, and expose the delivery/retry log to the subscriber.
- Message payloads are versioned objects with a type discriminator, not bare values — a new field can't break existing consumers.
- Redis pub/sub needs a dedicated subscriber connection (`.duplicate()`): a subscribed connection can't run normal commands. Guard the message parse and drop malformed messages instead of crashing the loop.
- Ordering isn't guaranteed across partitions/consumers. If order matters, key by entity and process one key serially, or carry a sequence number the consumer checks.
- Idempotent also means order-independent: a redelivered, delayed, or backfilled message must not clobber newer state — merge on the entity's version/timestamp carried in the payload, never on arrival order. Last-write-wins by arrival silently undoes the newest write during any replay.
