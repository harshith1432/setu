#!/usr/bin/env python3
"""
Standalone Database Pre-flight & Initialization Script for SeriCare / Setu.

Can be run before starting the web server or as a pre-deploy / release command in deployment:
Usage:
    python backend/init_db.py
"""

import os
import sys

# Ensure backend root is on Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.db_initializer import verify_and_ensure_database_ready

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    print("\n--- SeriCare / Setu Database Pre-Flight & Table Verification ---")
    result = verify_and_ensure_database_ready()
    print("--- Database Verification Complete ---\n")
