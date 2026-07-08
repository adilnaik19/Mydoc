-- My Doc+ schema (SQLite). Maps 1:1 to PostgreSQL for production.
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    role          TEXT NOT NULL DEFAULT 'patient',   -- patient | doctor | admin
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    phone         TEXT,
    password_hash TEXT NOT NULL,
    gender        TEXT,
    age           INTEGER,
    blood_group   TEXT,
    address       TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS specialties (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT
);

CREATE TABLE IF NOT EXISTS doctors (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    specialty_id     INTEGER REFERENCES specialties(id),
    qualification    TEXT,
    experience_years INTEGER DEFAULT 0,
    about            TEXT,
    languages        TEXT,               -- comma separated
    consultation_fee INTEGER DEFAULT 0,
    rating           REAL DEFAULT 0,
    reviews_count    INTEGER DEFAULT 0,
    hospital         TEXT,
    city             TEXT,
    photo            TEXT,
    video_consult    INTEGER DEFAULT 0,  -- boolean
    home_visit       INTEGER DEFAULT 0   -- boolean
);

CREATE TABLE IF NOT EXISTS doctor_slots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id    INTEGER NOT NULL REFERENCES doctors(id),
    weekday      INTEGER NOT NULL,       -- 0=Mon .. 6=Sun
    start_time   TEXT NOT NULL,          -- HH:MM
    end_time     TEXT NOT NULL,          -- HH:MM
    slot_minutes INTEGER NOT NULL DEFAULT 30
);

CREATE TABLE IF NOT EXISTS appointments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT NOT NULL UNIQUE,
    patient_id INTEGER NOT NULL REFERENCES users(id),
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id),
    date       TEXT NOT NULL,            -- YYYY-MM-DD
    slot       TEXT NOT NULL,            -- HH:MM
    type       TEXT NOT NULL DEFAULT 'clinic',  -- video | clinic | home
    symptoms   TEXT,
    status     TEXT NOT NULL DEFAULT 'confirmed', -- pending|confirmed|completed|cancelled
    fee        INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prescriptions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id INTEGER NOT NULL REFERENCES appointments(id),
    medicines      TEXT,                 -- JSON array
    advice         TEXT,
    tests          TEXT,
    follow_up_date TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id  INTEGER NOT NULL REFERENCES doctors(id),
    patient_id INTEGER NOT NULL REFERENCES users(id),
    rating     INTEGER NOT NULL,
    comment    TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_appt_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appt_doctor  ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_appt_date    ON appointments(date);
CREATE INDEX IF NOT EXISTS idx_doc_specialty ON doctors(specialty_id);
CREATE INDEX IF NOT EXISTS idx_doc_city      ON doctors(city);
