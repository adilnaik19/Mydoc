"""Appointment endpoints: book, list, detail, cancel, complete (+prescription)."""
import json
import secrets
from datetime import datetime, timezone

import db
from router import ApiError

VALID_TYPES = {"video", "clinic", "home"}


def _gen_code():
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "APT-" + "".join(secrets.choice(alphabet) for _ in range(6))


def _appt_view(row):
    row = dict(row)
    doc = db.query_one(
        "SELECT d.id, u.name AS name, s.name AS specialty, d.hospital, d.city, d.photo "
        "FROM doctors d JOIN users u ON u.id = d.user_id "
        "LEFT JOIN specialties s ON s.id = d.specialty_id WHERE d.id = ?",
        (row["doctor_id"],),
    )
    patient = db.query_one("SELECT name, phone, age, gender FROM users WHERE id = ?", (row["patient_id"],))
    presc = db.query_one("SELECT * FROM prescriptions WHERE appointment_id = ?", (row["id"],))
    if presc:
        presc = dict(presc)
        try:
            presc["medicines"] = json.loads(presc.get("medicines") or "[]")
        except json.JSONDecodeError:
            presc["medicines"] = []
    return {
        "id": row["id"],
        "code": row["code"],
        "date": row["date"],
        "slot": row["slot"],
        "type": row["type"],
        "symptoms": row["symptoms"],
        "status": row["status"],
        "fee": row["fee"],
        "created_at": row["created_at"],
        "doctor": doc,
        "patient": patient,
        "prescription": presc,
    }


def book(ctx):
    ctx.require("doctor_id", "date", "slot")
    doctor_id = int(ctx.body["doctor_id"])
    date_str = str(ctx.body["date"])
    slot = str(ctx.body["slot"])
    appt_type = ctx.body.get("type", "clinic")
    if appt_type not in VALID_TYPES:
        raise ApiError(400, f"type must be one of {sorted(VALID_TYPES)}")

    doctor = db.query_one("SELECT * FROM doctors WHERE id = ?", (doctor_id,))
    if not doctor:
        raise ApiError(404, "Doctor not found")

    # prevent double-booking
    clash = db.query_one(
        "SELECT id FROM appointments WHERE doctor_id = ? AND date = ? AND slot = ? "
        "AND status IN ('pending','confirmed')",
        (doctor_id, date_str, slot),
    )
    if clash:
        raise ApiError(409, "That slot is already booked")

    code = _gen_code()
    aid = db.execute(
        "INSERT INTO appointments (code, patient_id, doctor_id, date, slot, type, symptoms, status, fee, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, 'confirmed', ?, ?)",
        (
            code, ctx.user["id"], doctor_id, date_str, slot, appt_type,
            ctx.body.get("symptoms"), doctor["consultation_fee"],
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    row = db.query_one("SELECT * FROM appointments WHERE id = ?", (aid,))
    return 201, _appt_view(row)


def list_appointments(ctx):
    user = ctx.user
    status = ctx.query.get("status")

    if user["role"] == "patient":
        base = "SELECT * FROM appointments WHERE patient_id = ?"
        params = [user["id"]]
    elif user["role"] == "doctor":
        doc = db.query_one("SELECT id FROM doctors WHERE user_id = ?", (user["id"],))
        if not doc:
            return 200, []
        base = "SELECT * FROM appointments WHERE doctor_id = ?"
        params = [doc["id"]]
    else:  # admin
        base = "SELECT * FROM appointments WHERE 1=1"
        params = []

    if status == "upcoming":
        base += " AND status IN ('pending','confirmed')"
    elif status in ("completed", "cancelled"):
        base += " AND status = ?"
        params.append(status)

    base += " ORDER BY date DESC, slot DESC"
    rows = db.query(base, params)
    return 200, [_appt_view(r) for r in rows]


def _load_owned(ctx):
    aid = ctx.param_int("id")
    row = db.query_one("SELECT * FROM appointments WHERE id = ?", (aid,))
    if not row:
        raise ApiError(404, "Appointment not found")
    user = ctx.user
    if user["role"] == "admin":
        return row
    if user["role"] == "patient" and row["patient_id"] == user["id"]:
        return row
    if user["role"] == "doctor":
        doc = db.query_one("SELECT id FROM doctors WHERE user_id = ?", (user["id"],))
        if doc and row["doctor_id"] == doc["id"]:
            return row
    raise ApiError(403, "Not your appointment")


def get_appointment(ctx):
    return 200, _appt_view(_load_owned(ctx))


def cancel(ctx):
    row = _load_owned(ctx)
    if row["status"] in ("completed", "cancelled"):
        raise ApiError(409, f"Cannot cancel a {row['status']} appointment")
    db.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (row["id"],))
    return 200, _appt_view(db.query_one("SELECT * FROM appointments WHERE id = ?", (row["id"],)))


def complete(ctx):
    row = _load_owned(ctx)
    if ctx.user["role"] != "doctor":
        raise ApiError(403, "Only the doctor can complete an appointment")
    if row["status"] == "cancelled":
        raise ApiError(409, "Cannot complete a cancelled appointment")
    db.execute("UPDATE appointments SET status = 'completed' WHERE id = ?", (row["id"],))

    presc = ctx.body.get("prescription")
    if presc:
        db.execute(
            "INSERT INTO prescriptions (appointment_id, medicines, advice, tests, follow_up_date, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                row["id"],
                json.dumps(presc.get("medicines", [])),
                presc.get("advice"),
                presc.get("tests"),
                presc.get("follow_up_date"),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    return 200, _appt_view(db.query_one("SELECT * FROM appointments WHERE id = ?", (row["id"],)))


def register(router):
    router.add("POST", "/api/appointments", book, roles={"patient"})
    router.add("GET", "/api/appointments", list_appointments, roles={"patient", "doctor", "admin"})
    router.add("GET", "/api/appointments/:id", get_appointment, roles={"patient", "doctor", "admin"})
    router.add("POST", "/api/appointments/:id/cancel", cancel, roles={"patient", "doctor", "admin"})
    router.add("POST", "/api/appointments/:id/complete", complete, roles={"doctor"})
