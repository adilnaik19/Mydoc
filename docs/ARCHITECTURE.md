# My Doc+ — Architecture Overview

## 1. Purpose
My Doc+ is a healthcare appointment booking platform with three roles:
**Patient**, **Doctor**, and **Admin**. This document describes the architecture
of the MVP built to run in a zero-dependency sandbox, and how it maps to a
production stack.

## 2. Guiding principles
- **Clean layering:** transport (HTTP) → routing → service/handlers → data access → DB.
- **SOLID / separation of concerns:** each module has one responsibility.
- **Stateless auth:** JWT-style tokens (HMAC-SHA256), no server session store.
- **Zero external dependencies (MVP):** everything uses the Python standard
  library so it runs anywhere Python 3.10+ is installed, with no `pip install`.
- **Production-portable design:** the same schema and API contract map 1:1 onto
  a Next.js + NestJS + PostgreSQL + Prisma stack (see section 8).

## 3. High-level diagram

```
+-------------------------------------------------------------+
|                      Browser (SPA)                          |
|  index.html + app.js + styles.css                           |
|  - Patient / Doctor / Admin views                           |
|  - Light & dark Material theme                              |
|  - Talks to REST API via fetch(), stores JWT in localStorage|
+----------------------------+--------------------------------+
                             | HTTP/JSON (REST)
                             v
+-------------------------------------------------------------+
|            Python stdlib HTTP server (backend/)             |
|                                                             |
|  server.py     -> ThreadingHTTPServer, request lifecycle    |
|  router.py     -> path/method dispatch, path params         |
|  auth.py       -> JWT sign/verify, pbkdf2 password hashing  |
|  handlers/     -> auth, doctors, appointments, admin        |
|  db.py         -> sqlite3 connection + query helpers        |
|  schema.sql    -> table definitions                         |
|  seed.py       -> sample specialties, doctors, patients     |
+----------------------------+--------------------------------+
                             |
                             v
                   +-------------------+
                   |   SQLite (file)   |
                   |  mydocplus.db     |
                   +-------------------+
```

## 4. Backend layers
| Layer | Module | Responsibility |
|-------|--------|----------------|
| Transport | `server.py` | Accept HTTP, parse body/headers, serve static frontend, delegate `/api/*` to the router |
| Routing | `router.py` | Match method + path (incl. `:id` params) to a handler, JSON in/out |
| Security | `auth.py` | Password hashing (PBKDF2), token issue/verify, `@require_auth` role checks |
| Domain | `handlers/*.py` | Business logic per resource |
| Data | `db.py` | Thin sqlite3 wrapper: `query`, `query_one`, `execute`, transactions |
| Storage | `mydocplus.db` | Relational persistence |

## 5. Request lifecycle
1. Browser sends `fetch('/api/...', { headers: { Authorization: 'Bearer <jwt>' }})`.
2. `server.py` reads the request, routes `/api/*` into `router.dispatch`.
3. Router resolves the handler; protected handlers call `auth.get_current_user`.
4. Handler runs domain logic via `db.py` and returns `(status, dict)`.
5. Server serializes JSON, sets CORS + security headers, responds.

## 6. Security model (MVP)
- Passwords hashed with **PBKDF2-HMAC-SHA256**, 200k iterations, per-user salt.
- **JWT-style** bearer tokens signed with HMAC-SHA256; payload carries
  `sub` (user id), `role`, `exp`.
- **Role-based access control** enforced per endpoint (`patient`/`doctor`/`admin`).
- Security headers (`X-Content-Type-Options`, `X-Frame-Options`, etc.).
- Input validated in handlers; parameterized SQL only (no string interpolation).

> Note: The MVP is a functional reference. Production hardening (rotating
> secrets, refresh tokens, rate limiting, TLS termination, audit logs, HIPAA/GDPR
> controls) is documented in `AUTH.md` and the security checklist.

## 7. Folder structure
```
mydocplus/
  docs/            # Option C deliverables (this design set)
    ARCHITECTURE.md
    DATABASE.md
    API.md
    AUTH.md
  backend/
    server.py
    router.py
    auth.py
    db.py
    config.py
    schema.sql
    seed.py
    handlers/
      __init__.py
      auth_handler.py
      doctors_handler.py
      appointments_handler.py
      admin_handler.py
  frontend/
    index.html
    styles.css
    app.js
  run.py             # entry point: init db, seed, start server
```

## 8. Mapping to the production stack (Option B, later)
| MVP (here) | Production equivalent |
|------------|----------------------|
| Python stdlib HTTP server | NestJS (Node.js) controllers/providers |
| `router.py` | Nest routing decorators |
| `auth.py` (hand-rolled JWT) | `@nestjs/jwt` + Passport, Auth0/Firebase |
| `db.py` + `schema.sql` | Prisma ORM + PostgreSQL migrations |
| Vanilla SPA | Next.js (App Router) + component library |
| SQLite file | PostgreSQL + Redis cache + cloud object storage |

The REST contract in `API.md` is stack-agnostic, so the frontend and the
production backend can be swapped independently.

## 9. Roadmap (vertical slices)
1. **Slice 1 (this build):** Patient auth, doctor search/profile, booking,
   appointment management, admin overview.
2. Doctor panel: schedule management, accept/complete appointments, prescriptions.
3. Payments (Stripe/Razorpay), invoices.
4. Video consultation (WebRTC) + chat.
5. AI assistant (symptom → specialty), notifications, maps, calendar sync.
