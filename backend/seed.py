"""Seed the database with specialties, doctors, patients, and an admin.

Idempotent: only seeds when the users table is empty.
"""
from datetime import datetime, timezone

import auth
import db

NOW = datetime.now(timezone.utc).isoformat()

SPECIALTIES = [
    ("Cardiology", "heart"),
    ("Dermatology", "skin"),
    ("Pediatrics", "child"),
    ("Orthopedics", "bone"),
    ("Neurology", "brain"),
    ("General Physician", "stethoscope"),
    ("Gynecology", "female"),
    ("Dentistry", "tooth"),
]

# (name, email, specialty_idx, qualification, years, about, languages, fee,
#  rating, reviews, hospital, city, video, home)
DOCTORS = [
    ("Dr. Neha Sharma", "neha@mydocplus.dev", 0, "MBBS, MD (Cardiology)", 12,
     "Interventional cardiologist focused on preventive heart care.",
     "English, Hindi, Marathi", 700, 4.8, 214, "Apollo Hospital", "Mumbai", 1, 0),
    ("Dr. Arjun Mehta", "arjun@mydocplus.dev", 5, "MBBS", 8,
     "General physician for everyday illnesses and health check-ups.",
     "English, Hindi", 400, 4.6, 180, "Fortis Clinic", "Delhi", 1, 1),
    ("Dr. Priya Nair", "priya@mydocplus.dev", 1, "MBBS, MD (Dermatology)", 10,
     "Skin, hair and cosmetic dermatology specialist.",
     "English, Malayalam, Hindi", 600, 4.7, 156, "SkinCare Clinic", "Bangalore", 1, 0),
    ("Dr. Rakesh Iyer", "rakesh@mydocplus.dev", 3, "MBBS, MS (Ortho)", 15,
     "Joint replacement and sports injury surgeon.",
     "English, Tamil, Hindi", 800, 4.5, 98, "Global Ortho Center", "Chennai", 0, 0),
    ("Dr. Sara Khan", "sara@mydocplus.dev", 2, "MBBS, MD (Pediatrics)", 9,
     "Child specialist with a gentle, parent-friendly approach.",
     "English, Hindi, Urdu", 500, 4.9, 302, "Rainbow Children's", "Hyderabad", 1, 1),
    ("Dr. Vikram Rao", "vikram@mydocplus.dev", 4, "MBBS, DM (Neurology)", 18,
     "Neurologist treating headaches, epilepsy and stroke.",
     "English, Telugu, Hindi", 900, 4.4, 77, "NeuroLife Hospital", "Hyderabad", 1, 0),
    ("Dr. Ananya Das", "ananya@mydocplus.dev", 6, "MBBS, MD (Gynecology)", 11,
     "Women's health, pregnancy care and fertility guidance.",
     "English, Bengali, Hindi", 650, 4.7, 189, "Motherhood Clinic", "Kolkata", 1, 1),
    ("Dr. Karan Patel", "karan@mydocplus.dev", 7, "BDS, MDS", 7,
     "Cosmetic dentistry, root canal and oral surgery.",
     "English, Gujarati, Hindi", 350, 4.6, 143, "SmileCare Dental", "Ahmedabad", 0, 0),
]

# weekday templates: Mon-Fri morning + evening
def _default_slots(doctor_id):
    rows = []
    for wd in range(0, 6):  # Mon-Sat
        rows.append((doctor_id, wd, "09:00", "12:00", 30))
        rows.append((doctor_id, wd, "17:00", "20:00", 30))
    return rows


def seed():
    db.init_db()
    if db.query_one("SELECT id FROM users LIMIT 1"):
        print("Database already seeded; skipping.")
        return

    # specialties
    spec_ids = []
    for name, icon in SPECIALTIES:
        sid = db.execute("INSERT INTO specialties (name, icon) VALUES (?, ?)", (name, icon))
        spec_ids.append(sid)

    # admin
    db.execute(
        "INSERT INTO users (role, name, email, password_hash, created_at) VALUES ('admin', ?, ?, ?, ?)",
        ("Admin", "admin@mydocplus.dev", auth.hash_password("admin123"), NOW),
    )

    # doctors (user + profile + slots)
    for (name, email, sidx, qual, years, about, langs, fee, rating, revs, hosp, city, video, home) in DOCTORS:
        uid = db.execute(
            "INSERT INTO users (role, name, email, phone, password_hash, created_at) "
            "VALUES ('doctor', ?, ?, ?, ?, ?)",
            (name, email, "+91-90000-00000", auth.hash_password("doctor123"), NOW),
        )
        did = db.execute(
            "INSERT INTO doctors (user_id, specialty_id, qualification, experience_years, about, "
            "languages, consultation_fee, rating, reviews_count, hospital, city, photo, video_consult, home_visit) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (uid, spec_ids[sidx], qual, years, about, langs, fee, rating, revs, hosp, city, None, video, home),
        )
        for s in _default_slots(did):
            db.execute(
                "INSERT INTO doctor_slots (doctor_id, weekday, start_time, end_time, slot_minutes) "
                "VALUES (?, ?, ?, ?, ?)", s,
            )

    # sample patient
    db.execute(
        "INSERT INTO users (role, name, email, phone, password_hash, age, gender, blood_group, created_at) "
        "VALUES ('patient', ?, ?, ?, ?, ?, ?, ?, ?)",
        ("Asha Rao", "asha@mydocplus.dev", "+91-98888-88888",
         auth.hash_password("patient123"), 29, "Female", "O+", NOW),
    )

    print("Seed complete: 1 admin, {} doctors, 1 patient.".format(len(DOCTORS)))


if __name__ == "__main__":
    seed()
