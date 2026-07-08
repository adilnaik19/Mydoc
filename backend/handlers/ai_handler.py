"""AI Symptom Assistant (rule-based, zero-dependency).

Maps a free-text symptom description to the most relevant medical specialty,
flags possible emergencies, and recommends doctors to book. This is a
transparent keyword/scoring model — not a diagnosis. A clear disclaimer is
always returned, and emergency red-flags are surfaced first.
"""
import re

import ai_client
import db
from router import ApiError

SYSTEM_PROMPT = (
    "You are the My Doc+ health assistant, embedded in a doctor-appointment app. "
    "Help users understand symptoms, general health and wellness topics, common "
    "medicines, and how to use the app to find and book doctors. "
    "Guidelines: Be warm, clear and concise. You are NOT a substitute for a "
    "qualified doctor — never give a definitive diagnosis or prescribe specific "
    "prescription medication; instead explain possibilities in general terms and "
    "encourage booking a consultation. If the user describes a possible emergency "
    "(e.g. chest pain, trouble breathing, severe bleeding, stroke signs, thoughts "
    "of self-harm), tell them to seek emergency care immediately. When helpful, "
    "suggest which type of specialist (e.g. Cardiologist, Dermatologist) they "
    "should see. You may answer general non-medical questions briefly, but gently "
    "steer back to health when appropriate."
)

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


EMERGENCY_MESSAGE = (
    "⚠️ This could be a medical emergency. Please call your local emergency "
    "number or go to the nearest emergency room right away. I can't help with "
    "emergencies, but real help is available now."
)


def _detect_red_flag(text):
    text = text.lower()
    return next((f for f in RED_FLAGS if f in text), None)


def _best_specialty(text):
    """Return (name, id, scores) for the best keyword match, or (None, None, {})."""
    text = text.lower()
    scores = {}
    for specialty, keywords in SPECIALTY_KEYWORDS.items():
        score = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw), text))
        if score:
            scores[specialty] = score
    if not scores:
        return None, None, {}
    best = max(scores, key=scores.get)
    return best, _find_specialty_id(best), scores


def _fallback_reply(text):
    """Compose a helpful text answer without an LLM (basic mode)."""
    best, best_id, _ = _best_specialty(text)
    if best:
        docs = _recommend_doctors(best_id, limit=2)
        names = ", ".join(d["name"] for d in docs) if docs else ""
        reply = (
            f"Based on what you described, a **{best}** specialist is likely the "
            f"best fit. You can search {best} in the app to book an appointment."
        )
        if names:
            reply += f" Highly-rated options: {names}."
    else:
        reply = (
            "I couldn't match that to a specific specialty. A **General "
            "Physician** is a good first step — they can assess you and refer "
            "you if needed. Use *Find Doctors* to book one."
        )
    reply += (
        "\n\n_Tip: set an AI API key (MYDOCPLUS_AI_KEY) to unlock full "
        "conversational answers._"
    )
    return reply


def triage(ctx):
    text = str(ctx.body.get("symptoms", "")).strip().lower()
    if not text:
        raise ApiError(400, "Please describe your symptoms")

    # 1) Emergency red-flag check.
    hit = _detect_red_flag(text)
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


def chat(ctx):
    """Conversational assistant. Uses a real LLM when configured, else falls
    back to the rule-based responder. Emergencies are always short-circuited."""
    messages = ctx.body.get("messages")
    if not messages:
        single = str(ctx.body.get("message", "")).strip()
        if not single:
            raise ApiError(400, "Please type a message")
        messages = [{"role": "user", "content": single}]

    # normalize + find the latest user message
    messages = [
        {"role": ("assistant" if m.get("role") == "assistant" else "user"),
         "content": str(m.get("content", "")).strip()}
        for m in messages if str(m.get("content", "")).strip()
    ]
    if not messages:
        raise ApiError(400, "Please type a message")
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")

    # Safety: hard stop on emergencies regardless of AI availability.
    if _detect_red_flag(last_user):
        return 200, {"mode": "safety", "reply": EMERGENCY_MESSAGE, "emergency": True}

    if ai_client.is_enabled():
        try:
            reply = ai_client.chat(messages, system=SYSTEM_PROMPT)
            return 200, {"mode": "ai", "reply": reply}
        except Exception as e:  # noqa: BLE001 — degrade gracefully
            return 200, {
                "mode": "basic",
                "reply": _fallback_reply(last_user),
                "note": "AI temporarily unavailable: " + str(e)[:140],
            }

    return 200, {"mode": "basic", "reply": _fallback_reply(last_user)}


def status(ctx):
    return 200, {"ai_enabled": ai_client.is_enabled(),
                 "provider": ai_client.PROVIDER if ai_client.is_enabled() else None}


def register(router):
    router.add("POST", "/api/ai/triage", triage)
    router.add("POST", "/api/ai/chat", chat)
    router.add("GET", "/api/ai/status", status)
