# My Doc+ — Database Schema (ERD)

SQLite for the MVP; the same model maps directly to PostgreSQL.

## 1. Entity-Relationship Diagram

```
+---------------+          +------------------+          +------------------+
|    users      |          |    doctors       |          |   specialties    |
+---------------+          +------------------+          +------------------+
| id (PK)       |1        1| id (PK)          |* ------ 1| id (PK)          |
| role          |----------| user_id (FK)     |          | name             |
| name          |          | specialty_id (FK)|--------->| icon             |
| email (UQ)    |          | qualification    |          +------------------+
| phone         |          | experience_years |
| password_hash |          | about            |
| gender        |          | languages        |
| age           |          | consultation_fee |
| blood_group   |          | rating           |
| address       |          | reviews_count    |
| created_at    |          | hospital         |
+-------+-------+          | city             |
        |                  | photo            |
        | 1                | video_consult    |
        |                  | home_visit       |
        |                  +---------+--------+
        |                            | 1
        |                            |
        | *                          | *
+-------v--------------------------------------v---------+
|                     appointments                        |
+---------------------------------------------------------+
| id (PK)                                                 |
| code            (human-readable, e.g. APT-8F3K2A)       |
| patient_id (FK -> users.id)                             |
| doctor_id  (FK -> doctors.id)                           |
| date            (YYYY-MM-DD)                            |
| slot            (HH:MM)                                 |
| type            (video | clinic | home)                 |
| symptoms                                                |
| status          (pending|confirmed|completed|cancelled) |
| fee                                                     |
| created_at                                              |
+-----------------------+---------------------------------+
                        | 1
                        | 0..1
                +-------v-----------+
                |   prescriptions   |
                +-------------------+
                | id (PK)           |
                | appointment_id FK |
                | medicines (JSON)  |
                | advice            |
                | tests             |
                | follow_up_date    |
                | created_at        |
                +-------------------+

+------------------+
|  doctor_slots    |   (availability template per doctor)
+------------------+
| id (PK)          |
| doctor_id (FK)   |
| weekday (0-6)    |
| start_time       |
| end_time         |
| slot_minutes     |
+------------------+

+------------------+
|    reviews       |
+------------------+
| id (PK)          |
| doctor_id (FK)   |
| patient_id (FK)  |
| rating (1-5)     |
| comment          |
| created_at       |
+------------------+
```

## 2. Table definitions (summary)

### users
Single table for all roles (`patient`, `doctor`, `admin`). Doctor-specific
professional fields live in `doctors`, linked by `user_id`.

| column | type | notes |
|--------|------|-------|
| id | INTEGER PK | autoincrement |
| role | TEXT | `patient` \| `doctor` \| `admin` |
| name | TEXT | required |
| email | TEXT UNIQUE | login identifier |
| phone | TEXT | optional |
| password_hash | TEXT | `iterations$salt$hash` (PBKDF2) |
| gender | TEXT | optional |
| age | INTEGER | optional |
| blood_group | TEXT | optional |
| address | TEXT | optional |
| created_at | TEXT | ISO timestamp |

### specialties
Lookup table (Cardiology, Dermatology, …) with an icon key for the UI.

### doctors
Professional profile linked to a `users` row with `role='doctor'`.
Holds specialty, fee, experience, rating, hospital/city, and capability flags
(`video_consult`, `home_visit`).

### appointments
Core booking entity. `code` is a shareable, human-readable id used for the
QR/confirmation. `status` drives the patient/doctor lifecycle.

### prescriptions
Optional 1:1 record attached to a completed appointment. `medicines` is a JSON
array of `{name, dosage, frequency, duration}`.

### doctor_slots
Availability template (per weekday). The API expands these into concrete,
bookable time slots for a given date, minus already-booked ones.

### reviews
Patient ratings that roll up into `doctors.rating` / `reviews_count`.

## 3. Indexes
- `users(email)` unique.
- `appointments(patient_id)`, `appointments(doctor_id)`, `appointments(date)`.
- `doctors(specialty_id)`, `doctors(city)`.

## 4. Referential integrity
Foreign keys enforced (`PRAGMA foreign_keys = ON`). Deleting a user cascades to
their doctor profile and appointments in the production model; the MVP uses soft
guards to keep sample data stable.
