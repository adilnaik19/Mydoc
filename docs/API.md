# My Doc+ — API Specification

Base URL: `/api`
All requests/responses are JSON. Protected endpoints require
`Authorization: Bearer <token>`.

## Conventions
- Success: `2xx` with a JSON body.
- Error: `{ "error": "message" }` with `4xx`/`5xx`.
- Timestamps are ISO-8601 strings.
- Roles: `patient`, `doctor`, `admin`.

---

## Auth

### POST /api/auth/signup
Create a patient account.
```json
Request:  { "name": "Asha R", "email": "asha@x.com", "password": "secret12", "phone": "+91..." }
Response: 201 { "token": "<jwt>", "user": { "id": 5, "name": "Asha R", "role": "patient", "email": "asha@x.com" } }
```

### POST /api/auth/login
Authenticate any role.
```json
Request:  { "email": "asha@x.com", "password": "secret12" }
Response: 200 { "token": "<jwt>", "user": { ... } }
```

### GET /api/auth/me   *(auth)*
Return the current user's profile.
```json
Response: 200 { "id": 5, "name": "Asha R", "role": "patient", "email": "...", "phone": "...", "age": null, ... }
```

### PUT /api/auth/me   *(auth)*
Update editable profile fields (name, phone, age, gender, blood_group, address).

---

## Specialties

### GET /api/specialties
```json
Response: 200 [ { "id": 1, "name": "Cardiology", "icon": "heart" }, ... ]
```

---

## Doctors

### GET /api/doctors
List / search doctors. All query params optional and combinable.

| param | example | effect |
|-------|---------|--------|
| `q` | `?q=sharma` | match name / hospital |
| `specialty` | `?specialty=2` | filter by specialty id |
| `city` | `?city=Mumbai` | filter by city |
| `min_rating` | `?min_rating=4` | rating floor |
| `max_fee` | `?max_fee=600` | fee ceiling |
| `video` | `?video=1` | offers video consult |
| `home` | `?home=1` | offers home visit |
| `sort` | `?sort=rating` \| `fee` \| `experience` | ordering |

```json
Response: 200 [
  { "id": 3, "name": "Dr. Neha Sharma", "specialty": "Cardiology",
    "experience_years": 12, "consultation_fee": 500, "rating": 4.7,
    "reviews_count": 214, "hospital": "Apollo", "city": "Mumbai",
    "photo": "...", "video_consult": true, "home_visit": false }, ...
]
```

### GET /api/doctors/:id
Full doctor profile including about, languages, qualifications, and recent reviews.

### GET /api/doctors/:id/slots?date=YYYY-MM-DD
Available time slots for a date (template minus booked).
```json
Response: 200 { "date": "2026-07-10", "slots": ["09:00","09:30","10:00", ...] }
```

---

## Appointments

### POST /api/appointments   *(auth: patient)*
```json
Request:  { "doctor_id": 3, "date": "2026-07-10", "slot": "10:00",
            "type": "video", "symptoms": "chest pain 2 days" }
Response: 201 { "id": 12, "code": "APT-8F3K2A", "status": "confirmed",
                "fee": 500, "doctor": { ... }, "date": "...", "slot": "..." }
```

### GET /api/appointments   *(auth)*
Returns the caller's appointments (patient sees theirs; doctor sees theirs).
Optional `?status=upcoming|completed|cancelled`.

### GET /api/appointments/:id   *(auth)*
Single appointment detail (must belong to caller or be admin/doctor of record).

### POST /api/appointments/:id/cancel   *(auth)*
Cancel an appointment (patient or doctor of record).

### POST /api/appointments/:id/complete   *(auth: doctor)*
Mark completed; optionally attach a prescription.
```json
Request: { "prescription": { "medicines": [ { "name":"Aspirin","dosage":"75mg","frequency":"OD","duration":"5 days" } ],
           "advice": "Rest, hydrate", "tests": "ECG", "follow_up_date": "2026-07-20" } }
```

---

## Reviews

### POST /api/doctors/:id/reviews   *(auth: patient)*
```json
Request:  { "rating": 5, "comment": "Very helpful" }
Response: 201 { "id": 9, "rating": 5, "comment": "..." }
```

---

## Admin

### GET /api/admin/stats   *(auth: admin)*
```json
Response: 200 {
  "total_doctors": 8, "total_patients": 25, "total_appointments": 40,
  "revenue": 18500, "cancellation_rate": 0.1,
  "appointments_by_status": { "confirmed": 20, "completed": 16, "cancelled": 4 }
}
```

### GET /api/admin/doctors | /api/admin/patients | /api/admin/appointments   *(auth: admin)*
Paginated listings for management tables.

---

## Status codes
| code | meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 400 | Validation error |
| 401 | Missing/invalid token |
| 403 | Authenticated but wrong role |
| 404 | Not found |
| 409 | Conflict (e.g. slot already booked, email in use) |
