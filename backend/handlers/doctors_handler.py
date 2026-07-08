"""Doctor endpoints: list/search/filter, profile, availability slots, reviews."""
from datetime import datetime, timedelta, timezone

import db
from router import ApiError

DOCTOR_SELECT = """
    SELECT d.id, u.name AS name, s.name AS specialty, s.id AS specialty_id,
           d.qualification, d.experience_years, d.about, d.languages,
           d.consultation_fee, d.rating, d.reviews_count, d.hospital, d.city,
           d.photo, d.video_consult, d.home_visit
    FROM doctors d
    JOIN users u ON u.id = d.user_id
    LEFT JOIN specialties s ON s.id = d.specialty_id
"""


def _shape(row):
    row = dict(row)
    row["video_consult"] = bool(row["video_consult"])
    row["home_visit"] = bool(row["home_visit"])
    row["languages"] = [l.strip() for l in (row.get("languages") or "").split(",") if l.strip()]
    return row


def list_doctors(ctx):
    q = ctx.query
    where, params = [], []
    if q.get("q"):
        where.append("(u.name LIKE ? OR d.hospital LIKE ?)")
        params += [f"%{q['q']}%", f"%{q['q']}%"]
    if q.get("specialty"):
        where.append("d.specialty_id = ?")
        params.append(q["specialty"])
    if q.get("city"):
        where.append("d.city LIKE ?")
        params.append(f"%{q['city']}%")
    if q.get("min_rating"):
        where.append("d.rating >= ?")
        params.append(q["min_rating"])
    if q.get("max_fee"):
        where.append("d.consultation_fee <= ?")
        params.append(q["max_fee"])
    if q.get("video") in ("1", "true"):
        where.append("d.video_consult = 1")
    if q.get("home") in ("1", "true"):
        where.append("d.home_visit = 1")

    sql = DOCTOR_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)

    sort = q.get("sort")
    if sort == "fee":
        sql += " ORDER BY d.consultation_fee ASC"
    elif sort == "experience":
        sql += " ORDER BY d.experience_years DESC"
    else:  # default & 'rating'
        sql += " ORDER BY d.rating DESC, d.reviews_count DESC"

    return 200, [_shape(r) for r in db.query(sql, params)]


def get_doctor(ctx):
    did = ctx.param_int("id")
    row = db.query_one(DOCTOR_SELECT + " WHERE d.id = ?", (did,))
    if not row:
        raise ApiError(404, "Doctor not found")
    doc = _shape(row)
    doc["reviews"] = db.query(
        "SELECT r.rating, r.comment, r.created_at, u.name AS patient "
        "FROM reviews r JOIN users u ON u.id = r.patient_id "
        "WHERE r.doctor_id = ? ORDER BY r.created_at DESC LIMIT 10",
        (did,),
    )
    return 200, doc


def get_slots(ctx):
    did = ctx.param_int("id")
    date_str = ctx.query.get("date")
    if not date_str:
        raise ApiError(400, "date query param required (YYYY-MM-DD)")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ApiError(400, "Invalid date format, expected YYYY-MM-DD")

    weekday = d.weekday()  # 0=Mon
    templates = db.query(
        "SELECT * FROM doctor_slots WHERE doctor_id = ? AND weekday = ?",
        (did, weekday),
    )
    all_slots = []
    for t in templates:
        cur = datetime.strptime(t["start_time"], "%H:%M")
        end = datetime.strptime(t["end_time"], "%H:%M")
        step = timedelta(minutes=t["slot_minutes"])
        while cur < end:
            all_slots.append(cur.strftime("%H:%M"))
            cur += step

    booked = {
        r["slot"]
        for r in db.query(
            "SELECT slot FROM appointments WHERE doctor_id = ? AND date = ? "
            "AND status IN ('pending','confirmed')",
            (did, date_str),
        )
    }
    available = sorted(s for s in set(all_slots) if s not in booked)
    return 200, {"date": date_str, "slots": available}


def add_review(ctx):
    did = ctx.param_int("id")
    ctx.require("rating")
    rating = int(ctx.body["rating"])
    if rating < 1 or rating > 5:
        raise ApiError(400, "rating must be 1-5")
    if not db.query_one("SELECT id FROM doctors WHERE id = ?", (did,)):
        raise ApiError(404, "Doctor not found")
    rid = db.execute(
        "INSERT INTO reviews (doctor_id, patient_id, rating, comment, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (did, ctx.user["id"], rating, ctx.body.get("comment"), datetime.now(timezone.utc).isoformat()),
    )
    # recompute rollup
    agg = db.query_one(
        "SELECT AVG(rating) AS avg, COUNT(*) AS cnt FROM reviews WHERE doctor_id = ?", (did,)
    )
    db.execute(
        "UPDATE doctors SET rating = ?, reviews_count = ? WHERE id = ?",
        (round(agg["avg"], 1), agg["cnt"], did),
    )
    return 201, {"id": rid, "rating": rating, "comment": ctx.body.get("comment")}


def list_specialties(ctx):
    return 200, db.query("SELECT id, name, icon FROM specialties ORDER BY name")


def register(router):
    router.add("GET", "/api/specialties", list_specialties)
    router.add("GET", "/api/doctors", list_doctors)
    router.add("GET", "/api/doctors/:id", get_doctor)
    router.add("GET", "/api/doctors/:id/slots", get_slots)
    router.add("POST", "/api/doctors/:id/reviews", add_review, roles={"patient"})
