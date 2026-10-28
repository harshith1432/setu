import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from app.services.db_service import get_user_by_username

@pytest.mark.anyio
async def test_three_tabs_concurrent_login_and_isolation(async_client):
    """
    Scenario 1-5:
    - Tab 1: Log in as Admin.
    - Tab 2: Log in as Farmer A (ramesh_farmer).
    - Tab 3: Log in as Farmer B (suresh_farmer).
    All three tabs remain authenticated simultaneously with unique session contexts.
    Each tab returns data belonging only to its own account.
    """
    # 1. Tab 1: Admin Login
    res1 = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"X-Tab-ID": "tab_1_admin"}
    )
    assert res1.status_code == 200
    data1 = res1.json()
    token1 = data1["access_token"]
    sess1 = data1["session_id"]
    assert sess1 is not None and sess1.startswith("sess_")
    assert data1["user"]["username"] == "admin"

    # 2. Tab 2: Farmer A Login
    res2 = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "ramesh_farmer", "password": "setu2026"},
        headers={"X-Tab-ID": "tab_2_farmer_a"}
    )
    assert res2.status_code == 200
    data2 = res2.json()
    token2 = data2["access_token"]
    sess2 = data2["session_id"]
    assert sess2 is not None and sess2.startswith("sess_")
    assert data2["user"]["username"] == "ramesh_farmer"

    # 3. Tab 3: Farmer B Login
    res3 = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "suresh_farmer", "password": "setu2026"},
        headers={"X-Tab-ID": "tab_3_farmer_b"}
    )
    assert res3.status_code == 200
    data3 = res3.json()
    token3 = data3["access_token"]
    sess3 = data3["session_id"]
    assert sess3 is not None and sess3.startswith("sess_")
    assert data3["user"]["username"] == "suresh_farmer"

    # Verify session uniqueness
    assert len({sess1, sess2, sess3}) == 3
    assert len({token1, token2, token3}) == 3

    # 4. Simultaneous authentication checks
    me1 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token1}", "X-Session-ID": sess1, "X-Tab-ID": "tab_1_admin"}
    )
    assert me1.status_code == 200
    assert me1.json()["username"] == "admin"
    assert me1.json()["role"] in ["admin", "superadmin"]

    me2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token2}", "X-Session-ID": sess2, "X-Tab-ID": "tab_2_farmer_a"}
    )
    assert me2.status_code == 200
    assert me2.json()["username"] == "ramesh_farmer"
    assert me2.json()["role"] == "farmer"

    me3 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token3}", "X-Session-ID": sess3, "X-Tab-ID": "tab_3_farmer_b"}
    )
    assert me3.status_code == 200
    assert me3.json()["username"] == "suresh_farmer"
    assert me3.json()["role"] == "farmer"


@pytest.mark.anyio
async def test_tab_refresh_and_role_authorization_isolation(async_client):
    """
    Scenario 6 & 12:
    - Refreshing Tab 2 preserves Farmer A's session.
    - RBAC / BOLA: Tab 1 can access Admin APIs; Tab 2 and Tab 3 cannot.
    - Farmer A can access shed_01; Farmer B can access shed_03; cross-shed access is blocked.
    """
    # Log in Tab 1 (Admin) and Tab 2 (Farmer A) and Tab 3 (Farmer B)
    res_admin = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok_admin = res_admin.json()["access_token"]
    sess_admin = res_admin.json()["session_id"]

    res_fa = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tok_fa = res_fa.json()["access_token"]
    sess_fa = res_fa.json()["session_id"]

    res_fb = await async_client.post("/api/v1/auth/login", json={"username": "suresh_farmer", "password": "setu2026"})
    tok_fb = res_fb.json()["access_token"]
    sess_fb = res_fb.json()["session_id"]

    # Refresh Tab 2: Still Farmer A
    refreshed_fa = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok_fa}", "X-Session-ID": sess_fa}
    )
    assert refreshed_fa.status_code == 200
    assert refreshed_fa.json()["username"] == "ramesh_farmer"

    # Tab 1 accesses admin farmers list -> 200 OK
    admin_call = await async_client.get(
        "/api/v1/admin/farmers",
        headers={"Authorization": f"Bearer {tok_admin}", "X-Session-ID": sess_admin}
    )
    assert admin_call.status_code == 200

    # Tab 2 attempts to access admin farmers list -> 403 Forbidden
    fa_call = await async_client.get(
        "/api/v1/admin/farmers",
        headers={"Authorization": f"Bearer {tok_fa}", "X-Session-ID": sess_fa}
    )
    assert fa_call.status_code == 403

    # Tab 2 accesses its own shed (shed_01) -> 200 OK
    fa_shed = await async_client.get(
        "/api/v1/sheds/shed_01/overview",
        headers={"Authorization": f"Bearer {tok_fa}", "X-Session-ID": sess_fa}
    )
    assert fa_shed.status_code == 200

    # Tab 2 attempts to access Tab 3's shed (shed_03) -> 403 Forbidden (BOLA isolation)
    fa_cross = await async_client.get(
        "/api/v1/sheds/shed_03/overview",
        headers={"Authorization": f"Bearer {tok_fa}", "X-Session-ID": sess_fa}
    )
    assert fa_cross.status_code == 403


@pytest.mark.anyio
async def test_independent_tab_logout(async_client):
    """
    Scenario 7:
    Logging out of Tab 2 (Farmer A) revokes only Tab 2's session.
    Tabs 1 (Admin) and 3 (Farmer B) remain 100% active and authenticated.
    """
    res1 = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok1 = res1.json()["access_token"]
    sess1 = res1.json()["session_id"]

    res2 = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tok2 = res2.json()["access_token"]
    sess2 = res2.json()["session_id"]

    res3 = await async_client.post("/api/v1/auth/login", json={"username": "suresh_farmer", "password": "setu2026"})
    tok3 = res3.json()["access_token"]
    sess3 = res3.json()["session_id"]

    # Logout Tab 2 ONLY
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {tok2}", "X-Session-ID": sess2}
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["session_id"] == sess2

    # Tab 2 must now be rejected (401)
    chk2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok2}", "X-Session-ID": sess2}
    )
    assert chk2.status_code == 401

    # Tab 1 (Admin) MUST STILL BE VALID
    chk1 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok1}", "X-Session-ID": sess1}
    )
    assert chk1.status_code == 200
    assert chk1.json()["username"] == "admin"

    # Tab 3 (Farmer B) MUST STILL BE VALID
    chk3 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok3}", "X-Session-ID": sess3}
    )
    assert chk3.status_code == 200
    assert chk3.json()["username"] == "suresh_farmer"


@pytest.mark.anyio
async def test_concurrent_api_requests_identity_integrity(async_client):
    """
    Scenario 9:
    Concurrent API requests across multiple tabs never mix identities or leak data.
    """
    res1 = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok1, sess1 = res1.json()["access_token"], res1.json()["session_id"]

    res2 = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tok2, sess2 = res2.json()["access_token"], res2.json()["session_id"]

    res3 = await async_client.post("/api/v1/auth/login", json={"username": "suresh_farmer", "password": "setu2026"})
    tok3, sess3 = res3.json()["access_token"], res3.json()["session_id"]

    async def fetch_me(tok, sess, expected_user):
        r = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tok}", "X-Session-ID": sess}
        )
        assert r.status_code == 200
        assert r.json()["username"] == expected_user
        return r.json()["username"]

    # Interweave 30 concurrent requests
    tasks = []
    for _ in range(10):
        tasks.append(fetch_me(tok1, sess1, "admin"))
        tasks.append(fetch_me(tok2, sess2, "ramesh_farmer"))
        tasks.append(fetch_me(tok3, sess3, "suresh_farmer"))

    results = await asyncio.gather(*tasks)
    assert results.count("admin") == 10
    assert results.count("ramesh_farmer") == 10
    assert results.count("suresh_farmer") == 10


@pytest.mark.anyio
async def test_token_refresh_per_tab(async_client):
    """
    Scenario 10:
    Token refresh in one tab renews its own credentials without overwriting or invalidating other tabs.
    """
    res1 = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok1, sess1 = res1.json()["access_token"], res1.json()["session_id"]

    res2 = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tok2, sess2 = res2.json()["access_token"], res2.json()["session_id"]

    # Refresh Tab 1
    ref1 = await async_client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {tok1}", "X-Session-ID": sess1}
    )
    assert ref1.status_code == 200
    new_tok1 = ref1.json()["access_token"]
    assert new_tok1 != tok1

    # Tab 1 works with new token
    me1 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_tok1}", "X-Session-ID": sess1}
    )
    assert me1.status_code == 200
    assert me1.json()["username"] == "admin"

    # Tab 2 continues working with its existing token without interruption
    me2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok2}", "X-Session-ID": sess2}
    )
    assert me2.status_code == 200
    assert me2.json()["username"] == "ramesh_farmer"


@pytest.mark.anyio
async def test_session_mismatch_header_rejected(async_client):
    """
    Security validation:
    Tampered request where X-Session-ID does not match the token's embedded session claim.
    Must be rejected with 401 Unauthorized.
    """
    res1 = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok1 = res1.json()["access_token"]

    res2 = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    sess2 = res2.json()["session_id"]

    # Send token1 with sess2 (mismatch!)
    mismatch_call = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tok1}", "X-Session-ID": sess2}
    )
    assert mismatch_call.status_code == 401
    assert "Session mismatch" in mismatch_call.json()["detail"]


@pytest.mark.anyio
async def test_list_sessions_and_logout_all(async_client):
    """
    Scenario 8 & Sessions Control:
    - Lists active sessions for current user with is_current flag.
    - POST /api/v1/auth/logout-all revokes all sessions for that user.
    """
    # User ramesh_farmer logs in on two separate tabs (Session A & Session B)
    resA = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tokA, sessA = resA.json()["access_token"], resA.json()["session_id"]

    resB = await async_client.post("/api/v1/auth/login", json={"username": "ramesh_farmer", "password": "setu2026"})
    tokB, sessB = resB.json()["access_token"], resB.json()["session_id"]

    # Also admin logs in
    res_admin = await async_client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    tok_admin, sess_admin = res_admin.json()["access_token"], res_admin.json()["session_id"]

    # List sessions from Tab A
    sess_list = await async_client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {tokA}", "X-Session-ID": sessA}
    )
    assert sess_list.status_code == 200
    sessions = sess_list.json()["sessions"]
    sess_ids = [s["session_id"] for s in sessions]
    assert sessA in sess_ids
    assert sessB in sess_ids

    # Tab A is current
    for s in sessions:
        if s["session_id"] == sessA:
            assert s["is_current"] is True
        elif s["session_id"] == sessB:
            assert s["is_current"] is False

    # Logout all sessions for ramesh_farmer from Tab A
    logout_all = await async_client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tokA}", "X-Session-ID": sessA}
    )
    assert logout_all.status_code == 200
    assert logout_all.json()["revoked_sessions"] >= 2

    # Both Tab A and Tab B are now revoked
    chkA = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokA}", "X-Session-ID": sessA})
    assert chkA.status_code == 401

    chkB = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokB}", "X-Session-ID": sessB})
    assert chkB.status_code == 401

    # Admin is completely untouched!
    chk_admin = await async_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok_admin}", "X-Session-ID": sess_admin})
    assert chk_admin.status_code == 200
    assert chk_admin.json()["username"] == "admin"
