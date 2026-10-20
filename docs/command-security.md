# Remote Command & Actuator Safety Lifecycle
**Target Actuators**: Evaporative Foggers/Coolers, Infrared Heaters, Exhaust Ventilation Fans, Photoperiod Lamps  
**Safety Classification**: High-Impact Physical Actuation  

---

## 1. The 6-Stage Command State Machine

To prevent physical damage, electrical fire, or loss of silkworm life, commands cannot be blindly applied. SeriCare enforces an auditable 6-stage lifecycle:

```
[ 1. REQUESTED ]
   │ Caller submits command via Web Dashboard or Mobile App
   ▼
[ 2. AUTHORIZED ]
   │ Server validates caller tenancy, role, and physical safety interlocks
   ▼
[ 3. QUEUED ]
   │ Command persisted in `device_commands` table with correlation ID and expiry
   ▼
[ 4. SENT ]
   │ Command delivered to hardware node via WebSocket, SSE, or polling stream
   ▼
[ 5. ACKNOWLEDGED ]
   │ Hardware node verifies receipt, battery/relay state, and checksum
   ▼
[ 6. APPLIED ]
   │ Relay physically energized/de-energized; hardware reports verified new state
```

### Terminal Failure States
- **`REJECTED`**: Command violated safety interlock or hardware safety limits.
- **`EXPIRED`**: Command remained unacknowledged past its `expires_at` window (default 60 seconds).
- **`FAILED`**: Hardware relay malfunction, power brownout, or actuator failure reported by node.

---

## 2. Safety Interlocks & Collision Prevention

1. **Anti-Simultaneous Run Interlock**:
   The cooler (water fogger) and heater MUST NEVER operate at the same time.
   - If a command requests `cooler = True`, the server and rules engine automatically enforce `heater = False`.
   - If a command requests `heater = True`, the server automatically enforces `cooler = False`.
2. **Exhaust Fan Safety Co-Trigger**:
   Whenever the cooler or heater runs, the exhaust fan is automatically engaged to ensure uniform air circulation and prevent localized hot/cold micro-pockets that kill delicate chawki larvae.
3. **Idempotency & Replay Prevention**:
   Every command requires a `correlation_id` (UUIDv4). Re-submitting the same correlation ID returns the existing command state without executing duplicate physical actuations.
4. **Command Expiry Enforcement**:
   Expired commands are never replayed. If an IoT node reconnects after an 8-hour internet outage, commands older than 60 seconds are automatically marked `EXPIRED` and ignored.

---

## 3. Emergency Override & Failsafe Behavior

If cloud connectivity is lost:
- The ESP32 local firmware defaults to autonomous fallback mode:
  - If Temperature > 30°C: Cooler ON, Fan ON.
  - If Temperature < 22°C: Heater ON, Fan ON.
  - If Air Quality < 50%: Fan ON.
- Manual emergency buttons in the shed provide direct physical relay disconnection.
