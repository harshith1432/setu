import sys, os
sys.path.insert(0, os.path.abspath('backend'))

from app.services.db_service import get_db_cursor

try:
    with get_db_cursor(dict_cursor=True) as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [r['table_name'] for r in cur.fetchall()]
        print(f"Connected to PostgreSQL successfully! Tables found: {len(tables)}")
        for t in tables:
            try:
                cur.execute(f"SELECT count(*) as c FROM {t}")
                c = cur.fetchone()['c']
                print(f"  - {t}: {c} rows")
            except Exception as e:
                print(f"  - {t}: (error counting: {e})")
except Exception as e:
    print("PostgreSQL connection check failed:", e)
