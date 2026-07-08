"""Auth endpoints: signup, login, me (get/update)."""
from datetime import datetime, timezone

import auth
import db
from router import ApiError

EDITABLE = ("name", "phone", "age", "gender", "blood_group", "address")


def _public_user(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "phone": row.get("phone"),
        "age": row.get("age"),
        "gender": row.get("gender"),
        "blood_group": row.get("blood_group"),
        "address": row.get("address"),
    }


def signup(ctx):
    ctx.require("name", "email", "password")
    email = str(ctx.body["email"]).strip().lower()
    password = str(ctx.body["password"])
    if len(password) < 6:
        raise ApiError(400, "Password must be at least 6 characters")
    if db.query_one("SELECT id FROM users WHERE email = ?", (email,)):
        raise ApiError(409, "Email already registered")
    uid = db.execute(
        "INSERT INTO users (role, name, email, phone, password_hash, created_at) "
        "VALUES ('patient', ?, ?, ?, ?, ?)",
        (
            str(ctx.body["name"]).strip(),
            email,
            ctx.body.get("phone"),
            auth.hash_password(password),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    user = db.query_one("SELECT * FROM users WHERE id = ?", (uid,))
    return 201, {"token": auth.create_token(uid, "patient"), "user": _public_user(user)}


def login(ctx):
    ctx.require("email", "password")
    email = str(ctx.body["email"]).strip().lower()
    user = db.query_one("SELECT * FROM users WHERE email = ?", (email,))
    if not user or not auth.verify_password(str(ctx.body["password"]), user["password_hash"]):
        raise ApiError(401, "Invalid email or password")
    return 200, {"token": auth.create_token(user["id"], user["role"]), "user": _public_user(user)}


def me(ctx):
    return 200, _public_user(ctx.user)


def update_me(ctx):
    updates = {k: ctx.body[k] for k in EDITABLE if k in ctx.body}
    if updates:
        cols = ", ".join(f"{k} = ?" for k in updates)
        db.execute(f"UPDATE users SET {cols} WHERE id = ?", (*updates.values(), ctx.user["id"]))
    user = db.query_one("SELECT * FROM users WHERE id = ?", (ctx.user["id"],))
    return 200, _public_user(user)


def register(router):
    router.add("POST", "/api/auth/signup", signup)
    router.add("POST", "/api/auth/login", login)
    router.add("GET", "/api/auth/me", me, roles={"patient", "doctor", "admin"})
    router.add("PUT", "/api/auth/me", update_me, roles={"patient", "doctor", "admin"})
