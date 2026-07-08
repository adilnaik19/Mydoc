"""AI Symptom Assistant (rule-based, zero-dependency).

Maps a free-text symptom description to the most relevant medical specialty,
flags possible emergencies, and recommends doctors to book. This is a
transparent keyword/scoring model — not a diagnosis. A clear disclaimer is
always returned, and emergency red-flags are surfaced first.
"""
import re

import db
from router import ApiError

# Emergency red-flags -> always advise urgent/in-person care.
RED_FLAGS = [
    "chest pain", "chest tightness", "can't breathe", "cant breathe",
    "difficulty breathing", "shortness of breath", "unconscious", "fainted",
    "severe bleeding", "stroke", "slurred speech", "face drooping",
    "suicidal", "seizure", "not breathing", "blue lips", "severe burn",
    "poison", "overdose",
]

# specialty name -> keywords. Names must match seeded specialties.
SPECIALTY_KEYWORDS = {
    "Cardiology": ["heart", "chest", "palpitation", "palpitations", "bp",
                   "blood pressure", "hypertension", "cholesterol", "pulse"],
    "Dermatology": ["skin", "rash", "acne", "pimple", "itch", "itching",
                    "hair", "hair fall", "dandruff", "eczema", "psoriasis",
                    "mole", "spot", "allergy skin"],
    "Pediatrics": ["child", "baby", "infant", "toddler", "kid", "newborn",
                   "vaccination", "vaccine", "my son", "my daughter"],
    "Orthopedics": ["bone", "joint", "knee", "back pain", "fracture", "sprain",
                    "shoulder", "hip", "ankle", "arthritis", "spine",
                    "muscle", "sports injury"],
    "Neurology": ["headache", "migraine", "dizziness", "dizzy", "numbness",
                  "tingling", "memory", "epilepsy", "tremor", "vertigo",
                  "nerve"],
    "Gynecology": ["period", "periods", "menstrual", "pregnan", "pregnancy",
                   "vaginal", "menopause", "fertility", "pcos", "uterus"],
    "Dentistry": ["tooth", "teeth", "gum", "gums", "toothache", "cavity",
                  "dental", "jaw", "wisdom tooth"],
    "General Physician": ["fever", "cold", "cough", "flu", "sore throat",
                          "tired", "fatigue", "weakness", "vomit", "nausea",
                          "diarrhea", "stomach", "body ache", "infection",
                          "checkup", "check up"],
}

DISCLAIMER = (
    "This is an automated suggestion to help you choose a specialist, not a "
    "medical diagnosis. For any serious or worsening symptoms, please consult "
    "a doctor directly."
)


def _find_specialty_id(name):
    row = db.query_one("SELECT id FROM specialties WHERE name = ?", (name,))
    return row["id"] if row else None


def _recommend_doctors(specialty_id, limit=3):
    if not specialty_id:
        return []
    rows = db.query(
        "SELECT d.id, u.name AS name, s.name AS specialty, d.experience_years, "
        "d.consultation_fee, d.rating, d.reviews_count, d.hospital, d.city, "
        "d.video_consult, d.home_visit "
        "FROM doctors d JOIN users u ON u.id = d.user_id "
        "LEFT JOIN specialties s ON s.id = d.specialty_id "
        "WHERE d.specialty_id = ? ORDER BY d.rating DESC, d.reviews_count DESC LIMIT ?",
        (specialty_id, limit),
    )
    for r in rows:
        r["video_consult"] = bool(r["video_consult"])
        r["home_visit"] = bool(r["home_visit"])
    return rows


def triage(ctx):
    text = str(ctx.body.get("symptoms", "")).strip().lower()
    if not text:
        raise ApiError(400, "Please describe your symptoms")

    # 1) Emergency red-flag check.
    hit = next((f for f in RED_FLAGS if f in text), None)
    if hit:
        return 200, {
            "urgency": "emergency",
            "message": (
                "Your symptoms may need urgent attention. If this is a medical "
                "emergency, please call your local emergency number or go to the "
                "nearest emergency room now."
            ),
            "specialty": None,
            "doctors": [],
            "disclaimer": DISCLAIMER,
        }

    # 2) Score specialties by keyword matches (word-boundary aware).
    scores = {}
    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw), text):
                score += 1
        if score:
            scores[specialty] = score

    if not scores:
        gp_id = _find_specialty_id("General Physician")
        return 200, {
            "urgency": "routine",
            "message": (
                "I couldn't match your symptoms to a specific specialty. A "
                "General Physician is a good first step — they can assess you "
                "and refer you if needed."
            ),
            "specialty": {"id": gp_id, "name": "General Physician"},
            "doctors": _recommend_doctors(gp_id),
            "disclaimer": DISCLAIMER,
        }

    best = max(scores, key=scores.get)
    best_id = _find_specialty_id(best)
    # simple urgency heuristic
    urgency = "soon" if any(w in text for w in ["severe", "bad", "worse", "days", "week"]) else "routine"

    return 200, {
        "urgency": urgency,
        "message": f"Based on what you described, a **{best}** specialist is likely the best fit.",
        "specialty": {"id": best_id, "name": best},
        "matched": scores,
        "doctors": _recommend_doctors(best_id),
        "disclaimer": DISCLAIMER,
    }


def register(router):
    router.add("POST", "/api/ai/triage", triage)
