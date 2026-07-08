# My Doc+ 🩺

A doctor appointment booking platform — **runnable, zero-dependency MVP**.

Built with only the **Python standard library** (HTTP server + `sqlite3`) on the
backend and **vanilla HTML/CSS/JS** on the frontend. No `pip install`, no
`npm install` — it runs anywhere Python 3.10+ is available.

This is the first vertical slice of the larger My Doc+ vision (Patient / Doctor /
Admin healthcare platform). See [`docs/`](docs) for the full design.

## Quick start

```bash
python run.py
# → My Doc+ running at http://0.0.0.0:8000
```

Open <http://localhost:8000>. The database is created and seeded automatically
on first run.

### Configuration (env vars)
| var | default | purpose |
|-----|---------|---------|
| `MYDOCPLUS_PORT` | `8000` | HTTP port |
| `MYDOCPLUS_SECRET` | dev secret | JWT signing key (set in production!) |
| `MYDOCPLUS_DB` | `./mydocplus.db` | SQLite file path |

## Demo accounts
| role | email | password |
|------|-------|----------|
| Patient | `asha@mydocplus.dev` | `patient123` |
| Doctor | `neha@mydocplus.dev` | `doctor123` |
| Admin | `admin@mydocplus.dev` | `admin123` |

(Other seeded doctors use the same `doctor123` password — see `backend/seed.py`.)

## What works in this slice
- **Patient:** sign up / sign in, browse & search doctors (filters: specialty,
  fee, video/home visit, sort), doctor profiles + reviews, book appointments
  (date → slot → type → symptoms → payment method), booking confirmation with a
  QR-style code, manage appointments (upcoming/completed/cancelled, cancel),
  view prescriptions, edit profile.
- **Doctor:** panel with stats, appointment list, complete appointment +
  create a digital prescription.
- **Admin:** dashboard stats (doctors, patients, appointments, revenue,
  cancellation rate) and a recent-appointments table.
- **Cross-cutting:** JWT auth, PBKDF2 password hashing, role-based access
  control, light/dark theme, responsive Material-style UI, skeleton loaders,
  toasts, empty states.

## Project structure
```
mydocplus/
  run.py               # entry point: init db → seed → serve
  docs/                # design deliverables
    ARCHITECTURE.md  DATABASE.md  API.md  AUTH.md
  backend/
    server.py  router.py  auth.py  db.py  config.py
    schema.sql  seed.py
    handlers/          # auth, doctors, appointments, admin
  frontend/
    index.html  styles.css  app.js
```

## API
Full REST reference in [`docs/API.md`](docs/API.md). Base path `/api`.

## Roadmap (next slices)
Payments (Stripe/Razorpay), WebRTC video consultation, AI symptom→specialty
assistant, notifications (FCM/SMS/email), Google Maps, calendar sync, and the
production port to **Next.js + NestJS + PostgreSQL + Prisma** (the schema and API
contract already map 1:1 — see `docs/ARCHITECTURE.md`).

## Testing
The backend was verified end-to-end (auth, search/filter, slot generation,
booking with double-book protection, RBAC, prescriptions, reviews, admin stats).
Because the app is dependency-free, you can smoke-test with `curl`:

```bash
curl -s localhost:8000/api/doctors?sort=rating
```
