"""Admin endpoints: dashboard stats and management listings."""
import db


def stats(ctx):
    total_doctors = db.query_one("SELECT COUNT(*) AS c FROM doctors")["c"]
    total_patients = db.query_one("SELECT COUNT(*) AS c FROM users WHERE role = 'patient'")["c"]
    total_appts = db.query_one("SELECT COUNT(*) AS c FROM appointments")["c"]
    revenue = db.query_one(
        "SELECT COALESCE(SUM(fee),0) AS s FROM appointments WHERE status IN ('confirmed','completed')"
    )["s"]

    by_status = {"pending": 0, "confirmed": 0, "completed": 0, "cancelled": 0}
    for r in db.query("SELECT status, COUNT(*) AS c FROM appointments GROUP BY status"):
        by_status[r["status"]] = r["c"]

    cancelled = by_status["cancelled"]
    cancellation_rate = round(cancelled / total_appts, 3) if total_appts else 0

    return 200, {
        "total_doctors": total_doctors,
        "total_patients": total_patients,
        "total_appointments": total_appts,
        "revenue": revenue,
        "cancellation_rate": cancellation_rate,
        "appointments_by_status": by_status,
    }


def doctors(ctx):
    return 200, db.query(
        "SELECT d.id, u.name, u.email, s.name AS specialty, d.city, d.consultation_fee, "
        "d.rating, d.reviews_count FROM doctors d JOIN users u ON u.id = d.user_id "
        "LEFT JOIN specialties s ON s.id = d.specialty_id ORDER BY d.rating DESC"
    )


def patients(ctx):
    return 200, db.query(
        "SELECT id, name, email, phone, created_at FROM users WHERE role = 'patient' "
        "ORDER BY created_at DESC"
    )


def appointments(ctx):
    return 200, db.query(
        "SELECT a.id, a.code, a.date, a.slot, a.type, a.status, a.fee, "
        "pu.name AS patient, du.name AS doctor "
        "FROM appointments a "
        "JOIN users pu ON pu.id = a.patient_id "
        "JOIN doctors d ON d.id = a.doctor_id "
        "JOIN users du ON du.id = d.user_id "
        "ORDER BY a.date DESC, a.slot DESC"
    )


def register(router):
    router.add("GET", "/api/admin/stats", stats, roles={"admin"})
    router.add("GET", "/api/admin/doctors", doctors, roles={"admin"})
    router.add("GET", "/api/admin/patients", patients, roles={"admin"})
    router.add("GET", "/api/admin/appointments", appointments, roles={"admin"})
