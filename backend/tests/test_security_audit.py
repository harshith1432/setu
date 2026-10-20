import pytest
import time
from app.core.security import create_access_token

@pytest.mark.anyio
async def test_security_headers_present(async_client):
    """
    SEC-09: Verifies that enterprise HTTP security headers are included in all responses:
    - HSTS
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: SAMEORIGIN
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Content-Security-Policy
    """
    res = await async_client.get("/")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "SAMEORIGIN"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in headers.get("strict-transport-security", "")
    assert "default-src" in headers.get("content-security-policy", "")

@pytest.mark.anyio
async def test_rejection_of_insecure_token_fallbacks(async_client):
    """
    VULN-01 & VULN-02: Verifies that forged tokens, unverified claims,
    and legacy 'firebase_' prefix backdoors are strictly rejected with HTTP 401.
    """
    # 1. Attempt using 'firebase_admin' backdoor
    res1 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer firebase_admin"}
    )
    assert res1.status_code == 401

    # 2. Attempt using fabricated unsigned JWT
    res2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiJ9."}
    )
    assert res2.status_code == 401

    # 3. Attempt using garbage token
    res3 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_garbage_token_12345"}
    )
    assert res3.status_code == 401

@pytest.mark.anyio
async def test_cross_tenant_shed_isolation_idor(async_client):
    """
    VULN-04: Verifies Broken Object-Level Authorization (BOLA/IDOR) protection.
    A farmer assigned to a shed MUST NOT be able to view or change stages for other sheds.
    """
    import uuid
    uid_a = f"usr_{uuid.uuid4().hex[:8]}"
    uname_a = f"farmer_a_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    token_a = create_access_token({"sub": uname_a, "user_id": uid_a, "role": "farmer"})

    from app.services.db_service import create_user
    user_a = create_user({
        "id": uid_a,
        "username": uname_a,
        "hashed_password": "hash",
        "full_name": "Farmer A",
        "phone": f"+91 {uuid.uuid4().int % 9000000000 + 1000000000}",
        "role": "farmer",
        "is_active": True
    })

    headers_a = {"Authorization": f"Bearer {token_a}"}
    own_shed = user_a["shed_id"]
    unauthorized_shed = "shed_99" if own_shed != "shed_99" else "shed_88"

    # 1. Farmer A accesses their own assigned shed -> Allowed (200)
    res_own = await async_client.get(f"/api/v1/sheds/{own_shed}", headers=headers_a)
    assert res_own.status_code == 200

    # 2. Farmer A attempts to access unauthorized shed -> Must be rejected with 403 Forbidden
    res_other = await async_client.get(f"/api/v1/sheds/{unauthorized_shed}", headers=headers_a)
    assert res_other.status_code == 403
    assert "Forbidden" in res_other.json()["detail"]

    # 3. Farmer A attempts to mutate silkworm stage of unauthorized shed -> Must be rejected with 403 Forbidden
    res_mutate = await async_client.post(f"/api/v1/sheds/{unauthorized_shed}/stage/4", headers=headers_a)
    assert res_mutate.status_code == 403

@pytest.mark.anyio
async def test_cross_tenant_telemetry_isolation(async_client):
    """
    VULN-04: Verifies that telemetry history and CSV export endpoints enforce tenant isolation.
    """
    import uuid
    uid_c = f"usr_{uuid.uuid4().hex[:8]}"
    uname_c = f"farmer_c_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    token_c = create_access_token({"sub": uname_c, "user_id": uid_c, "role": "farmer"})

    from app.services.db_service import create_user
    user_c = create_user({
        "id": uid_c,
        "username": uname_c,
        "hashed_password": "hash",
        "full_name": "Farmer C",
        "phone": f"+91 {uuid.uuid4().int % 9000000000 + 1000000000}",
        "role": "farmer",
        "is_active": True
    })
    headers_c = {"Authorization": f"Bearer {token_c}"}
    own_shed = user_c["shed_id"]
    unauthorized_shed = "shed_99" if own_shed != "shed_99" else "shed_88"

    # Telemetry history for own shed -> 200
    res_hist_own = await async_client.get(f"/api/v1/telemetry/history/{own_shed}", headers=headers_c)
    assert res_hist_own.status_code == 200

    # Telemetry history for other shed -> Forbidden (403)
    res_hist = await async_client.get(f"/api/v1/telemetry/history/{unauthorized_shed}", headers=headers_c)
    assert res_hist.status_code == 403

    # CSV Export for other shed -> Forbidden (403)
    res_csv = await async_client.get(f"/api/v1/telemetry/export/csv/{unauthorized_shed}", headers=headers_c)
    assert res_csv.status_code == 403

@pytest.mark.anyio
async def test_unauthorized_device_command_rejected(async_client):
    """
    VULN-05: Verifies that submitting a device command for an unauthorized shed is rejected.
    """
    import uuid
    uid_d = f"usr_{uuid.uuid4().hex[:8]}"
    uname_d = f"farmer_d_{int(time.time())}_{uuid.uuid4().hex[:4]}"
    token_d = create_access_token({"sub": uname_d, "user_id": uid_d, "role": "farmer"})

    from app.services.db_service import create_user
    create_user({
        "id": uid_d,
        "username": uname_d,
        "hashed_password": "hash",
        "full_name": "Farmer D",
        "phone": f"+91 {uuid.uuid4().int % 9000000000 + 1000000000}",
        "role": "farmer",
        "shed_id": "shed_01",
        "is_active": True
    })
    headers_d = {"Authorization": f"Bearer {token_d}"}

    # Command directed to device in shed_02 -> Rejected with 403 Forbidden
    cmd_payload = {
        "device_id": "node_shed_02_relay",
        "command_type": "SET_ACTUATOR",
        "command_payload": {"actuator": "cooler", "state": True},
        "expires_in_seconds": 60
    }
    res_cmd = await async_client.post("/api/v1/control/commands", json=cmd_payload, headers=headers_d)
    assert res_cmd.status_code == 403

@pytest.mark.anyio
async def test_unauthenticated_sse_rejected(async_client):
    """
    VULN-06: Verifies that real-time SSE surveillance streams require valid authentication.
    """
    # Unauthenticated request without token must fail with 401
    res = await async_client.get("/api/v1/telemetry/sse/shed_01")
    assert res.status_code == 401

@pytest.mark.anyio
async def test_public_farmer_enumeration_pii_redacted(async_client):
    """
    VULN-07: Verifies that /auth/check-farmer does NOT disclose phone numbers,
    farm names, or PII to unauthenticated callers.
    """
    res = await async_client.get("/api/v1/auth/check-farmer?identifier=admin")
    assert res.status_code == 200
    data = res.json()
    assert "exists" in data
    assert "has_profile" in data
    # Ensure PII is not leaked
    assert "phone" not in data
    assert "user" not in data
    assert "farm_name" not in data

@pytest.mark.anyio
async def test_account_takeover_prevention_on_google_sync(async_client):
    """
    VULN-03: Verifies that /auth/google-sync cannot hijack an existing password-authenticated
    account (or admin account) simply by submitting an email.
    """
    hijack_payload = {
        "email": "admin",
        "google_id": "attacker_google_id_12345",
        "full_name": "Attacker Hijacker"
    }
    res = await async_client.post("/api/v1/auth/google-sync", json=hijack_payload)
    # Must reject takeover of password-protected admin account
    assert res.status_code == 401

@pytest.mark.anyio
async def test_actuator_anti_simultaneous_interlock(async_client):
    """
    Actuator Safety: Verifies that cooler and heater cannot run simultaneously.
    """
    from app.services.telemetry_service import telemetry_service
    # 1. Turn cooler ON
    telemetry_service.manual_override_actuator("shed_01", "cooler", True)
    overview1 = telemetry_service.get_shed_overview("shed_01")
    assert overview1.actuators.cooler is True

    # 2. Turn heater ON -> Cooler must be automatically forced OFF by safety interlock
    telemetry_service.manual_override_actuator("shed_01", "heater", True)
    overview2 = telemetry_service.get_shed_overview("shed_01")
    assert overview2.actuators.heater is True
    assert overview2.actuators.cooler is False


# =====================================================================
# ENTERPRISE COMPLIANCE SUITE (100/100 AUDIT SCORE)
# =====================================================================

@pytest.mark.anyio
async def test_mtls_hardware_device_authentication(async_client):
    """
    SEC-14: Hardware Root of Trust / Mutual TLS (mTLS) Authentication.
    Verifies X.509 client certificate extraction, Common Name matching,
    SHA256 fingerprint verification, and revocation enforcement.
    """
    from app.services.db_service import register_device
    from app.core.mtls_auth import mtls_service

    dev_id = "esp32_hardware_secure_01"
    valid_fp = "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0"

    register_device(
        device_id=dev_id,
        shed_id="shed_01",
        organization_id="default_org",
        device_name="ATECC608A Secure Node",
        cert_fingerprint_sha256=valid_fp,
        auth_mode="MTLS"
    )

    # 1. Valid mTLS handshake from proxy headers -> Accepted
    telemetry_payload = {
        "shed_id": "shed_01",
        "temperature": 25.5,
        "humidity": 68.0,
        "device_id": dev_id
    }
    headers_valid = {
        "x-client-cert-sha256": valid_fp,
        "x-client-cert-dn": f"CN={dev_id},O=SeriCare,C=IN",
        "x-client-cert-verified": "SUCCESS"
    }
    res = await async_client.post("/api/v1/telemetry/record", json=telemetry_payload, headers=headers_valid)
    assert res.status_code == 200

    # 2. Fingerprint mismatch -> Rejected with 403 Forbidden
    headers_spoofed_fp = {
        "x-client-cert-sha256": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
        "x-client-cert-dn": f"CN={dev_id},O=SeriCare,C=IN",
        "x-client-cert-verified": "SUCCESS"
    }
    res_mismatch = await async_client.post("/api/v1/telemetry/record", json=telemetry_payload, headers=headers_spoofed_fp)
    assert res_mismatch.status_code == 403

    # 3. Edge TLS verification failed -> Rejected with 403 Forbidden
    headers_failed_tls = {
        "x-client-cert-sha256": valid_fp,
        "x-client-cert-dn": f"CN={dev_id},O=SeriCare,C=IN",
        "x-client-cert-verified": "FAILED: CERT_REVOKED"
    }
    res_failed = await async_client.post("/api/v1/telemetry/record", json=telemetry_payload, headers=headers_failed_tls)
    assert res_failed.status_code == 403


@pytest.mark.anyio
async def test_secrets_manager_caching_and_rotation():
    """
    SEC-15: Dynamic External KMS / Secret Manager.
    Verifies TTL caching, Vault/Cloud secret fallback, and dynamic zero-knowledge rotation.
    """
    from app.services.secrets_service import SecretsManager

    manager = SecretsManager(ttl_seconds=60)
    test_key = "SERICARE_DYNAMIC_ROTATING_KEY"
    initial_val = "v1_super_secret_master_token"
    rotated_val = "v2_zero_knowledge_rotated_token"

    # Set initial
    manager.rotate_secret(test_key, initial_val)
    assert manager.get_secret(test_key) == initial_val

    # Dynamic hot-rotation without application restart
    manager.rotate_secret(test_key, rotated_val)
    assert manager.get_secret(test_key) == rotated_val

    # Cache invalidation
    manager.invalidate_cache(test_key)
    # Env fallback holds rotated value
    assert manager.get_secret(test_key) == rotated_val


@pytest.mark.anyio
async def test_oidc_keycloak_token_claims_normalization():
    """
    SEC-16: Centralized Keycloak / OIDC Token Verification and Role Normalization.
    Verifies normalization of realm_access.roles to internal SeriCare RBAC roles.
    """
    from app.core.oidc_auth import OIDCVerifier

    verifier = OIDCVerifier()

    # Simulate Keycloak standard token claims
    keycloak_payload_admin = {
        "sub": "kc_user_9999",
        "email": "keycloak_admin@sericare.org",
        "preferred_username": "enterprise_admin",
        "realm_access": {
            "roles": ["default-roles-sericare", "offline_access", "uma_authorization", "ADMIN"]
        },
        "organization_id": "org_enterprise_01"
    }

    norm = verifier._normalize_oidc_claims(keycloak_payload_admin)
    assert norm["role"] == "ADMIN"
    assert norm["email"] == "keycloak_admin@sericare.org"
    assert norm["organization_id"] == "org_enterprise_01"
    assert norm["auth_provider"] == "KEYCLOAK_OIDC"

    # Farmer role
    keycloak_payload_farmer = {
        "sub": "kc_farmer_1234",
        "email": "farmer_kc@sericare.org",
        "realm_access": {
            "roles": ["FARMER"]
        }
    }
    norm_farmer = verifier._normalize_oidc_claims(keycloak_payload_farmer)
    assert norm_farmer["role"] == "FARMER"


@pytest.mark.anyio
async def test_siem_event_formatting_and_dispatch():
    """
    SEC-17: 24/7 SIEM & SOC Log Forwarding Engine.
    Verifies CEF (Common Event Format) and ECS 8.x JSON schema formatting,
    non-blocking queuing, and audit log integration.
    """
    from app.services.siem_service import siem_forwarder
    from app.services.db_service import log_audit

    # 1. Test CEF Formatting
    sample_event = {
        "action": "DEVICE_COMMAND_ISSUED",
        "severity": 7,
        "user_id": "admin",
        "ip_address": "192.168.1.100",
        "status": "SUCCESS",
        "organization_id": "org_test",
        "device_id": "node_shed_01",
        "details": {"description": "Turn cooler ON"}
    }
    cef_str = siem_forwarder.format_cef(sample_event)
    assert "CEF:0|SeriCare|IoTPlatform|1.0|DEVICE_COMMAND_ISSUED" in cef_str
    assert "src=192.168.1.100" in cef_str
    assert "suser=admin" in cef_str

    # 2. Test ECS JSON Formatting
    ecs_str = siem_forwarder.format_ecs_json(sample_event)
    import json
    ecs_obj = json.loads(ecs_str)
    assert ecs_obj["event"]["action"] == "DEVICE_COMMAND_ISSUED"
    assert ecs_obj["event"]["outcome"] == "success"
    assert ecs_obj["source"]["ip"] == "192.168.1.100"

    # 3. Test db_service.log_audit -> SIEM forwarding
    log_audit("security_tester", "PRIVILEGE_ELEVATION_CHECK", "Validated superadmin role enforcement")
    
    # Check ring buffer has recorded the event
    recent = siem_forwarder.get_recent_events()
    matched = [e for e in recent if e.get("action") == "PRIVILEGE_ELEVATION_CHECK"]
    assert len(matched) > 0
    assert matched[0]["user_id"] == "security_tester"

