"""
Organization, Employee, Department, Role & Permission Database Service for SeriCare / Setu.
Provides PostgreSQL schema migrations, data queries, and security enforcement for:
- Organizations (Multi-tenant directory & profile)
- Departments & Circular Reporting Hierarchy Prevention
- Roles, System Templates, and Granular Permissions
- Employees, Onboarding Invitations, and Token Lifecycle
- Resource-Level Access Scopes (Assigned, Department, Organization)
"""

import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from app.services.db_service import get_db_cursor
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

# ==============================================================================
# PERMISSION DEFINITIONS
# ==============================================================================

SYSTEM_PERMISSIONS = [
    # Organization
    {"code": "org:read", "name": "View Organization", "category": "Organization", "description": "View organization details and profiles"},
    {"code": "org:write", "name": "Manage Organization Settings", "category": "Organization", "description": "Edit organization profile, branding and settings"},
    {"code": "org:subscriptions", "name": "Manage Subscriptions", "category": "Organization", "description": "Assign or upgrade organizational subscription plans"},
    
    # Users & Employees
    {"code": "users:read", "name": "View Users", "category": "Users", "description": "Browse employee directory and view user profiles"},
    {"code": "users:invite", "name": "Invite Users", "category": "Users", "description": "Issue secure onboarding invitations to new employees"},
    {"code": "users:write", "name": "Edit Users", "category": "Users", "description": "Modify employee records, departments, and designations"},
    {"code": "users:suspend", "name": "Suspend Users", "category": "Users", "description": "Activate, suspend, or revoke employee accounts"},
    {"code": "users:roles", "name": "Assign Roles", "category": "Users", "description": "Assign authorized roles to employees"},
    
    # Roles & Permissions
    {"code": "roles:read", "name": "View Roles", "category": "Roles", "description": "View system role templates and permissions"},
    {"code": "roles:write", "name": "Manage Custom Roles", "category": "Roles", "description": "Create, modify, and delete custom organizational roles"},
    {"code": "roles:assign", "name": "Assign Permitted Roles", "category": "Roles", "description": "Grant permitted roles to subordinate team members"},
    
    # Farmers and Sheds
    {"code": "farmers:read", "name": "View Farmers", "category": "Farmers & Sheds", "description": "View enrolled farmers and farm records"},
    {"code": "farmers:write", "name": "Manage Farmers", "category": "Farmers & Sheds", "description": "Create and edit farmer accounts and setups"},
    {"code": "sheds:read", "name": "View Assigned Sheds", "category": "Farmers & Sheds", "description": "View microclimate telemetry for authorized rearing sheds"},
    {"code": "sheds:write", "name": "Manage Shed Settings", "category": "Farmers & Sheds", "description": "Configure climate setpoints, stages, and thresholds"},
    
    # IoT Hardware
    {"code": "iot:read", "name": "View Devices", "category": "IoT", "description": "Browse registered gateways and IoT sensor nodes"},
    {"code": "iot:write", "name": "Register Devices", "category": "IoT", "description": "Commission and pair new IoT hardware controllers"},
    {"code": "iot:sensors", "name": "Configure Sensors", "category": "IoT", "description": "Adjust calibration offsets and sensor polling rates"},
    {"code": "iot:telemetry", "name": "View Telemetry", "category": "IoT", "description": "Stream live and historical sensor timeseries data"},
    {"code": "iot:control", "name": "Control Actuators", "category": "IoT", "description": "Trigger heaters, coolers, humidifiers, and ventilation relays"},
    
    # Operations
    {"code": "ops:incidents_read", "name": "View Incidents", "category": "Operations", "description": "View climate warnings and emergency alerts"},
    {"code": "ops:incidents_ack", "name": "Acknowledge Incidents", "category": "Operations", "description": "Acknowledge active alarms and assign responders"},
    {"code": "ops:incidents_resolve", "name": "Resolve Incidents", "category": "Operations", "description": "Mark incidents as safely resolved with post-mortem notes"},
    {"code": "ops:installations_read", "name": "View Installations", "category": "Operations", "description": "View field installation jobs and team schedules"},
    {"code": "ops:installations_write", "name": "Manage Installations", "category": "Operations", "description": "Dispatch field technicians and verify sign-off checklists"},
    
    # Commercial
    {"code": "commercial:products_read", "name": "View Products", "category": "Commercial", "description": "Browse sericulture equipment catalogue and inventory"},
    {"code": "commercial:products_write", "name": "Manage Products", "category": "Commercial", "description": "Update product specifications, prices, and stock balance"},
    {"code": "commercial:orders_read", "name": "View Orders", "category": "Commercial", "description": "View customer equipment and sensor orders"},
    {"code": "commercial:orders_write", "name": "Manage Orders", "category": "Commercial", "description": "Process orders and update fulfilment statuses"},
    {"code": "commercial:billing_read", "name": "View Billing", "category": "Commercial", "description": "View invoices, subscriptions, and payment history"},
    {"code": "commercial:billing_write", "name": "Manage Billing", "category": "Commercial", "description": "Create invoices, record payments, and manage subscription plans"},
    
    # Analytics
    {"code": "analytics:read", "name": "View Operational Analytics", "category": "Analytics", "description": "Access yield, mortality, and microclimate aggregations"},
    {"code": "analytics:export", "name": "Export Authorized Reports", "category": "Analytics", "description": "Export CSV/PDF audits and seasonal performance metrics"},
    
    # Administration
    {"code": "admin:audit_read", "name": "View Audit Logs", "category": "Administration", "description": "Inspect immutable administrative and security audit trail"},
    {"code": "admin:integrations", "name": "Manage Integrations", "category": "Administration", "description": "Configure cloud, WhatsApp, and telemetry bridges"},
    {"code": "admin:settings", "name": "Manage Platform Settings", "category": "Administration", "description": "Configure platform-wide policies and global setpoints"},
]

ALL_PERMISSION_CODES = [p["code"] for p in SYSTEM_PERMISSIONS]

# 10 Role Templates with exact granular permission mappings
ROLE_TEMPLATES = {
    "superadmin": {
        "name": "Platform Super Admin",
        "code": "superadmin",
        "description": "Master administrative access across all tenant organizations, platform configurations, and security audits.",
        "permissions": ALL_PERMISSION_CODES,
    },
    "company_admin": {
        "name": "Company Admin",
        "code": "company_admin",
        "description": "Full administrative control within the tenant organization: employee management, sheds, IoT hardware, and subscriptions.",
        "permissions": [
            "org:read", "org:write", "org:subscriptions",
            "users:read", "users:invite", "users:write", "users:suspend", "users:roles",
            "roles:read", "roles:write", "roles:assign",
            "farmers:read", "farmers:write", "sheds:read", "sheds:write",
            "iot:read", "iot:write", "iot:sensors", "iot:telemetry", "iot:control",
            "ops:incidents_read", "ops:incidents_ack", "ops:incidents_resolve", "ops:installations_read", "ops:installations_write",
            "commercial:products_read", "commercial:orders_read", "commercial:orders_write", "commercial:billing_read", "commercial:billing_write",
            "analytics:read", "analytics:export",
            "admin:audit_read"
        ],
    },
    "ceo": {
        "name": "CEO / Executive",
        "code": "ceo",
        "description": "Executive dashboard covering business KPIs, revenue, subscriptions, operational performance, and high-level reports.",
        "permissions": [
            "org:read",
            "users:read",
            "farmers:read", "sheds:read",
            "iot:read", "iot:telemetry",
            "commercial:products_read", "commercial:orders_read", "commercial:billing_read",
            "analytics:read", "analytics:export",
            "admin:audit_read"
        ],
    },
    "hr": {
        "name": "HR / User Administrator",
        "code": "hr",
        "description": "Human resources and user operations: employee directory, pending invitations, onboarding workflows, and department structures.",
        "permissions": [
            "org:read",
            "users:read", "users:invite", "users:write", "users:suspend", "users:roles",
            "roles:read",
            "admin:audit_read"
        ],
    },
    "operations_manager": {
        "name": "Operations Manager",
        "code": "operations_manager",
        "description": "Field operations oversight: rearing shed monitoring, device health, incident interlocks, and technician deployments.",
        "permissions": [
            "farmers:read", "farmers:write", "sheds:read", "sheds:write",
            "iot:read", "iot:write", "iot:sensors", "iot:telemetry", "iot:control",
            "ops:incidents_read", "ops:incidents_ack", "ops:incidents_resolve", "ops:installations_read", "ops:installations_write",
            "analytics:read"
        ],
    },
    "technician": {
        "name": "Installation Technician",
        "code": "technician",
        "description": "Field technical operations: assigned installation jobs, hardware checklists, sensor calibration, and diagnostic reports.",
        "permissions": [
            "farmers:read", "sheds:read",
            "iot:read", "iot:sensors", "iot:telemetry",
            "ops:incidents_read", "ops:incidents_ack", "ops:installations_read", "ops:installations_write"
        ],
    },
    "sales": {
        "name": "Sales & Billing",
        "code": "sales",
        "description": "Commercial management: customer enquiries, product catalogue, orders, invoices, and subscription accounting.",
        "permissions": [
            "farmers:read",
            "commercial:products_read", "commercial:products_write", "commercial:orders_read", "commercial:orders_write", "commercial:billing_read", "commercial:billing_write",
            "analytics:read"
        ],
    },
    "support": {
        "name": "Support Agent",
        "code": "support",
        "description": "Helpdesk and technical customer support: ticket triage, farmer assistance, incident monitoring, and order lookups.",
        "permissions": [
            "farmers:read", "sheds:read",
            "iot:read", "iot:telemetry",
            "ops:incidents_read", "ops:incidents_ack",
            "commercial:orders_read"
        ],
    },
    "analyst": {
        "name": "Analyst / Researcher",
        "code": "analyst",
        "description": "Data research & sericultural analytics: historical microclimate trends, sensor telemetry distributions, and exportable data.",
        "permissions": [
            "farmers:read", "sheds:read",
            "iot:read", "iot:telemetry",
            "analytics:read", "analytics:export"
        ],
    },
    "farmer": {
        "name": "Farmer",
        "code": "farmer",
        "description": "End-user farmer: view assigned rearing shed conditions, target growth stages, control authorized actuators, and receive alerts.",
        "permissions": [
            "sheds:read",
            "iot:read", "iot:telemetry", "iot:control"
        ],
    },
}


# ==============================================================================
# SCHEMA INITIALIZATION & MIGRATIONS
# ==============================================================================

def init_org_employee_tables():
    """Initializes tables for organizations, departments, roles, permissions, employees, and invitations."""
    now_dt = datetime.now(timezone.utc)
    
    with get_db_cursor(commit=True) as cursor:
        # 1. Organizations Master Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            code VARCHAR(64) UNIQUE NOT NULL,
            domain VARCHAR(128),
            contact_email VARCHAR(255),
            contact_phone VARCHAR(32),
            address TEXT,
            subscription_tier VARCHAR(64) NOT NULL DEFAULT 'ENTERPRISE',
            status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            max_users INT NOT NULL DEFAULT 100,
            max_sheds INT NOT NULL DEFAULT 50,
            settings JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_org_code ON organizations (code);
        CREATE INDEX IF NOT EXISTS idx_org_status ON organizations (status);
        """)

        # 2. Departments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            code VARCHAR(64) UNIQUE NOT NULL,
            description TEXT,
            head_id VARCHAR(64),
            status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_dept_code ON departments (code);
        """)

        # 3. Roles Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id VARCHAR(64) PRIMARY KEY,
            code VARCHAR(64) UNIQUE NOT NULL,
            name VARCHAR(128) NOT NULL,
            description TEXT,
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_roles_code ON roles (code);
        """)

        # 4. Permissions Master Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS permissions (
            code VARCHAR(64) PRIMARY KEY,
            name VARCHAR(128) NOT NULL,
            category VARCHAR(64) NOT NULL,
            description TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_perm_category ON permissions (category);
        """)

        # 5. Role-Permissions Join Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id VARCHAR(64) REFERENCES roles(id) ON DELETE CASCADE,
            permission_code VARCHAR(64) REFERENCES permissions(code) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_code)
        );
        """)

        # 6. Employees Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id VARCHAR(64) PRIMARY KEY,
            user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
            employee_id VARCHAR(64) UNIQUE NOT NULL,
            official_email VARCHAR(255) UNIQUE NOT NULL,
            department_id VARCHAR(64) REFERENCES departments(id) ON DELETE SET NULL,
            designation VARCHAR(128) NOT NULL DEFAULT 'Staff Member',
            reporting_manager_id VARCHAR(64) REFERENCES employees(id) ON DELETE SET NULL,
            role_code VARCHAR(64) NOT NULL DEFAULT 'farmer',
            role_id VARCHAR(64) REFERENCES roles(id) ON DELETE SET NULL,
            access_scope VARCHAR(32) NOT NULL DEFAULT 'GLOBAL',
            assigned_resources JSONB NOT NULL DEFAULT '{"sheds": [], "devices": []}'::jsonb,
            employment_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
            invitation_status VARCHAR(32) NOT NULL DEFAULT 'NONE',
            last_login TIMESTAMPTZ,
            created_by VARCHAR(64),
            created_at TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_emp_user ON employees (user_id);
        CREATE INDEX IF NOT EXISTS idx_emp_dept ON employees (department_id);
        CREATE INDEX IF NOT EXISTS idx_emp_manager ON employees (reporting_manager_id);
        CREATE INDEX IF NOT EXISTS idx_emp_status ON employees (employment_status);
        """)

        # 7. Employee Invitations Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_invitations (
            id VARCHAR(64) PRIMARY KEY,
            token VARCHAR(128) UNIQUE NOT NULL,
            employee_id VARCHAR(64) REFERENCES employees(id) ON DELETE CASCADE,
            user_id VARCHAR(64) REFERENCES users(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            role_code VARCHAR(64) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
            created_by VARCHAR(64) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL,
            accepted_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS idx_inv_token ON employee_invitations (token);
        CREATE INDEX IF NOT EXISTS idx_inv_employee ON employee_invitations (employee_id);
        CREATE INDEX IF NOT EXISTS idx_inv_status ON employee_invitations (status);
        """)

        # 8. Enrich users and audit_logs tables dynamically
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS official_email VARCHAR(255);")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE;")
        cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS access_scope VARCHAR(32) DEFAULT 'GLOBAL';")
        

        cursor.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS target_resource VARCHAR(128);")
        cursor.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS ip_address VARCHAR(64);")
        

        # 9. Seed System Permissions
        for perm in SYSTEM_PERMISSIONS:
            cursor.execute("""
            INSERT INTO permissions (code, name, category, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                category = EXCLUDED.category,
                description = EXCLUDED.description;
            """, (perm["code"], perm["name"], perm["category"], perm["description"]))

        # Organizations seeding removed

        # 11. Seed Roles & Map Permissions
        for rcode, rdata in ROLE_TEMPLATES.items():
            role_id = f"role_{rcode}"
            cursor.execute("""
            INSERT INTO roles (id, code, name, description, is_system, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, TRUE, 'ACTIVE', %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                is_system = TRUE;
            """, (role_id, rdata["code"], rdata["name"], rdata["description"], now_dt, now_dt))

            # Bind permissions
            for pcode in rdata["permissions"]:
                cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_code)
                VALUES (%s, %s)
                ON CONFLICT (role_id, permission_code) DO NOTHING;
                """, (role_id, pcode))

        # 12. Seed Default Departments
        default_depts = [
            ("dept_exec", "Executive & Strategy", "EXEC", "Corporate oversight, strategy, and overall board governance.", now_dt),
            ("dept_ops", "Operations & Field Services", "OPS", "Shed microclimate supervision, field deployment, and maintenance.", now_dt),
            ("dept_eng", "IoT Engineering & R&D", "ENG", "Hardware sensor calibration, gateway firmware, and telemetry analytics.", now_dt),
            ("dept_comm", "Commercial & Sales", "COMM", "Farm supplies distribution, subscriptions, and financial accounting.", now_dt),
            ("dept_hr", "Human Resources & Onboarding", "HR", "Personnel onboarding, organizational development, and RBAC governance.", now_dt),
            ("dept_supp", "Customer Helpdesk & Support", "SUPP", "Farmer assistance, emergency incident triage, and field escalations.", now_dt),
        ]
        for dept in default_depts:
            cursor.execute("""
            INSERT INTO departments (id, name, code, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description;
            """, (*dept, now_dt))

        # 13. Ensure Seed Users & Link Employee Records
        _seed_all_role_employees(cursor, now_dt)


def _seed_all_role_employees(cursor, now_dt):
    """
    Ensures accounts and linked employee records exist for all 10 standard roles.
    Includes reporting hierarchies (e.g. Technician reports to Operations Manager).
    """
    # Baseline list of demo users with employee details
    accounts = [
        # 1. Super Admin
        {
            "uid": "usr_admin_default", "uname": "admin", "pwd": "admin",
            "name": "Central Platform Administrator", "phone": "+91 98450 99999",
            "email": "admin@sericare.io", "role": "superadmin",
            "emp_id": "EMP-001", "dept_id": "dept_exec", "desig": "Chief Platform Architect",
            "manager_uid": None, "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02", "shed_03"], "devices": ["esp32_shed_01", "esp32_shed_02"]}
        },
        # 2. Company Admin
        {
            "uid": "usr_comp_admin", "uname": "comp_admin", "pwd": "company2026",
            "name": "Siddharth Rao (Company Admin)", "phone": "+91 98450 11002",
            "email": "siddharth.rao@sericare.io", "role": "company_admin",
            "emp_id": "EMP-002", "dept_id": "dept_exec", "desig": "General Manager & Tenant Administrator",
            "manager_uid": "usr_admin_default", "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02", "shed_03"], "devices": []}
        },
        # 3. CEO
        {
            "uid": "usr_ceo", "uname": "ceo", "pwd": "ceo2026",
            "name": "Vikramaditya Hegde", "phone": "+91 98450 11001",
            "email": "ceo@sericare.io", "role": "ceo",
            "emp_id": "EMP-003", "dept_id": "dept_exec", "desig": "Chief Executive Officer",
            "manager_uid": None, "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02"], "devices": []}
        },
        # 4. HR
        {
            "uid": "usr_hr_01", "uname": "hr_deepa", "pwd": "hr2026",
            "name": "Deepa Kulkarni (HR Lead)", "phone": "+91 98450 55005",
            "email": "deepa.hr@sericare.io", "role": "hr",
            "emp_id": "EMP-004", "dept_id": "dept_hr", "desig": "Head of People & User Administration",
            "manager_uid": "usr_ceo", "scope": "GLOBAL",
            "resources": {"sheds": [], "devices": []}
        },
        # 5. Operations Manager
        {
            "uid": "usr_ops_01", "uname": "ops_manoj", "pwd": "ops2026",
            "name": "Manoj Patil (Operations Director)", "phone": "+91 98450 66006",
            "email": "manoj.ops@sericare.io", "role": "operations_manager",
            "emp_id": "EMP-005", "dept_id": "dept_ops", "desig": "Director of Field Operations",
            "manager_uid": "usr_ceo", "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02", "shed_03"], "devices": []}
        },
        # 6. Technician (Reports to Operations Manager!)
        {
            "uid": "usr_technician_01", "uname": "tech_kiran", "pwd": "tech2026",
            "name": "Kiran Kumar (Field Lead)", "phone": "+91 98450 22002",
            "email": "kiran.tech@sericare.io", "role": "technician",
            "emp_id": "EMP-006", "dept_id": "dept_ops", "desig": "Senior IoT Installation Specialist",
            "manager_uid": "usr_ops_01", "scope": "ASSIGNED_ONLY",
            "resources": {"sheds": ["shed_01"], "devices": ["esp32_shed_01"]}
        },
        # 7. Sales & Billing
        {
            "uid": "usr_sales_01", "uname": "sales_anand", "pwd": "sales2026",
            "name": "Anand Verma (Billing Lead)", "phone": "+91 98450 44004",
            "email": "anand.sales@sericare.io", "role": "sales",
            "emp_id": "EMP-007", "dept_id": "dept_comm", "desig": "Commercial & Subscription Lead",
            "manager_uid": "usr_ceo", "scope": "GLOBAL",
            "resources": {"sheds": [], "devices": []}
        },
        # 8. Support Agent
        {
            "uid": "usr_support_01", "uname": "support_priya", "pwd": "support2026",
            "name": "Priya Sharma (Support Specialist)", "phone": "+91 98450 33003",
            "email": "priya.support@sericare.io", "role": "support",
            "emp_id": "EMP-008", "dept_id": "dept_supp", "desig": "Senior Technical Support Specialist",
            "manager_uid": "usr_ops_01", "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02"], "devices": []}
        },
        # 9. Analyst / Researcher
        {
            "uid": "usr_analyst_01", "uname": "analyst_sneha", "pwd": "analyst2026",
            "name": "Dr. Sneha Murthy (Seri-Scientist)", "phone": "+91 98450 77007",
            "email": "sneha.research@sericare.io", "role": "analyst",
            "emp_id": "EMP-009", "dept_id": "dept_eng", "desig": "Principal Sericultural Research Analyst",
            "manager_uid": "usr_ceo", "scope": "GLOBAL",
            "resources": {"sheds": ["shed_01", "shed_02", "shed_03"], "devices": []}
        },
        # 10. Farmer
        {
            "uid": "usr_farmer_ramesh", "uname": "ramesh_farmer", "pwd": "setu2026",
            "name": "Ramesh Gowda", "phone": "+91 98450 12345",
            "email": "ramesh.farmer@sericare.io", "role": "farmer",
            "emp_id": "EMP-010", "dept_id": "dept_ops", "desig": "Master Sericulture Cultivator",
            "manager_uid": "usr_ops_01", "scope": "ASSIGNED_ONLY",
            "resources": {"sheds": ["shed_01"], "devices": ["esp32_shed_01"]}
        },
    ]

    import json

    # 1st Pass: Ensure user records exist
    for acc in accounts:
        cursor.execute("SELECT id FROM users WHERE username = %s", (acc["uname"],))
        existing_u = cursor.fetchone()
        if not existing_u:
            cursor.execute("""
            INSERT INTO users (id, username, hashed_password, full_name, phone, official_email, preferred_language, role, farm_name, region, shed_id, batch_id, dfl_capacity, breed, is_active, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'en', %s, 'SeriCare Cluster Facility', 'Central Hub', 'shed_01', 'SERI-2026', '250 DFL', 'Double Hybrid (FC1 x FC2)', TRUE, %s)
            """, (acc["uid"], acc["uname"], get_password_hash(acc["pwd"]), acc["name"], acc["phone"], acc["email"], acc["role"], now_dt))
        else:
            # Sync role and email
            cursor.execute("""
            UPDATE users SET official_email = %s WHERE username = %s;
            """, (acc["email"], acc["uname"]))

    # 2nd Pass: Create employee records
    for acc in accounts:
        emp_db_id = f"emp_{acc['emp_id'].lower().replace('-', '_')}"
        role_id = f"role_{acc['role']}"
        res_json = json.dumps(acc["resources"])
        
        cursor.execute("SELECT id FROM employees WHERE id = %s OR employee_id = %s", (emp_db_id, acc["emp_id"]))
        existing_emp = cursor.fetchone()
        if not existing_emp:
            cursor.execute("""
            INSERT INTO employees (
                id, user_id, employee_id, official_email,
                department_id, designation, reporting_manager_id,
                role_code, role_id, access_scope, assigned_resources,
                employment_status, invitation_status, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s::jsonb, 'ACTIVE', 'ACCEPTED', %s, %s)
            """, (
                emp_db_id, acc["uid"], acc["emp_id"], acc["email"],
                acc["dept_id"], acc["desig"], acc["role"], role_id,
                acc["scope"], res_json, now_dt, now_dt
            ))

    # 3rd Pass: Link reporting managers
    for acc in accounts:
        if acc["manager_uid"]:
            cursor.execute("SELECT id FROM employees WHERE user_id = %s", (acc["manager_uid"],))
            mgr_row = cursor.fetchone()
            if mgr_row:
                mgr_emp_id = mgr_row[0]
                cursor.execute("""
                UPDATE employees SET reporting_manager_id = %s WHERE user_id = %s;
                """, (mgr_emp_id, acc["uid"]))


# ==============================================================================
# HIERARCHY & CIRCULAR REPORTING VALIDATION
# ==============================================================================

def validate_no_circular_reporting(employee_id: str, candidate_manager_id: Optional[str]) -> None:
    """
    Prevents circular reporting structures (e.g. A reports to B, B reports to A).
    Traverses the management hierarchy from candidate_manager_id upwards.
    Raises ValueError if a cycle is detected.
    """
    if not candidate_manager_id:
        return
    if candidate_manager_id == employee_id:
        raise ValueError("An employee cannot be designated as their own reporting manager.")

    visited = {employee_id}
    curr_mgr = candidate_manager_id

    with get_db_cursor(dict_cursor=True) as cursor:
        while curr_mgr:
            if curr_mgr in visited:
                raise ValueError(
                    f"Circular reporting structure detected: employee '{employee_id}' "
                    f"is already an ancestor or superior of candidate manager '{candidate_manager_id}'."
                )
            visited.add(curr_mgr)
            cursor.execute("SELECT reporting_manager_id FROM employees WHERE id = %s", (curr_mgr,))
            row = cursor.fetchone()
            curr_mgr = row["reporting_manager_id"] if row else None


# ==============================================================================
# PERMISSION & SCOPE RESOLUTION HELPERS
# ==============================================================================

def get_user_effective_permissions(user_id: str, role_code: Optional[str] = None) -> List[str]:
    """
    Fetches all effective permission codes for a user from their assigned role,
    custom role overrides, or platform superadmin status.
    """
    with get_db_cursor(dict_cursor=True) as cursor:
        # Check if role_code passed or query from user
        if not role_code:
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            urow = cursor.fetchone()
            role_code = urow["role"] if urow else "farmer"

        # Platform Super Admin has all permissions
        if role_code in ["superadmin", "admin"]:
            return list(ALL_PERMISSION_CODES)

        # Check employee custom role_id or standard template
        cursor.execute("SELECT role_id, role_code FROM employees WHERE user_id = %s", (user_id,))
        erow = cursor.fetchone()
        
        target_role_id = erow["role_id"] if erow and erow.get("role_id") else f"role_{role_code}"
        
        cursor.execute("""
        SELECT permission_code FROM role_permissions WHERE role_id = %s
        """, (target_role_id,))
        rows = cursor.fetchall()
        
        if rows:
            return [r["permission_code"] for r in rows]
            
        # Fallback to role template
        tmpl = ROLE_TEMPLATES.get(role_code)
        return list(tmpl["permissions"]) if tmpl else []


def get_user_access_context(user_id: str) -> Dict[str, Any]:
    """
    Retrieves the complete authorization and data isolation context for an active user:
    - role
    - access_scope (ASSIGNED_ONLY, DEPARTMENT, ORGANIZATION)
    - assigned_resources (sheds, devices)
    - permissions list
    """
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT u.id, u.username, u.role, u.is_active,
               e.id as employee_db_id, e.employee_id, e.department_id,
               e.access_scope, e.assigned_resources, e.employment_status
        FROM users u
        LEFT JOIN employees e ON e.user_id = u.id
        WHERE u.id = %s
        """, (user_id,))
        row = cursor.fetchone()
        if not row:
            return {
                
                "role": "farmer",
                "access_scope": "GLOBAL",
                "assigned_resources": {"sheds": [], "devices": []},
                "permissions": [],
                "is_active": False
            }

        role = row["role"]
        perms = get_user_effective_permissions(user_id, role)
        
        assigned_res = row.get("assigned_resources")
        if isinstance(assigned_res, str):
            import json
            try:
                assigned_res = json.loads(assigned_res)
            except Exception:
                assigned_res = {"sheds": [], "devices": []}
        elif not isinstance(assigned_res, dict):
            assigned_res = {"sheds": [], "devices": []}

        # Check account suspension across both tables
        is_active = bool(row.get("is_active", True))
        if row.get("employment_status") == "SUSPENDED":
            is_active = False

        return {
            "user_id": row["id"],
            "username": row["username"],
            "role": role,
            
            "employee_db_id": row.get("employee_db_id"),
            "employee_id": row.get("employee_id"),
            "department_id": row.get("department_id"),
            "access_scope": row.get("access_scope") or ("ASSIGNED_ONLY" if role in ["farmer", "technician"] else "GLOBAL"),
            "assigned_resources": assigned_res,
            "permissions": perms,
            "is_active": is_active
        }


# ==============================================================================
# AUDIT LOGGING HELPER
# ==============================================================================
# ORGANIZATIONS OPERATIONS
# ==============================================================================

def list_organizations(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[int, List[Dict[str, Any]]]:
    """Lists organizations with pagination, filters, and dynamic counts of employees, sheds, devices."""
    with get_db_cursor(dict_cursor=True) as cursor:
        where_clauses = []
        params = []
        if search:
            where_clauses.append("(name ILIKE %s OR code ILIKE %s OR domain ILIKE %s)")
            p = f"%{search.strip()}%"
            params.extend([p, p, p])
        if status:
            where_clauses.append("status = %s")
            params.append(status.upper())

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Count total
        cursor.execute(f"SELECT COUNT(*) as count FROM organizations {where_sql}", tuple(params))
        total_count = cursor.fetchone()["count"]

        # Fetch records with aggregates
        query = f"""
        SELECT o.id, o.name, o.code, o.domain, o.contact_email, o.contact_phone,
               o.address, o.subscription_tier, o.status, o.max_users, o.max_sheds,
               o.settings, o.created_at, o.updated_at,
               (SELECT COUNT(*) FROM employees e WHERE e.organization_id = o.id) as employee_count,
               (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id AND u.role = 'farmer') as farmer_count,
               (SELECT COUNT(*) FROM devices d WHERE d.organization_id = o.id) as device_count
        FROM organizations o
        {where_sql}
        ORDER BY o.created_at ASC
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, tuple(params + [limit, offset]))
        rows = cursor.fetchall()
        return total_count, [dict(r) for r in rows]


def get_organization_detail(org_id: str) -> Optional[Dict[str, Any]]:
    """Fetches organization profile, subscription, and capacity usage."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT o.*,
               (SELECT COUNT(*) FROM employees e WHERE e.organization_id = o.id) as employee_count,
               (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id AND u.role = 'farmer') as farmer_count,
               (SELECT COUNT(*) FROM devices d WHERE d.organization_id = o.id) as device_count,
               (SELECT COUNT(*) FROM departments dept WHERE dept.organization_id = o.id) as department_count
        FROM organizations o
        WHERE o.id = %s
        """, (org_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def create_organization(data: Dict[str, Any], actor: str) -> Dict[str, Any]:
    """Registers a new tenant organization with safe validation."""
    now_dt = datetime.now(timezone.utc)
    org_id = data.get("id") or f"org_{secrets.token_hex(6)}"
    code = data["code"].strip().upper()
    name = data["name"].strip()
    
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        # Check unique code
        cursor.execute("SELECT id FROM organizations WHERE code = %s", (code,))
        if cursor.fetchone():
            raise ValueError(f"Organization with code '{code}' already exists.")

        import json
        settings_json = json.dumps(data.get("settings") or {})
        
        cursor.execute("""
        INSERT INTO organizations (
            id, name, code, domain, contact_email, contact_phone, address,
            subscription_tier, status, max_users, max_sheds, settings,
            created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        RETURNING *
        """, (
            org_id, name, code,
            data.get("domain"), data.get("contact_email"), data.get("contact_phone"), data.get("address"),
            data.get("subscription_tier", "ENTERPRISE"), data.get("status", "ACTIVE").upper(),
            data.get("max_users", 100), data.get("max_sheds", 50), settings_json,
            now_dt, now_dt
        ))
        created = cursor.fetchone()

        # Seed default departments for the new organization
        default_depts = [
            ("Operations", "OPS", "Field operations & sheds"),
            ("Engineering", "ENG", "IoT Hardware and maintenance"),
            ("Administration", "ADMIN", "Management and HR")
        ]
        for dname, dcode, ddesc in default_depts:
            dept_id = f"dept_{org_id}_{dcode.lower()}"
            cursor.execute("""
            INSERT INTO departments (id, organization_id, name, code, description, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (organization_id, code) DO NOTHING
            """, (dept_id, org_id, dname, dcode, ddesc, now_dt, now_dt))

    log_security_audit(
        actor=actor,
        action="CREATE_ORGANIZATION",
        details=f"Registered new organization '{name}' (Code: {code})",
        target_resource=org_id,
        organization_id=org_id
    )
    return dict(created)


def update_organization(org_id: str, updates: Dict[str, Any], actor: str) -> Optional[Dict[str, Any]]:
    """Updates organization profile, tier, quotas, or settings."""
    now_dt = datetime.now(timezone.utc)
    allowed_fields = ["name", "domain", "contact_email", "contact_phone", "address", "subscription_tier", "max_users", "max_sheds", "settings"]
    
    set_clauses = ["updated_at = %s"]
    params = [now_dt]
    
    for f in allowed_fields:
        if f in updates and updates[f] is not None:
            if f == "settings":
                import json
                set_clauses.append(f"{f} = %s::jsonb")
                params.append(json.dumps(updates[f]))
            else:
                set_clauses.append(f"{f} = %s")
                params.append(updates[f])

    if len(set_clauses) == 1:
        return get_organization_detail(org_id)

    params.append(org_id)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute(f"""
        UPDATE organizations
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING *
        """, tuple(params))
        row = cursor.fetchone()

    if row:
        log_security_audit(
            actor=actor,
            action="UPDATE_ORGANIZATION",
            details=f"Updated organization details: {list(updates.keys())}",
            target_resource=org_id,
            organization_id=org_id
        )
        return dict(row)
    return None


def update_organization_status(org_id: str, new_status: str, actor: str) -> Optional[Dict[str, Any]]:
    """Suspends or reactivates an organization. When suspended, disables company logins."""
    new_status = new_status.upper()
    if new_status not in ["ACTIVE", "SUSPENDED", "TRIAL"]:
        raise ValueError("Status must be ACTIVE, SUSPENDED, or TRIAL")

    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        UPDATE organizations
        SET status = %s, updated_at = %s
        WHERE id = %s
        RETURNING *
        """, (new_status, now_dt, org_id))
        row = cursor.fetchone()
        
        # If suspended, synchronize employee suspension
        if new_status == "SUSPENDED":
            cursor.execute("""
            UPDATE employees SET employment_status = 'SUSPENDED' WHERE organization_id = %s;
            """, (org_id,))
        elif new_status == "ACTIVE":
            cursor.execute("""
            UPDATE employees SET employment_status = 'ACTIVE' WHERE organization_id = %s AND employment_status = 'SUSPENDED';
            """, (org_id,))

    if row:
        log_security_audit(
            actor=actor,
            action="ORGANIZATION_STATUS_CHANGE",
            details=f"Organization {org_id} status updated to {new_status}",
            target_resource=org_id,
            organization_id=org_id
        )
        return dict(row)
    return None


def get_organization_resources(org_id: str) -> Dict[str, Any]:
    """Returns all employees, sheds, and devices owned by an organization."""
    with get_db_cursor(dict_cursor=True) as cursor:
        # Employees
        cursor.execute("""
        SELECT e.id, e.employee_id, e.official_email, e.designation, e.role_code,
               e.employment_status, u.full_name, u.username
        FROM employees e
        JOIN users u ON u.id = e.user_id
        WHERE e.organization_id = %s
        ORDER BY e.created_at ASC
        """, (org_id,))
        employees = [dict(r) for r in cursor.fetchall()]

        # Farmers & Sheds
        cursor.execute("""
        SELECT id, username, full_name, phone, shed_id, farm_name, region, is_active
        FROM users
        WHERE organization_id = %s AND role = 'farmer'
        ORDER BY created_at ASC
        """, (org_id,))
        farmers = [dict(r) for r in cursor.fetchall()]

        # Devices
        cursor.execute("""
        SELECT device_id, shed_id, device_name, firmware_version, status, last_seen_at
        FROM devices
        WHERE organization_id = %s
        ORDER BY created_at ASC
        """, (org_id,))
        devices = [dict(r) for r in cursor.fetchall()]

        return {
            "organization_id": org_id,
            "employees": employees,
            "farmers": farmers,
            "devices": devices,
            "totals": {
                "employees": len(employees),
                "farmers": len(farmers),
                "devices": len(devices)
            }
        }


def get_organization_activity(org_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Returns organizational audit logs."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT id, timestamp, actor, action, details, target_resource, ip_address
        FROM audit_logs
        WHERE organization_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """, (org_id, limit))
        return [dict(r) for r in cursor.fetchall()]


# ==============================================================================


# ==============================================================================

def log_security_audit(
    actor: str,
    action: str,
    details: str,
    target_resource: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """Logs auditable administrative, authorization, and security events."""
    now_dt = datetime.now(timezone.utc)
    try:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("""
            INSERT INTO audit_logs (timestamp, actor, action, details, target_resource, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (now_dt, actor, action, details, target_resource or "system", ip_address or "127.0.0.1"))
    except Exception as e:
        logger.error("Failed to write security audit log: %s", e)


# DEPARTMENTS OPERATIONS
# ==============================================================================

def list_departments(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists departments with member counts and head name."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT d.id, d.name, d.code, d.description, d.head_id, d.status,
               d.created_at, d.updated_at,
               (SELECT COUNT(*) FROM employees e WHERE e.department_id = d.id) as employee_count,
               (SELECT u.full_name FROM employees he JOIN users u ON u.id = he.user_id WHERE he.id = d.head_id) as head_name
        FROM departments d
        ORDER BY d.created_at ASC
        """)
        return [dict(r) for r in cursor.fetchall()]


def get_department(dept_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves department details along with list of member employees."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT d.*, (SELECT u.full_name FROM employees he JOIN users u ON u.id = he.user_id WHERE he.id = d.head_id) as head_name
        FROM departments d
        WHERE d.id = %s
        """, (dept_id,))
        dept = cursor.fetchone()
        if not dept:
            return None

        # Fetch member employees
        cursor.execute("""
        SELECT e.id, e.employee_id, e.official_email, e.designation, e.role_code,
               e.employment_status, u.full_name, u.phone
        FROM employees e
        JOIN users u ON u.id = e.user_id
        WHERE e.department_id = %s
        ORDER BY u.full_name ASC
        """, (dept_id,))
        dept_dict = dict(dept)
        dept_dict["members"] = [dict(r) for r in cursor.fetchall()]
        return dept_dict


def create_department(data: Dict[str, Any], actor: str) -> Dict[str, Any]:
    """Creates a department."""
    now_dt = datetime.now(timezone.utc)
    code = data["code"].strip().upper()
    name = data["name"].strip()
    dept_id = data.get("id") or f"dept_{code.lower()}"

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT id FROM departments WHERE code = %s
        """, (code,))
        if cursor.fetchone():
            raise ValueError(f"Department code '{code}' already exists.")

        cursor.execute("""
        INSERT INTO departments (id, name, code, description, head_id, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """, (
            dept_id, name, code, data.get("description"),
            data.get("head_id"), data.get("status", "ACTIVE").upper(),
            now_dt, now_dt
        ))
        created = cursor.fetchone()

    log_security_audit(
        actor=actor,
        action="CREATE_DEPARTMENT",
        details=f"Created department '{name}' ({code})",
        target_resource=dept_id
    )
    return dict(created)


def update_department(dept_id: str, updates: Dict[str, Any], actor: str) -> Optional[Dict[str, Any]]:
    """Updates department name, description, head, or status."""
    now_dt = datetime.now(timezone.utc)
    set_clauses = ["updated_at = %s"]
    params = [now_dt]

    for f in ["name", "description", "head_id", "status"]:
        if f in updates and updates[f] is not None:
            set_clauses.append(f"{f} = %s")
            params.append(updates[f])

    if len(set_clauses) == 1:
        return get_department(dept_id)

    params.append(dept_id)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute(f"""
        UPDATE departments
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING *
        """, tuple(params))
        row = cursor.fetchone()

    if row:
        log_security_audit(
            actor=actor,
            action="UPDATE_DEPARTMENT",
            details=f"Updated department {dept_id}: {list(updates.keys())}",
            target_resource=dept_id,
            
        )
        return dict(row)
    return None


def delete_department(dept_id: str, actor: str) -> bool:
    """Safely removes or deactivates a department."""
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("SELECT name FROM departments WHERE id = %s", (dept_id,))
        dept = cursor.fetchone()
        if not dept:
            return False

        # Check if members exist
        cursor.execute("SELECT COUNT(*) as count FROM employees WHERE department_id = %s", (dept_id,))
        count = cursor.fetchone()["count"]
        if count > 0:
            raise ValueError(f"Cannot delete department '{dept['name']}'. It still contains {count} assigned employees. Reassign them first.")

        cursor.execute("DELETE FROM departments WHERE id = %s", (dept_id,))
        
    log_security_audit(
        actor=actor,
        action="DELETE_DEPARTMENT",
        details=f"Deleted department '{dept['name']}' ({dept_id})",
        target_resource=dept_id,
        
    )
    return True


# ==============================================================================
# ROLES & PERMISSIONS OPERATIONS
# ==============================================================================

def list_all_permissions() -> List[Dict[str, Any]]:
    """Returns all system permissions grouped by category."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT code, name, category, description
        FROM permissions
        ORDER BY category ASC, code ASC
        """)
        return [dict(r) for r in cursor.fetchall()]


def list_roles(org_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lists roles with permissions."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT r.id, r.code, r.name, r.description, r.is_system, r.status,
               r.created_at, r.updated_at,
               (SELECT COUNT(*) FROM employees e WHERE e.role_id = r.id OR e.role_code = r.code) as user_count
        FROM roles r
        ORDER BY r.is_system DESC, r.name ASC
        """)
        roles = [dict(r) for r in cursor.fetchall()]

        # Attach permissions list to each role
        for role in roles:
            cursor.execute("""
            SELECT p.code, p.name, p.category, p.description
            FROM role_permissions rp
            JOIN permissions p ON p.code = rp.permission_code
            WHERE rp.role_id = %s
            ORDER BY p.category, p.code
            """, (role["id"],))
            perms = cursor.fetchall()
            role["permissions"] = [p["code"] for p in perms]
            role["permissions_detailed"] = [dict(p) for p in perms]

        return roles


def get_role_detail(role_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full role details with permissions."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM roles WHERE id = %s OR code = %s", (role_id, role_id))
        role = cursor.fetchone()
        if not role:
            return None
        role_dict = dict(role)

        cursor.execute("""
        SELECT p.code, p.name, p.category, p.description
        FROM role_permissions rp
        JOIN permissions p ON p.code = rp.permission_code
        WHERE rp.role_id = %s
        ORDER BY p.category, p.code
        """, (role_dict["id"],))
        perms = cursor.fetchall()
        role_dict["permissions"] = [p["code"] for p in perms]
        role_dict["permissions_detailed"] = [dict(p) for p in perms]
        return role_dict


def create_custom_role(
    data: Dict[str, Any],
    creator_perms: List[str],
    actor: str,
    actor_is_superadmin: bool = False
) -> Dict[str, Any]:
    """
    Creates a new custom role with selected permissions.
    Enforces privilege escalation checks: administrator cannot grant permissions they do not possess.
    """
    now_dt = datetime.now(timezone.utc)
    code = data["code"].strip().lower()
    name = data["name"].strip()
    role_id = data.get("id") or f"role_custom_{secrets.token_hex(4)}"
    requested_perms = data.get("permissions") or []

    # System code collision check
    if code in ROLE_TEMPLATES:
        raise ValueError(f"Role code '{code}' is reserved for system roles.")

    # Privilege escalation check
    if not actor_is_superadmin:
        unauthorized_perms = set(requested_perms) - set(creator_perms)
        if unauthorized_perms:
            raise ValueError(f"Privilege escalation prevented: cannot grant permissions you do not possess: {list(unauthorized_perms)}")

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        INSERT INTO roles (id, code, name, description, is_system, status, created_at, updated_at)
        VALUES (%s, %s, %s, %s, FALSE, %s, %s, %s)
        RETURNING *
        """, (
            role_id, code, name, data.get("description", "Custom operational role"),
            data.get("status", "ACTIVE").upper(), now_dt, now_dt
        ))
        created = cursor.fetchone()

        # Insert permissions
        for pcode in requested_perms:
            cursor.execute("""
            INSERT INTO role_permissions (role_id, permission_code)
            VALUES (%s, %s)
            ON CONFLICT (role_id, permission_code) DO NOTHING
            """, (role_id, pcode))

    log_security_audit(
        actor=actor,
        action="CREATE_CUSTOM_ROLE",
        details=f"Created custom role '{name}' with {len(requested_perms)} permissions",
        target_resource=role_id
    )
    result = dict(created)
    result["permissions"] = requested_perms
    return result


def update_custom_role(
    role_id: str,
    updates: Dict[str, Any],
    creator_perms: List[str],
    actor: str,
    actor_is_superadmin: bool = False
) -> Optional[Dict[str, Any]]:
    """Updates custom role name, description, status, and permissions. System roles protected."""
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM roles WHERE id = %s", (role_id,))
        role = cursor.fetchone()
        if not role:
            return None
        if role["is_system"]:
            raise ValueError("System-critical role templates are protected and cannot be modified or deleted.")

        now_dt = datetime.now(timezone.utc)
        set_clauses = ["updated_at = %s"]
        params = [now_dt]

        for f in ["name", "description", "status"]:
            if f in updates and updates[f] is not None:
                set_clauses.append(f"{f} = %s")
                params.append(updates[f])

        params.append(role_id)
        cursor.execute(f"""
        UPDATE roles
        SET {', '.join(set_clauses)}
        WHERE id = %s
        RETURNING *
        """, tuple(params))
        updated_role = cursor.fetchone()

        # Update permissions if supplied
        if "permissions" in updates and isinstance(updates["permissions"], list):
            req_perms = updates["permissions"]
            if not actor_is_superadmin:
                unauthorized = set(req_perms) - set(creator_perms)
                if unauthorized:
                    raise ValueError(f"Privilege escalation prevented: unauthorized permissions {list(unauthorized)}")

            cursor.execute("DELETE FROM role_permissions WHERE role_id = %s", (role_id,))
            for pcode in req_perms:
                cursor.execute("""
                INSERT INTO role_permissions (role_id, permission_code)
                VALUES (%s, %s)
                ON CONFLICT (role_id, permission_code) DO NOTHING
                """, (role_id, pcode))

    log_security_audit(
        actor=actor,
        action="UPDATE_ROLE",
        details=f"Updated role {role_id}",
        target_resource=role_id,
        
    )
    return get_role_detail(role_id)


def delete_custom_role(role_id: str, actor: str) -> bool:
    """Deletes custom role if not in use. System roles are protected."""
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("SELECT * FROM roles WHERE id = %s OR code = %s", (role_id, role_id))
        role = cursor.fetchone()
        if not role:
            return False
        if role["is_system"]:
            raise ValueError("System-critical role templates cannot be deleted.")

        # Check assigned employees
        cursor.execute("SELECT COUNT(*) as count FROM employees WHERE role_id = %s", (role["id"],))
        count = cursor.fetchone()["count"]
        if count > 0:
            raise ValueError(f"Cannot delete role: it is currently assigned to {count} active employees.")

        cursor.execute("DELETE FROM roles WHERE id = %s", (role["id"],))

    log_security_audit(
        actor=actor,
        action="DELETE_ROLE",
        details=f"Deleted custom role '{role['name']}' ({role_id})",
        target_resource=role_id,
        
    )
    return True


# ==============================================================================
# EMPLOYEES & ONBOARDING OPERATIONS
# ==============================================================================

def list_employees(
    org_id: Optional[str] = None,
    dept_id: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_desc: bool = True,
    limit: int = 20,
    offset: int = 0
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Lists employees with safe projection (never returning password hashes or invitation secrets),
    search, multi-criteria filtering, and pagination.
    """
    valid_sorts = {
        "created_at": "e.created_at",
        "employee_id": "e.employee_id",
        "full_name": "u.full_name",
        "designation": "e.designation",
        "status": "e.employment_status"
    }
    sort_column = valid_sorts.get(sort_by, "e.created_at")
    sort_dir = "DESC" if sort_desc else "ASC"

    where_clauses = []
    params = []


    if dept_id:
        where_clauses.append("e.department_id = %s")
        params.append(dept_id)
    if role:
        where_clauses.append("e.role_code = %s")
        params.append(role)
    if status:
        where_clauses.append("e.employment_status = %s")
        params.append(status.upper())
    if search:
        p = f"%{search.strip()}%"
        where_clauses.append("(u.full_name ILIKE %s OR e.official_email ILIKE %s OR e.employee_id ILIKE %s OR u.username ILIKE %s)")
        params.extend([p, p, p, p])

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute(f"""
        SELECT COUNT(*) as count
        FROM employees e
        JOIN users u ON u.id = e.user_id
        {where_sql}
        """, tuple(params))
        total_count = cursor.fetchone()["count"]

        query = f"""
        SELECT e.id, e.user_id, e.employee_id, e.official_email,
               e.department_id, e.designation, e.reporting_manager_id, e.role_code, e.role_id,
               e.access_scope, e.assigned_resources, e.employment_status, e.invitation_status,
               e.last_login, e.created_at, e.updated_at,
               u.username, u.full_name, u.phone, u.is_active as user_is_active, u.mfa_enabled,
               dept.name as department_name,
               (SELECT mu.full_name FROM employees me JOIN users mu ON mu.id = me.user_id WHERE me.id = e.reporting_manager_id) as reporting_manager_name
        FROM employees e
        JOIN users u ON u.id = e.user_id
        LEFT JOIN departments dept ON dept.id = e.department_id
        {where_sql}
        ORDER BY {sort_column} {sort_dir}
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, tuple(params + [limit, offset]))
        rows = cursor.fetchall()
        
        results = []
        for r in rows:
            d = dict(r)
            # Ensure assigned_resources is json
            if isinstance(d.get("assigned_resources"), str):
                import json
                try:
                    d["assigned_resources"] = json.loads(d["assigned_resources"])
                except Exception:
                    pass
            results.append(d)

        return total_count, results


def get_employee_detail(employee_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full employee record, direct reports, and active permissions."""
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT e.*,
               u.username, u.full_name, u.phone, u.preferred_language, u.is_active as user_is_active, u.mfa_enabled,
               dept.name as department_name,
               (SELECT mu.full_name FROM employees me JOIN users mu ON mu.id = me.user_id WHERE me.id = e.reporting_manager_id) as reporting_manager_name
        FROM employees e
        JOIN users u ON u.id = e.user_id
        LEFT JOIN departments dept ON dept.id = e.department_id
        WHERE e.id = %s OR e.employee_id = %s
        """, (employee_id, employee_id))
        row = cursor.fetchone()
        if not row:
            return None
        emp_dict = dict(row)

        # Parse assigned_resources
        if isinstance(emp_dict.get("assigned_resources"), str):
            import json
            try:
                emp_dict["assigned_resources"] = json.loads(emp_dict["assigned_resources"])
            except Exception:
                pass

        # Direct reports
        cursor.execute("""
        SELECT e.id, e.employee_id, e.official_email, e.designation, e.role_code,
               u.full_name, e.employment_status
        FROM employees e
        JOIN users u ON u.id = e.user_id
        WHERE e.reporting_manager_id = %s
        ORDER BY u.full_name ASC
        """, (emp_dict["id"],))
        emp_dict["direct_reports"] = [dict(r) for r in cursor.fetchall()]

        # Effective permissions
        emp_dict["effective_permissions"] = get_user_effective_permissions(emp_dict["user_id"], emp_dict["role_code"])

        # Pending invitation details if any
        cursor.execute("""
        SELECT id, token, expires_at, status, created_at
        FROM employee_invitations
        WHERE employee_id = %s AND status = 'PENDING'
        ORDER BY created_at DESC LIMIT 1
        """, (emp_dict["id"],))
        inv_row = cursor.fetchone()
        if inv_row:
            emp_dict["active_invitation"] = {
                "id": inv_row["id"],
                "expires_at": inv_row["expires_at"].isoformat(),
                "status": inv_row["status"],
                "created_at": inv_row["created_at"].isoformat()
            }
        else:
            emp_dict["active_invitation"] = None

        return emp_dict


def create_employee_with_invitation(
    data: Dict[str, Any],
    actor: str,
    actor_perms: List[str],
    actor_is_superadmin: bool = False,
    base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """
    Transactional onboarding:
    1. Validates inputs, uniqueness, and circular reporting.
    2. Enforces privilege escalation prevention on role.
    3. Creates platform user and linked employee record.
    4. Issues cryptographically secure, time-limited, single-use invitation token.
    5. Dispatches or formats activation link.
    6. Logs audit trail.
    """
    now_dt = datetime.now(timezone.utc)
    email = data["official_email"].strip().lower()
    full_name = data["full_name"].strip()
    emp_code = data["employee_id"].strip().upper()
    role_code = data.get("role_code", "technician")
    dept_id = data.get("department_id")
    manager_id = data.get("reporting_manager_id")
    scope = data.get("access_scope") or ("ASSIGNED_ONLY" if role_code in ["technician", "farmer"] else "GLOBAL")
    resources = data.get("assigned_resources") or {"sheds": [], "devices": []}
    
    # 1. Privilege escalation check: cannot assign superadmin unless caller is superadmin
    if role_code in ["superadmin", "admin"] and not actor_is_superadmin:
        raise ValueError("Privilege escalation prevented: only Platform Super Admins can assign superadmin role.")

    # 2. Check circular reporting if manager supplied
    temp_emp_id = f"emp_{secrets.token_hex(4)}"
    if manager_id:
        validate_no_circular_reporting(temp_emp_id, manager_id)

    import json
    resources_json = json.dumps(resources)

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        # Check uniqueness
        cursor.execute("""
        SELECT id FROM employees WHERE official_email = %s OR employee_id = %s
        """, (email, emp_code))
        if cursor.fetchone():
            raise ValueError(f"An employee with email '{email}' or ID '{emp_code}' already exists.")

        # Determine username from email prefix or generate
        base_username = email.split("@")[0].replace(".", "_")
        cursor.execute("SELECT id FROM users WHERE username = %s", (base_username,))
        uname = base_username if not cursor.fetchone() else f"{base_username}_{secrets.token_hex(2)}"

        # Generate provisional user identity with unguessable random password (awaiting onboarding activation)
        user_id = f"usr_{secrets.token_hex(6)}"
        provisional_password_hash = get_password_hash(secrets.token_urlsafe(32))

        cursor.execute("""
        INSERT INTO users (
            id, username, hashed_password, full_name, phone, official_email,
            preferred_language, role, farm_name, region, shed_id,
            batch_id, dfl_capacity, breed, is_active, mfa_enabled, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'en', %s, 'SeriCare Operations', 'Regional Hub', 'shed_01', 'SERI-2026', 'N/A', 'N/A', FALSE, FALSE, %s)
        RETURNING *
        """, (
            user_id, uname, provisional_password_hash, full_name,
            data.get("phone", "+91 98000 00000"), email, role_code, now_dt
        ))
        created_user = cursor.fetchone()

        # Create employee record in PENDING_ACTIVATION state
        role_id = f"role_{role_code}"
        cursor.execute("""
        INSERT INTO employees (
            id, user_id, employee_id, official_email,
            department_id, designation, reporting_manager_id,
            role_code, role_id, access_scope, assigned_resources,
            employment_status, invitation_status, created_by, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'PENDING_ACTIVATION', 'PENDING', %s, %s, %s)
        RETURNING *
        """, (
            temp_emp_id, user_id, emp_code, email,
            dept_id, data.get("designation", "Operations Staff"), manager_id,
            role_code, role_id, scope, resources_json,
            actor, now_dt, now_dt
        ))
        created_emp = cursor.fetchone()

        # Generate secure, single-use, 7-day invitation token
        inv_token = secrets.token_urlsafe(32)
        inv_id = f"inv_{secrets.token_hex(6)}"
        expires_at = now_dt + timedelta(days=7)

        cursor.execute("""
        INSERT INTO employee_invitations (
            id, token, employee_id, user_id, email,
            role_code, expires_at, status, created_by, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s)
        RETURNING *
        """, (
            inv_id, inv_token, temp_emp_id, user_id, email,
            role_code, expires_at, actor, now_dt
        ))
        invitation = cursor.fetchone()

    # Log security audit
    log_security_audit(
        actor=actor,
        action="INVITE_EMPLOYEE",
        details=f"Invited new employee '{full_name}' ({email}, ID: {emp_code}, Role: {role_code})",
        target_resource=temp_emp_id,
        
    )

    activation_url = f"{base_url.rstrip('/')}/admin#invitation_token={inv_token}"
    return {
        "status": "success",
        "success": True,
        "employee_id": temp_emp_id,
        "employee_code": emp_code,
        "user_id": user_id,
        "official_email": email,
        "full_name": full_name,
        "role_code": role_code,
        "invitation_token": inv_token,
        "activation_url": activation_url,
        "expires_at": expires_at.isoformat(),
        "delivery_notice": "Invitation token generated. Since external SMTP relay is unconfigured in this environment, provide the secure activation URL directly to the employee."
    }


def update_employee(
    employee_id: str,
    updates: Dict[str, Any],
    actor: str,
    actor_is_superadmin: bool = False
) -> Optional[Dict[str, Any]]:
    """Updates employee details, department, designation, manager, and access scope."""
    emp = get_employee_detail(employee_id)
    if not emp:
        return None

    # Circular reporting check
    new_manager_id = updates.get("reporting_manager_id")
    if new_manager_id:
        validate_no_circular_reporting(emp["id"], new_manager_id)

    # Privilege escalation check on role change
    new_role = updates.get("role_code")
    if new_role and new_role in ["superadmin", "admin"] and not actor_is_superadmin:
        raise ValueError("Privilege escalation prevented: only Platform Super Admins can assign superadmin role.")

    now_dt = datetime.now(timezone.utc)
    set_clauses = ["updated_at = %s"]
    params = [now_dt]

    allowed_fields = ["department_id", "designation", "reporting_manager_id", "role_code", "access_scope"]
    for f in allowed_fields:
        if f in updates and updates[f] is not None:
            set_clauses.append(f"{f} = %s")
            params.append(updates[f])
            if f == "role_code":
                set_clauses.append("role_id = %s")
                params.append(f"role_{updates[f]}")

    if "assigned_resources" in updates and updates["assigned_resources"] is not None:
        import json
        set_clauses.append("assigned_resources = %s::jsonb")
        params.append(json.dumps(updates["assigned_resources"]))

    params.append(emp["id"])

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute(f"""
        UPDATE employees
        SET {', '.join(set_clauses)}
        WHERE id = %s
        """, tuple(params))

        # Synchronize user full_name and role if provided
        u_clauses = []
        u_params = []
        if "full_name" in updates and updates["full_name"]:
            u_clauses.append("full_name = %s")
            u_params.append(updates["full_name"])
        if new_role:
            u_clauses.append("role = %s")
            u_params.append(new_role)
        if "phone" in updates and updates["phone"]:
            u_clauses.append("phone = %s")
            u_params.append(updates["phone"])

        if u_clauses:
            u_params.append(emp["user_id"])
            cursor.execute(f"""
            UPDATE users SET {', '.join(u_clauses)} WHERE id = %s
            """, tuple(u_params))

    log_security_audit(
        actor=actor,
        action="UPDATE_EMPLOYEE",
        details=f"Updated employee record {emp['employee_id']} ({emp['official_email']})",
        target_resource=emp["id"],
        
    )
    return get_employee_detail(emp["id"])


def update_employee_status(
    employee_id: str,
    new_status: str,
    actor: str
) -> Dict[str, Any]:
    """
    Activates or suspends employee account.
    Immediately invalidates existing sessions by toggling users.is_active.
    """
    new_status = new_status.upper()
    if new_status not in ["ACTIVE", "SUSPENDED", "PENDING_ACTIVATION"]:
        raise ValueError("Status must be ACTIVE, SUSPENDED, or PENDING_ACTIVATION")

    emp = get_employee_detail(employee_id)
    if not emp:
        raise ValueError(f"Employee '{employee_id}' not found.")

    is_user_active = (new_status == "ACTIVE")
    now_dt = datetime.now(timezone.utc)

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        UPDATE employees
        SET employment_status = %s, updated_at = %s
        WHERE id = %s
        """, (new_status, now_dt, emp["id"]))

        # Instant session invalidation in users table
        cursor.execute("""
        UPDATE users
        SET is_active = %s
        WHERE id = %s
        """, (is_user_active, emp["user_id"]))

    log_security_audit(
        actor=actor,
        action="EMPLOYEE_STATUS_CHANGE",
        details=f"Employee {emp['employee_id']} ({emp['full_name']}) status changed to {new_status}. User session active: {is_user_active}",
        target_resource=emp["id"],
        
    )
    return {
        "status": "success",
        "employee_id": emp["id"],
        "employment_status": new_status,
        "user_is_active": is_user_active
    }


def resend_employee_invitation(
    employee_id: str,
    actor: str,
    base_url: str = "http://localhost:8000"
) -> Dict[str, Any]:
    """Revokes any existing pending token and issues a fresh single-use activation invitation."""
    emp = get_employee_detail(employee_id)
    if not emp:
        raise ValueError(f"Employee '{employee_id}' not found.")

    now_dt = datetime.now(timezone.utc)
    new_token = secrets.token_urlsafe(32)
    new_inv_id = f"inv_{secrets.token_hex(6)}"
    expires_at = now_dt + timedelta(days=7)

    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        # Revoke old pending invitations
        cursor.execute("""
        UPDATE employee_invitations
        SET status = 'REVOKED'
        WHERE employee_id = %s AND status = 'PENDING'
        """, (emp["id"],))

        # Insert fresh invitation
        cursor.execute("""
        INSERT INTO employee_invitations (
            id, token, employee_id, user_id, email,
            role_code, expires_at, status, created_by, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PENDING', %s, %s)
        RETURNING *
        """, (
            new_inv_id, new_token, emp["id"], emp["user_id"],
            emp["official_email"], emp["role_code"], expires_at, actor, now_dt
        ))

        cursor.execute("""
        UPDATE employees SET invitation_status = 'PENDING', updated_at = %s WHERE id = %s
        """, (now_dt, emp["id"]))

    log_security_audit(
        actor=actor,
        action="RESEND_INVITATION",
        details=f"Re-issued onboarding invitation for employee {emp['employee_id']} ({emp['official_email']})",
        target_resource=emp["id"],
        
    )

    activation_url = f"{base_url.rstrip('/')}/admin#invitation_token={new_token}"
    return {
        "status": "success",
        "employee_id": emp["id"],
        "official_email": emp["official_email"],
        "invitation_token": new_token,
        "activation_url": activation_url,
        "expires_at": expires_at.isoformat(),
        "delivery_notice": "Fresh invitation token generated. External SMTP unconfigured in local sandbox; provide URL directly to employee."
    }


def revoke_employee_invitation(employee_id: str, actor: str) -> bool:
    """Revokes active invitation link, preventing activation."""
    emp = get_employee_detail(employee_id)
    if not emp:
        return False

    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        UPDATE employee_invitations
        SET status = 'REVOKED'
        WHERE employee_id = %s AND status = 'PENDING'
        """, (emp["id"],))

        cursor.execute("""
        UPDATE employees SET invitation_status = 'REVOKED', updated_at = %s WHERE id = %s
        """, (now_dt, emp["id"]))

    log_security_audit(
        actor=actor,
        action="REVOKE_INVITATION",
        details=f"Revoked pending invitation for {emp['employee_id']} ({emp['official_email']})",
        target_resource=emp["id"],
        
    )
    return True


# ==============================================================================
# INVITATION VERIFICATION & PASSWORD ACTIVATION
# ==============================================================================

def verify_invitation_token(token: str) -> Dict[str, Any]:
    """
    Validates invitation token authenticity, expiration, and status.
    Returns non-sensitive metadata for the onboarding form.
    """
    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT i.id, i.token, i.email, i.role_code, i.expires_at, i.status,
               e.id as employee_id, e.employee_id as corporate_emp_id, e.designation,
               u.full_name, u.username
        FROM employee_invitations i
        JOIN employees e ON e.id = i.employee_id
        JOIN users u ON u.id = i.user_id
        WHERE i.token = %s
        """, (token,))
        inv = cursor.fetchone()
        if not inv:
            raise ValueError("Invalid invitation link. This invitation does not exist or has been deleted.")

        if inv["status"] == "ACCEPTED":
            raise ValueError("This invitation has already been accepted and the account is active. Please log in.")
        if inv["status"] == "REVOKED":
            raise ValueError("This invitation was revoked by an administrator. Please contact your organization.")
        if inv["expires_at"] < now_dt:
            raise ValueError("This invitation link has expired. Please request a new invitation link from your administrator.")

        return {
            "valid": True,
            "email": inv["email"],
            "official_email": inv["email"],
            "full_name": inv["full_name"],
            "username": inv["username"],
            "corporate_employee_id": inv["corporate_emp_id"],
            "designation": inv["designation"],
            
            "role_code": inv["role_code"],
            "expires_at": inv["expires_at"].isoformat()
        }


def accept_invitation_and_activate(
    token: str,
    new_password: str,
    mfa_enabled: bool = False
) -> Dict[str, Any]:
    """
    Safe transactional onboarding completion:
    - Verifies token validity
    - Sets verified bcrypt password hash
    - Sets MFA flag
    - Transitions account status to ACTIVE
    - Marks invitation as ACCEPTED
    - Logs audit events
    """
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    now_dt = datetime.now(timezone.utc)
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT i.*, u.username, u.full_name, e.employee_id as corporate_emp_id
        FROM employee_invitations i
        JOIN users u ON u.id = i.user_id
        JOIN employees e ON e.id = i.employee_id
        WHERE i.token = %s
        """, (token,))
        inv = cursor.fetchone()
        if not inv:
            raise ValueError("Invalid invitation link.")
        if inv["status"] != "PENDING":
            raise ValueError(f"Invitation is no longer pending (Current state: {inv['status']}).")
        if inv["expires_at"] < now_dt:
            raise ValueError("Invitation link has expired.")

        hashed_pwd = get_password_hash(new_password)

        # 1. Activate user and store password
        cursor.execute("""
        UPDATE users
        SET hashed_password = %s,
            is_active = TRUE,
            mfa_enabled = %s
        WHERE id = %s
        """, (hashed_pwd, mfa_enabled, inv["user_id"]))

        # 2. Activate employee
        cursor.execute("""
        UPDATE employees
        SET employment_status = 'ACTIVE',
            invitation_status = 'ACCEPTED',
            updated_at = %s
        WHERE id = %s
        """, (now_dt, inv["employee_id"]))

        # 3. Mark invitation accepted
        cursor.execute("""
        UPDATE employee_invitations
        SET status = 'ACCEPTED',
            accepted_at = %s
        WHERE id = %s
        """, (now_dt, inv["id"]))

    log_security_audit(
        actor=inv["username"],
        action="INVITATION_ACCEPTED",
        details=f"Employee {inv['corporate_emp_id']} ({inv['email']}) accepted invitation and established password",
        target_resource=inv["employee_id"],
        
    )
    log_security_audit(
        actor=inv["username"],
        action="ACCOUNT_ACTIVATED",
        details=f"Account for {inv['full_name']} activated successfully (MFA: {mfa_enabled})",
        target_resource=inv["user_id"],
        
    )

    return {
        "status": "success",
        "success": True,
        "username": inv["username"],
        "full_name": inv["full_name"],
        "email": inv["email"],
        
        "message": "Account successfully activated. You may now log in to the platform."
    }
