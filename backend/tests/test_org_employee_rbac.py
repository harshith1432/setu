from app.services.db_service import init_db
from app.services.enterprise_db import init_enterprise_tables
from app.services.org_employee_db import init_org_employee_tables

init_db()
init_enterprise_tables()
init_org_employee_tables()

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_department_management_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as Superadmin
        admin_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
        assert admin_login.status_code == 200, f"Admin login failed: {admin_login.text}"
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Superadmin lists departments
        depts_res = await client.get("/api/v1/departments", headers=admin_headers)
        assert depts_res.status_code == 200
        depts = depts_res.json()
        assert isinstance(depts, list)
        assert len(depts) >= 1

        # 3. Superadmin creates a new department
        unique_suffix = uuid.uuid4().hex[:6]
        create_dept_res = await client.post("/api/v1/departments", headers=admin_headers, json={
            "name": f"Quality Assurance {unique_suffix}",
            "code": f"QA_{unique_suffix.upper()}",
            "description": "Silk cocoon quality assurance and batch certification",
            "status": "ACTIVE"
        })
        assert create_dept_res.status_code == 201, f"Dept creation failed: {create_dept_res.text}"
        created_dept = create_dept_res.json()
        created_dept_id = created_dept["id"]

        # 4. Superadmin updates department
        update_res = await client.put(f"/api/v1/departments/{created_dept_id}", headers=admin_headers, json={
            "description": "Updated quality inspection department"
        })
        assert update_res.status_code == 200
        assert update_res.json()["description"] == "Updated quality inspection department"

        # 5. Retrieve department details by ID
        get_res = await client.get(f"/api/v1/departments/{created_dept_id}", headers=admin_headers)
        assert get_res.status_code == 200
        assert get_res.json()["name"] == f"Quality Assurance {unique_suffix}"



@pytest.mark.anyio
async def test_employee_onboarding_and_activation_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as HR Manager
        hr_login = await client.post("/api/v1/auth/login", json={"username": "hr_deepa", "password": "hr2026"})
        assert hr_login.status_code == 200, f"HR login failed: {hr_login.text}"
        hr_token = hr_login.json()["access_token"]
        hr_headers = {"Authorization": f"Bearer {hr_token}"}

        # 1. Create a new employee with onboarding invitation
        unique_suffix = uuid.uuid4().hex[:6]
        emp_code = f"EMP-{unique_suffix}"
        emp_email = f"emp_{unique_suffix}@sericare.internal"
        create_res = await client.post("/api/v1/employees", headers=hr_headers, json={
            "employee_id": emp_code,
            "full_name": f"Tester Onboard {unique_suffix}",
            "official_email": emp_email,
            "phone": "+91 9988776655",
            "department_id": "dept_ops",
            "designation": "Assistant Farm Lead",
            "role_code": "technician",
            "access_scope": "ASSIGNED_ONLY"
        })
        assert create_res.status_code == 201, f"Employee creation failed: {create_res.text}"
        emp_data = create_res.json()
        assert emp_data["status"] == "success"
        invitation_token = emp_data.get("invitation_token")
        assert invitation_token is not None, "Invitation token was not returned"
        created_emp_db_id = emp_data["employee_id"]

        # 2. Prevent duplicate employee code in same organization
        dup_res = await client.post("/api/v1/employees", headers=hr_headers, json={
            "employee_id": emp_code,
            "full_name": "Duplicate User",
            "official_email": f"other_{unique_suffix}@sericare.internal",
            "department_id": "dept_ops",
            "role_code": "technician"
        })
        assert dup_res.status_code == 400

        # 3. Verify public invitation token endpoint
        verify_token_res = await client.get(f"/api/v1/auth/invitations/{invitation_token}")
        assert verify_token_res.status_code == 200
        inv_payload = verify_token_res.json()
        assert inv_payload["valid"] is True
        assert inv_payload["email"] == emp_email

        # 4. Accept invitation and establish password
        new_password = "SecureTesterPassword2026!"
        accept_res = await client.post(f"/api/v1/auth/invitations/{invitation_token}/accept", json={
            "password": new_password
        })
        assert accept_res.status_code == 200
        assert accept_res.json()["success"] is True

        # 5. Token reuse MUST fail
        reused_res = await client.post(f"/api/v1/auth/invitations/{invitation_token}/accept", json={
            "password": "AnotherPassword2026!"
        })
        assert reused_res.status_code == 400, "Used invitation token should be rejected"

        # 6. Newly onboarded employee can log in with new password
        emp_login = await client.post("/api/v1/auth/login", json={
            "username": emp_email,
            "password": new_password
        })
        assert emp_login.status_code == 200, f"Login with newly set password failed: {emp_login.text}"
        new_token = emp_login.json()["access_token"]
        assert new_token is not None

        # 7. Session revocation on suspension:
        # HR suspends this employee account
        suspend_res = await client.patch(f"/api/v1/employees/{created_emp_db_id}/status", headers=hr_headers, json={
            "status": "SUSPENDED"
        })
        assert suspend_res.status_code == 200

        # Now any API call using the suspended employee's existing JWT MUST be rejected with 403 Forbidden
        auth_call_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"})
        assert auth_call_res.status_code == 403, f"Expected 403 Forbidden for suspended employee, got {auth_call_res.status_code}"


@pytest.mark.anyio
async def test_circular_reporting_hierarchy_prevention():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Create Employee A
        code_a = f"EMPA-{uuid.uuid4().hex[:4]}"
        emp_a_res = await client.post("/api/v1/employees", headers=admin_headers, json={
            "employee_id": code_a,
            "full_name": "Supervisor Alpha",
            "official_email": f"{code_a.lower()}@test.com",
            "department_id": "dept_ops",
            "role_code": "operations_manager"
        })
        assert emp_a_res.status_code == 201
        id_a = emp_a_res.json()["employee_id"]

        # Create Employee B with reporting manager A
        code_b = f"EMPB-{uuid.uuid4().hex[:4]}"
        emp_b_res = await client.post("/api/v1/employees", headers=admin_headers, json={
            "employee_id": code_b,
            "full_name": "Subordinate Beta",
            "official_email": f"{code_b.lower()}@test.com",
            "department_id": "dept_ops",
            "reporting_manager_id": id_a,
            "role_code": "technician"
        })
        assert emp_b_res.status_code == 201
        id_b = emp_b_res.json()["employee_id"]

        # Now attempt to set Employee A's manager to Employee B (introducing cycle A -> B -> A)
        cycle_res = await client.put(f"/api/v1/employees/{id_a}", headers=admin_headers, json={
            "reporting_manager_id": id_b
        })
        assert cycle_res.status_code == 400, f"Expected 400 Bad Request on circular reporting, got {cycle_res.status_code}"
        assert "circular" in cycle_res.json()["detail"].lower()


@pytest.mark.anyio
async def test_roles_and_privilege_escalation_prevention():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Authenticated user can view permissions
        admin_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        perms_res = await client.get("/api/v1/permissions", headers=admin_headers)
        assert perms_res.status_code == 200
        perms = perms_res.json()
        assert len(perms) >= 30

        # 2. System roles cannot be modified or deleted
        delete_sys_role = await client.delete("/api/v1/roles/superadmin", headers=admin_headers)
        assert delete_sys_role.status_code == 400
        assert "system" in delete_sys_role.json()["detail"].lower()

        # 3. Create a valid custom role
        custom_role_code = f"cust_aud_{uuid.uuid4().hex[:4]}"
        create_role_res = await client.post("/api/v1/roles", headers=admin_headers, json={
            "code": custom_role_code,
            "name": "Custom Auditor",
            "description": "Custom role for compliance auditors",
            "permissions": ["admin:audit_read", "org:read", "users:read"]
        })
        assert create_role_res.status_code == 201
        created_role = create_role_res.json()
        assert created_role["code"] == custom_role_code

        # 4. Privilege Escalation Prevention:
        # A non-superadmin (HR manager) cannot create a custom role with permissions they do not possess
        hr_login = await client.post("/api/v1/auth/login", json={"username": "hr_deepa", "password": "hr2026"})
        hr_token = hr_login.json()["access_token"]
        hr_headers = {"Authorization": f"Bearer {hr_token}"}

        escalate_role_res = await client.post("/api/v1/roles", headers=hr_headers, json={
            "code": f"esc_{uuid.uuid4().hex[:4]}",
            "name": "Escalated Role",
            "description": "Unauthorized elevation",
            "permissions": ["admin:integrations", "org:write"]
        })
        assert escalate_role_res.status_code in (400, 403), f"Expected denial for privilege escalation, got {escalate_role_res.status_code}"


@pytest.mark.anyio
async def test_role_based_dashboard_view_and_audit_trail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test dashboard role views for different personas
        roles_to_test = [
            ("admin", "admin", "superadmin", "overview"),
            ("comp_admin", "company2026", "company_admin", "overview"),
            ("tech_kiran", "tech2026", "technician", "installations"),
            ("sales_anand", "sales2026", "sales", "orders"),
            ("support_priya", "support2026", "support", "support")
        ]

        for u, p, expected_role, expected_tab in roles_to_test:
            login_res = await client.post("/api/v1/auth/login", json={"username": u, "password": p})
            assert login_res.status_code == 200, f"Login failed for {u}"
            token = login_res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            dash_res = await client.get("/api/v1/dashboard/role-view", headers=headers)
            assert dash_res.status_code == 200, f"Dashboard view failed for {u}: {dash_res.text}"
            dash_data = dash_res.json()
            assert dash_data["role"] == expected_role
            assert dash_data["default_tab"] == expected_tab
            assert len(dash_data["kpis"]) == 4

        # Test Audit Trail filtering
        admin_login = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        audit_res = await client.get("/api/v1/admin/audit?limit=10", headers=admin_headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()
        assert isinstance(logs, list)
        assert len(logs) > 0
        assert "action" in logs[0]
        assert "actor" in logs[0]
