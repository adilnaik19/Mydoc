# My Doc+ — Authentication & Security

## 1. Overview
Stateless, token-based auth. The server holds no session; every protected
request carries a signed bearer token that the server verifies cryptographically.

## 2. Password storage
- Algorithm: **PBKDF2-HMAC-SHA256**, 200,000 iterations.
- Per-user random 16-byte salt (`secrets.token_bytes`).
- Stored format: `pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>`.
- Verification is constant-time (`hmac.compare_digest`).

## 3. Token format (JWT-style)
A compact `header.payload.signature`, each part base64url-encoded.

```
header:    { "alg": "HS256", "typ": "JWT" }
payload:   { "sub": <user_id>, "role": "patient", "iat": <ts>, "exp": <ts+7d> }
signature: HMAC_SHA256(base64url(header) + "." + base64url(payload), SECRET)
```

- Signed with a server secret (`config.SECRET`, overridable via env
  `MYDOCPLUS_SECRET`).
- Verified on every protected request: signature match + `exp` not passed.

## 4. Sign-up / login flow
```
Sign up (patient)
  client -> POST /api/auth/signup {name,email,password}
  server  : validate -> ensure email unused -> hash password -> insert user
          -> issue token -> 201 {token, user}

Login (any role)
  client -> POST /api/auth/login {email,password}
  server  : find user by email -> verify password (constant time)
          -> issue token -> 200 {token, user}

Authenticated request
  client -> GET /api/... Authorization: Bearer <token>
  server  : parse token -> verify signature -> check exp -> load user
          -> enforce role -> handle
```

## 5. Role-based access control
Each protected handler declares the roles allowed. The dispatcher rejects with:
- `401` when the token is missing/invalid/expired,
- `403` when the user is valid but the role isn't permitted.

| Resource | patient | doctor | admin |
|----------|:------:|:-----:|:----:|
| Book appointment | ✅ | | |
| View own appointments | ✅ | ✅ | ✅ |
| Complete + prescribe | | ✅ | |
| Admin stats/management | | | ✅ |

## 6. Transport & headers
- CORS enabled for the SPA origin (MVP: permissive for local use).
- Security headers on every response: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`.
- Production: terminate TLS at the load balancer, HSTS, secure cookies if used.

## 7. Roadmap to production hardening
The MVP covers hashing, signing, RBAC, and validation. The following extend it
toward the full spec (kept out of the runnable MVP because they need external
services):
- OAuth / social login (Google, Apple) via Auth0 or Firebase Auth.
- Email verification + phone OTP + biometric (device) login.
- Two-factor authentication (TOTP).
- Refresh tokens + short-lived access tokens + token revocation list (Redis).
- Rate limiting (per-IP / per-account) and brute-force lockout.
- Audit logging of security-relevant events.
- Secret rotation via a managed secrets store (KMS / Secrets Manager).
- GDPR data-export/erasure endpoints; HIPAA-aligned access controls and
  encryption at rest for medical records.

## 8. Security checklist (tracked)
- [x] Passwords hashed (PBKDF2, salted, high iterations)
- [x] Constant-time password comparison
- [x] Signed, expiring tokens
- [x] Role-based authorization per endpoint
- [x] Parameterized SQL (no injection)
- [x] Security response headers
- [ ] TLS / HSTS (deployment concern)
- [ ] Rate limiting
- [ ] 2FA / OTP / social login
- [ ] Audit logs
- [ ] Encryption at rest for records (KMS)
