import os
import sys
import time

def main():
    db_url = os.getenv("DATABASE_URL", "postgresql://setu_user:setu_password@127.0.0.1:5433/setu")
    print(f"Connecting to database: {db_url}")

    import psycopg2
    connected = False
    for attempt in range(20):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            connected = True
            print("PostgreSQL connection confirmed!")
            break
        except Exception as e:
            print(f"Waiting for PostgreSQL... (attempt {attempt+1}/20): {e}")
            time.sleep(1)

    if not connected:
        print("ERROR: Could not connect to PostgreSQL")
        sys.exit(1)

    import traceback
    try:
        from app.services.db_service import init_db
        from app.services.enterprise_db import init_enterprise_tables
        from app.services.org_employee_db import init_org_employee_tables

        print("Initializing core database...")
        init_db()
        print("Initializing enterprise database...")
        init_enterprise_tables()
        print("Initializing org employee database...")
        init_org_employee_tables()
        print("All tables successfully initialized and seeded!")
    except Exception as e:
        print(f"FAILED during table initialization: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
