#!/usr/bin/env python3
"""My Doc+ entry point: initialize DB, seed sample data, and start the server.

Usage:
    python run.py
Environment:
    MYDOCPLUS_PORT   (default 8000)
    MYDOCPLUS_SECRET (JWT signing secret)
    MYDOCPLUS_DB     (sqlite file path)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

import db          # noqa: E402
import seed        # noqa: E402
from server import serve  # noqa: E402


def main():
    db.init_db()
    seed.seed()
    serve()


if __name__ == "__main__":
    main()
