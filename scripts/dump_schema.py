import sys, os
sys.path.insert(0, os.path.abspath('backend'))
from app.services.db_service import get_db_cursor
import json

schema_info = {}

with get_db_cursor(dict_cursor=True) as cur:
    # 1. Get all public tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [r['table_name'] for r in cur.fetchall()]
    
    for t in tables:
        # Columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (t,))
        cols = cur.fetchall()
        
        # Primary key
        cur.execute("""
            SELECT c.column_name
            FROM information_schema.table_constraints tc 
            JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) 
            JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
              AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
            WHERE tc.constraint_type = 'PRIMARY KEY' and tc.table_name = %s;
        """, (t,))
        pks = [r['column_name'] for r in cur.fetchall()]
        
        # Foreign keys
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = %s;
        """, (t,))
        fks = cur.fetchall()

        # Row count
        try:
            cur.execute(f"SELECT count(*) as c FROM {t}")
            cnt = cur.fetchone()['c']
        except Exception:
            cnt = 0

        schema_info[t] = {
            'columns': cols,
            'primary_key': pks,
            'foreign_keys': fks,
            'count': cnt
        }

with open('scripts/postgres_schema_dump.json', 'w', encoding='utf-8') as f:
    json.dump(schema_info, f, default=str, indent=2)

print(f"Schema dump written successfully for {len(schema_info)} tables.")
