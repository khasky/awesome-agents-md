# Payments and checkout

Read this when integrating a payment provider (Stripe — the same principles hold for Adyen, Braintree, PayPal): checkout, webhooks, fulfillment.

<!-- Distilled from Stripe's official integration guides (webhook signature verification, idempotency, fulfillment) and PCI-DSS handling basics; cross-checked against production reference implementations. -->

- Never trust client-sent prices, currencies, or totals: the client sends product ids and quantities; the server re-derives every line item and amount from the canonical database/catalog before creating the payment session.
- Verify webhook signatures against the raw, unparsed request body with the provider SDK; reject (400) if the signature header is missing or invalid. A parsed then re-serialized body fails verification.
- Fulfill only from the webhook (`checkout.session.completed`/`payment_intent.succeeded`), never on the browser success/redirect page — the redirect is display-only and unreliable (tab closed, network dropped). Mark the success page `noindex`.
- Fulfillment is idempotent: look up by the provider's session/event id and no-op if already processed — providers redeliver and retry events.
- Webhook return codes drive provider retries: 400 on bad signature (no retry), 5xx on a handler exception (provider retries), 2xx only after the work is durably done. Never return 2xx on failure — that drops the event.
- Do all order writes (order, line items, stock decrement, cart clear) in one transaction; run side-effects (confirmation email, analytics) after commit, best-effort, catching their errors so they never roll back a paid order.
- Guard stock/inventory against oversell in the database (`GREATEST(stock - qty, 0)` or a conditional `UPDATE … WHERE stock >= qty`), not read-modify-write in app code.
- Send the provider's idempotency key on create calls (charge, refund, session) so a retried request can't double-charge.
- Rate-limit checkout initiation per client so an attacker can't run up provider API cost or spam sessions.
- Never store raw card data; keep provider secret keys server-only (`sk_…`, `whsec_…`) and out of the client bundle and any tracked file (`rules/backend-security.md`).
