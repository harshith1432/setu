# Incident Response Plan & Security Playbooks
**Scope**: Production IoT Infrastructure, Cloud Services, Telemetry Streams, Actuator Controls  
**Framework**: NIST SP 800-61 Rev. 2 (Computer Security Incident Handling Guide)  

---

## 1. Incident Severity Levels

- **SEV-1 (Critical)**: Active unauthorized actuator control, unauthorized remote command execution, database breach, compromise of superadmin credentials.
- **SEV-2 (High)**: Cross-tenant data leakage (IDOR exploit), persistent authentication bypass attempt, rogue hardware node injecting telemetry.
- **SEV-3 (Medium)**: API rate limit abuse, suspicious webhook failures, brute-force login attempts against farmer accounts.
- **SEV-4 (Low)**: Minor configuration drift, isolated client-side script error, non-exploitable bug.

---

## 2. Emergency Security Playbooks

### Playbook 1: Compromised IoT Hardware Node / Rogue Sensor
1. **Identification**: Alert in `audit_logs` showing abnormal sequence jump or outlier telemetry.
2. **Containment**:
   Immediately invoke device revocation:
   ```sql
   UPDATE devices SET status = 'REVOKED' WHERE device_id = 'compromised_node_id';
   ```
3. **Eradication**: Disconnect device from local Wi-Fi / cellular gateway; re-flash with fresh unique credentials.
4. **Recovery**: Re-provision device with new `device_key_hash`.

### Playbook 2: Leaked Admin Credentials / Token Compromise
1. **Containment**:
   - Rotate `SETU_SECRET_KEY` environment variable in deployment settings (Render / Cloud Run).
   - This instantly invalidates all outstanding active JWT access tokens across the cluster.
2. **Eradication**:
   - Reset compromised administrator password in database with high-entropy Argon2 hash.
3. **Recovery**:
   - Administrators re-login and establish new authenticated sessions.

### Playbook 3: Emergency Actuator Shutdown (Physical Failsafe)
1. **Trigger**: Uncommanded heating, relay oscillation, or sensor anomaly risking silk batch mortality.
2. **Execution**:
   Super Admin invokes Emergency Override:
   `POST /api/v1/admin/emergency/bypass` with `{"action": "COOLDOWN_ALL", "shed_id": "shed_01"}`.
3. **Hardware Action**: Backend and gateway de-energize all high-voltage relays immediately.
