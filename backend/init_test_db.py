import os
import sys
import time

import os
import sys

def main():
    print("Initializing Setu Pure Firebase Cloud Firestore & resilient datastores...")

    try:
        from app.services.firestore_service import firestore_service
        print(f"Cloud Firestore available: {firestore_service.is_available}")

        from app.services.db_service import init_db
        from app.services.enterprise_db import init_enterprise_tables
        from app.services.org_employee_db import init_org_employee_tables

        print("Initializing core baseline collections...")
        init_db()
        print("Initializing enterprise platform catalogue...")
        init_enterprise_tables()
        print("Initializing organizational RBAC & employee directory...")
        init_org_employee_tables()
        print("All Pure Firebase collections and local datastores successfully initialized!")
    except Exception as e:
        import traceback
        print(f"FAILED during database initialization: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
