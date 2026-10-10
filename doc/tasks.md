# SeriCare --- Development Task Plan

## 1. Development Strategy

Build SeriCare in vertical slices instead of developing the entire
frontend, backend and IoT layers independently.

A vertical slice should work end-to-end:

``` text
Sensor
 ↓
ESP32
 ↓
MQTT
 ↓
Backend
 ↓
Database
 ↓
App
```

Then add control:

``` text
App
 ↓
Backend
 ↓
MQTT
 ↓
ESP32
 ↓
Relay
```

------------------------------------------------------------------------

# Phase 0 --- Project Setup

## T-001 Repository Structure

Create repositories/modules for:

-   Backend
-   Frontend
-   Firmware
-   Infrastructure
-   Documentation

### Acceptance

All projects have:

-   README
-   Environment configuration
-   Development instructions
-   Basic CI

------------------------------------------------------------------------

## T-002 Environment Configuration

Configure:

-   Database URL
-   MQTT broker URL
-   MQTT credentials
-   JWT/session secrets
-   Weather API credentials
-   Notification credentials
-   AI credentials

Never commit secrets.

------------------------------------------------------------------------

# Phase 1 --- Backend Foundation

## T-101 Flask Application

Create Flask project structure.

Implement:

-   Application factory
-   Configuration
-   Blueprints/modules
-   Error handling
-   Logging

------------------------------------------------------------------------

## T-102 PostgreSQL

Create database connection.

Implement migrations.

------------------------------------------------------------------------

## T-103 Authentication

Implement:

-   Registration
-   Login
-   Logout
-   Password management
-   Authentication middleware

------------------------------------------------------------------------

## T-104 Authorization

Implement ownership rules:

``` text
User
 ↓
Farm
 ↓
Shed
 ↓
Device
```

A user must not access another user's device.

------------------------------------------------------------------------

# Phase 2 --- Database

## T-201 Core Models

Create:

-   User
-   Farm
-   Shed
-   Device
-   Sensor
-   GrowthStage
-   EnvironmentRule

------------------------------------------------------------------------

## T-202 Telemetry Models

Create:

-   SensorReading
-   DeviceState
-   DeviceEvent
-   DeviceHealth

------------------------------------------------------------------------

## T-203 Command Models

Create:

-   DeviceCommand
-   CommandAcknowledgment
-   ControlEvent

------------------------------------------------------------------------

## T-204 Notification Models

Create:

-   Notification
-   NotificationPreference

------------------------------------------------------------------------

# Phase 3 --- IoT Prototype

## T-301 ESP32 Sensor Reading

Implement:

-   Temperature sensor
-   Humidity sensor
-   Sensor validation

------------------------------------------------------------------------

## T-302 Light Sensor Integration

Implement:

- Ambient/light sensor reading
- Sensor calibration
- Light data validation
- MQTT telemetry field for light

---

## T-302 Wi-Fi Connection

Implement:

-   Wi-Fi setup
-   Reconnect
-   Connection status

------------------------------------------------------------------------

## T-303 MQTT Connection

Implement:

-   MQTT authentication
-   Connect/reconnect
-   Subscribe
-   Publish

------------------------------------------------------------------------

## T-304 Telemetry Publishing

Publish:

``` json
{
  "temperature": 26.8,
  "humidity": 74,
  "timestamp": "..."
}
```

------------------------------------------------------------------------

## T-305 Backend MQTT Consumer

Receive telemetry.

Validate it.

Store it.

Update latest state.

------------------------------------------------------------------------

# Phase 4 --- Live Dashboard

## T-401 Dashboard API

Create endpoint for:

-   Current environment
-   Device status
-   Growth stage
-   Active control state

------------------------------------------------------------------------

## T-402 Frontend Dashboard

Build:

-   Overall status
-   Temperature card
-   Humidity card
-   Growth stage
-   Device status

------------------------------------------------------------------------

## T-403 Real-Time Updates

Implement WebSocket/SSE or efficient polling.

Show:

-   Live readings
-   Last updated
-   Device offline state

------------------------------------------------------------------------

# Phase 5 --- Device Control

## T-501 Relay Integration

Connect ESP32 to safe relay hardware.

Test using a low-risk prototype load before real equipment.

------------------------------------------------------------------------

## T-502 Command API

Example:

``` text
POST /api/devices/{device_id}/commands
```

------------------------------------------------------------------------

## T-503 MQTT Commands

Backend publishes control commands.

------------------------------------------------------------------------

## T-504 Device Command Handler

ESP32 receives command.

Validates it.

Controls actuator.

Returns acknowledgment.

------------------------------------------------------------------------

## T-505 Command State Tracking

Implement:

``` text
CREATED
VALIDATED
SENT
RECEIVED
EXECUTED
FAILED
```

------------------------------------------------------------------------

# Phase 6 --- Safety Layer

## T-601 Sensor Validation

Implement:

-   Missing reading
-   Invalid values
-   Stale reading
-   Sensor failure

------------------------------------------------------------------------

## T-602 Command Validation

Reject unsafe settings.

------------------------------------------------------------------------

## T-603 Heating/Cooling Interlock

Prevent incompatible simultaneous actions.

------------------------------------------------------------------------

## T-604 Local Device Safety

Implement local safety logic on ESP32.

------------------------------------------------------------------------

## T-605 Offline Mode

Test:

-   Internet loss
-   MQTT loss
-   Backend downtime
-   Sensor failure

------------------------------------------------------------------------

# Phase 7 --- Growth Stage Engine

## T-701 Growth Stage Model

Implement:

-   1st instar
-   2nd instar
-   3rd instar
-   4th instar
-   5th instar

------------------------------------------------------------------------

## T-702 Rule Configuration

Store stage-specific configuration in database.

------------------------------------------------------------------------

## T-703 Stage Selection UI

Allow farmer/admin to select stage.

------------------------------------------------------------------------

## T-704 Stage-Aware Status

Environment status must use the current stage.

------------------------------------------------------------------------

# Phase 8 --- Automatic Control

## T-801 Rules Engine

Implement:

``` text
Sensor
 ↓
Validation
 ↓
Growth stage
 ↓
Preferred range
 ↓
Safety
 ↓
Decision
```

------------------------------------------------------------------------

## T-802 Hysteresis

Prevent rapid actuator switching.

------------------------------------------------------------------------

## T-803 Minimum Runtime

Prevent rapid cycling.

------------------------------------------------------------------------

## T-804 Automatic Command Execution

Rules engine creates validated device commands.

------------------------------------------------------------------------

## T-805 Verification

After command:

``` text
Command
 ↓
ACK
 ↓
New telemetry
 ↓
Verify
```

------------------------------------------------------------------------

# Phase 9 --- Weather Intelligence

## T-901 Weather Integration

Get:

-   Outside temperature
-   Outside humidity
-   Forecast

------------------------------------------------------------------------

## T-902 Weather Storage

Store useful weather observations.

------------------------------------------------------------------------

## T-903 Trend Detection

Calculate:

-   Rising temperature
-   Falling temperature
-   Humidity trend
-   Stability

------------------------------------------------------------------------

# Phase 10 --- Notifications

## T-1001 Notification Engine

Create event-based notifications.

------------------------------------------------------------------------

## T-1002 Deduplication

Prevent notification spam.

------------------------------------------------------------------------

## T-1003 Recovery Notifications

Notify when conditions return to normal.

------------------------------------------------------------------------

# Phase 11 --- AI

## T-1101 AI Assistant

Implement farmer-friendly Q&A.

------------------------------------------------------------------------

## T-1102 Explanation Generator

Explain deterministic system decisions.

------------------------------------------------------------------------

## T-1103 Recommendation Layer

Combine:

-   Current state
-   Growth stage
-   Weather
-   History

------------------------------------------------------------------------

## T-1104 AI Guardrails

AI must not:

-   Invent readings
-   Bypass safety
-   Claim unverified hardware actions
-   Directly override rules

------------------------------------------------------------------------

# Phase 12 --- History & Insights

## T-1201 Historical API

Implement time-range queries.

------------------------------------------------------------------------

## T-1202 Charts

Create:

-   Temperature chart
-   Humidity chart
-   Equipment activity chart

------------------------------------------------------------------------

## T-1203 Insights

Create:

-   Daily
-   Weekly
-   Monthly

------------------------------------------------------------------------

# Phase 13 --- Multilingual UI

## T-1301 Translation System

Centralize translations.

------------------------------------------------------------------------

## T-1302 English

Complete all screens.

------------------------------------------------------------------------

## T-1303 Kannada

Translate all user-facing content.

------------------------------------------------------------------------

## T-1304 Telugu

Translate all user-facing content.

------------------------------------------------------------------------

# Phase 14 --- Advanced Mode

## T-1401 Exact Metrics

Show exact values.

## T-1402 Manual Control

Provide safe controls.

## T-1403 Device Diagnostics

Show:

-   Online state
-   Last seen
-   Sensor health
-   Firmware

------------------------------------------------------------------------

# Phase 15 --- Admin

## T-1501 Device Registration

Admin can register devices.

## T-1502 Farm/Shed Management

Admin can manage deployment.

## T-1503 Rule Management

Admin can manage versioned rules.

## T-1504 Audit Logs

Track important changes.

------------------------------------------------------------------------

# Phase 16 --- Testing

## T-1601 Unit Tests

Test:

-   Rules
-   API
-   Commands
-   Validation

## T-1602 Integration Tests

Test:

``` text
ESP32 → MQTT → Backend → DB
```

and:

``` text
App → Backend → MQTT → ESP32
```

## T-1603 Failure Tests

Test:

-   MQTT unavailable
-   Device offline
-   Sensor failure
-   Database unavailable
-   Weather API unavailable

## T-1604 Load Tests

Test increasing:

-   Users
-   Devices
-   Telemetry rate
-   API traffic

------------------------------------------------------------------------

# Phase 17 --- Security

Implement:

-   TLS
-   Secure authentication
-   Device authentication
-   Authorization
-   Secret management
-   Rate limiting
-   Input validation
-   Audit logging
-   Dependency scanning
-   Secure firmware practices

------------------------------------------------------------------------

# Phase 18 --- Deployment

Production architecture:

``` text
Nginx
 ↓
Flask
 ↓
PostgreSQL
Redis
Celery
MQTT
```

Deploy with:

-   HTTPS
-   Monitoring
-   Backups
-   Logs
-   Health checks

------------------------------------------------------------------------

# Phase 19 --- Field Pilot

Start with a small number of rearing sheds.

Measure:

-   Sensor accuracy
-   Device reliability
-   Command latency
-   Automation stability
-   False alerts
-   Farmer usability
-   Network reliability

Do not move directly from laboratory prototype to large deployment.

------------------------------------------------------------------------

# Definition of Done

A feature is complete only when:

-   Code exists
-   API is implemented where required
-   UI is implemented where required
-   Database changes are migrated
-   Error handling exists
-   Security is considered
-   Tests exist
-   Documentation exists
-   Real hardware behavior is verified where applicable
