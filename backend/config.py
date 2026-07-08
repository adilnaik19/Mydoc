"""Central configuration for My Doc+."""
import os

# Server secret used to sign JWT-style tokens. Override in production.
SECRET = os.environ.get("MYDOCPLUS_SECRET", "dev-secret-change-me-in-production")

# Token lifetime in seconds (7 days).
TOKEN_TTL = 7 * 24 * 3600

# PBKDF2 iterations for password hashing.
PBKDF2_ITERATIONS = 200_000

# Server bind config.
HOST = os.environ.get("MYDOCPLUS_HOST", "0.0.0.0")
PORT = int(os.environ.get("MYDOCPLUS_PORT", "8000"))

# Paths.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.environ.get("MYDOCPLUS_DB", os.path.join(PROJECT_DIR, "mydocplus.db"))
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
SCHEMA_PATH = os.path.join(BASE_DIR, "schema.sql")
