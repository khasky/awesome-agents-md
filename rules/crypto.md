# Applied cryptography

Read this when code hashes, encrypts, signs, or generates anything security-bearing: passwords, tokens, sessions, signatures, encrypted fields.

<!-- Distilled from sobolevn/awesome-cryptography, paragonie/awesome-appsec, the OWASP Password Storage and Cryptographic Storage cheat sheets, and libsodium's design guidance. -->

- Never implement a primitive, a mode, or a protocol yourself. Use libsodium, the platform's audited API (`crypto` in Node, `cryptography` in Python, Web Crypto in browsers), or a maintained wrapper — "we only wrote the padding" is how it breaks.
- Banned in a security role: MD5 and SHA-1 (signatures, tokens, integrity), ECB mode, a static or reused IV/nonce, and any non-cryptographic RNG (`Math.random`, `rand()`, `System.currentTimeMillis` as a seed). MD5 for a cache key or file dedup is fine — the role decides, not the function.
- Passwords use argon2id (memory-hard) or bcrypt; the cost factor is a tuned number with a comment naming when it was last measured, re-tuned as hardware moves — a constant copied from a 2015 blog post is a finding. Enforce a length floor (≥12) plus a breached-password check rather than composition rules.
- Random values that matter (tokens, session ids, salts, nonces, reset codes) come from the CSPRNG: `crypto.randomBytes`, `secrets.token_urlsafe`, `crypto/rand`, `SecureRandom`. Name the entropy in bits when reviewing: ≥128 for anything guessable offline.
- Compare secrets, MACs, and signatures in constant time (`crypto.timingSafeEqual`, `hmac.compare_digest`, `subtle.ConstantTimeCompare`); `===` on a token is a timing oracle.
- Encrypt with an AEAD (XChaCha20-Poly1305, AES-GCM) so ciphertext is authenticated; if you ever hand-compose, it is encrypt-then-MAC, never MAC-then-encrypt. A unique nonce per message is a correctness requirement, not a suggestion.
- JWT: pin the expected algorithm on verify and reject `alg: none` and any algorithm switch (HS/RS confusion is a full auth bypass); verify `exp`, `iss`, and `aud`, not just the signature. Prefer an opaque session id over a JWT when you control both ends.
- Design key rotation in from the start: a key id travels with the ciphertext/token so old material decrypts while new material is written under the new key. A scheme with no rotation path becomes unrotatable exactly when it is compromised.
- Keys live in a secrets manager or env, never in source, and never in the same store as the data they protect (core Security rule).
- Store token *hashes*, not tokens (`rules/backend-security.md`); a leaked table then yields nothing replayable.
- TLS is the transport floor: 1.2 minimum, certificate validation never disabled "for local dev" in shared code — gate it behind an explicit local-only flag or fix the local trust store.
