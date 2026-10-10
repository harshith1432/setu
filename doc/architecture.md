# SeriCare --- System Architecture

## 1. Architecture Overview

SeriCare is a distributed IoT platform consisting of:

1.  Farmer application
2.  Backend API
3.  MQTT messaging layer
4.  IoT devices
5.  Sensors
6.  Actuators
7.  Database
8.  Real-time state/cache
9.  Automation/rules engine
10. Weather service
11. AI/recommendation service
12. Notification service
13. Monitoring and audit layer

High-level architecture:

``` text
                         ┌─────────────────────┐
                         │     Farmer App      │
                         │ Mobile / Web        │
                         └──────────┬──────────┘
                                    │ HTTPS
                                    │ WebSocket/SSE
                                    ▼
                         ┌─────────────────────┐
                         │     Flask API       │
                         │ Auth / REST / RBAC  │
                         └───────┬─────┬───────┘
                                 │     │
                    ┌────────────┘     └─────────────┐
                    ▼                                ▼
             ┌─────────────┐                  ┌─────────────┐
             │ PostgreSQL  │                  │    Redis    │
             │ Persistent  │                  │ Live State  │
             │ Data        │                  │ Pub/Sub     │
             └─────────────┘                  └──────┬──────┘
                                                    │
                                                    ▼
                                             ┌─────────────┐
                                             │ MQTT Broker │
                                             └──────┬──────┘
                                                    │
                         ┌──────────────────────────┼──────────────────┐
                         ▼                          ▼                  ▼
                    ┌─────────┐                ┌─────────┐        ┌─────────┐
                    │ ESP32   │                │ ESP32   │        │ ESP32   │
                    │ Shed 01 │                │ Shed 02 │        │ Shed 03 │
                    └────┬────┘                └─────────┘        └─────────┘
                         │
                ┌────────┼───────────┐
                ▼        ▼           ▼
             Sensors   Sensors    Relays
                │                    │
          Temperature             Heater
          Humidity                 Cooler
          Other                    Fan
```

------------------------------------------------------------------------

## 2. Architectural Principles

### 2.1 IoT-first

The system must treat hardware as a first-class component, not an
optional add-on.

### 2.2 Bidirectional communication

Data must flow in both directions:

``` text
Device → Backend → App
App → Backend → Device
```

### 2.3 Safety before intelligence

Hard safety rules must be enforceable without AI.

### 2.4 Offline resilience

Basic device safety must continue without cloud connectivity.

### 2.5 Source of truth

Persistent configuration and historical data belong in PostgreSQL.

Short-lived/live state can be held in Redis.

The device remains the immediate authority for physical actuator state.

------------------------------------------------------------------------

## 3. Application Layer

The farmer-facing application should contain:

-   Authentication
-   Onboarding
-   Dashboard
-   Environment
-   Growth Stage
-   AI Assistant
-   Notifications
-   History
-   Insights
-   Advanced Mode
-   Settings

The UI should consume backend APIs rather than communicate directly with
IoT devices.

This prevents exposing device credentials or MQTT infrastructure to the
client.

------------------------------------------------------------------------

## 4. Backend Layer

Recommended backend:

**Python + Flask**

Core services/modules:

``` text
api/
auth/
users/
farms/
sheds/
devices/
sensors/
mqtt/
control/
growth/
rules/
weather/
ai/
notifications/
analytics/
audit/
settings/
```

### API Responsibilities

-   Authentication
-   Authorization
-   CRUD operations
-   Device registration
-   Sensor data access
-   Control commands
-   Dashboard aggregation
-   Historical queries
-   Notification management
-   Configuration

------------------------------------------------------------------------

## 5. MQTT Layer

MQTT should provide lightweight bidirectional messaging.

Example topic hierarchy:

``` text
sericare/{farm_id}/{shed_id}/{device_id}/telemetry
sericare/{farm_id}/{shed_id}/{device_id}/state
sericare/{farm_id}/{shed_id}/{device_id}/command
sericare/{farm_id}/{shed_id}/{device_id}/ack
sericare/{farm_id}/{shed_id}/{device_id}/event
sericare/{farm_id}/{shed_id}/{device_id}/health
```

Example telemetry:

``` json
{
  "device_id": "SHED001",
  "timestamp": "2026-10-07T10:30:00Z",
  "temperature": 26.8,
  "humidity": 74.0
}
```

Example command:

``` json
{
  "command_id": "cmd_123",
  "command": "set_temperature",
  "target": 26.0,
  "mode": "auto"
}
```

Example acknowledgment:

``` json
{
  "command_id": "cmd_123",
  "status": "accepted",
  "device_temperature": 26.8
}
```

------------------------------------------------------------------------

## 6. Device Architecture

The prototype can use an ESP32 or similar microcontroller.

Suggested components:

-   ESP32
-   Temperature/humidity/light sensors
-   Relay module
-   Fan/cooling equipment
-   Heating equipment
-   Optional humidifier/dehumidifier
-   Local status indicators
-   Stable power supply

### Device software responsibilities

``` text
Boot
 ↓
Load configuration
 ↓
Initialize sensors
 ↓
Connect Wi-Fi
 ↓
Connect MQTT
 ↓
Publish online status
 ↓
Read sensors periodically
 ↓
Publish telemetry
 ↓
Listen for commands
 ↓
Validate commands locally
 ↓
Control actuator
 ↓
Publish state/acknowledgment
```

------------------------------------------------------------------------

## 7. Device Safety

The device should implement basic local protection.

Examples:

-   Maximum heater duration
-   Maximum cooling duration
-   Sensor failure detection
-   Invalid command rejection
-   Emergency shutdown
-   Watchdog
-   Network disconnect behavior
-   Safe startup state

The exact thresholds must be established from validated
engineering/sericulture requirements rather than invented in software.

------------------------------------------------------------------------

## 8. Data Flow --- Sensor to Phone

``` text
Temperature Sensor
        ↓
ESP32
        ↓
MQTT telemetry
        ↓
MQTT Broker
        ↓
MQTT Consumer
        ↓
Validation
        ↓
PostgreSQL + Redis
        ↓
WebSocket/SSE or API
        ↓
Farmer App
```

------------------------------------------------------------------------

## 9. Data Flow --- Phone to Hardware

``` text
Farmer changes target
        ↓
App
        ↓
POST /devices/{id}/commands
        ↓
Authentication + Authorization
        ↓
Command Validation
        ↓
Safety/Rules Validation
        ↓
Command Record
        ↓
MQTT Publish
        ↓
ESP32
        ↓
Local Validation
        ↓
Relay / Actuator
        ↓
ACK
        ↓
Backend
        ↓
App
```

------------------------------------------------------------------------

## 10. Automatic Control Flow

``` text
Telemetry
   ↓
Normalize/validate
   ↓
Current growth stage
   ↓
Preferred range
   ↓
Safety range
   ↓
Trend
   ↓
Outside weather
   ↓
Rules Engine
   ↓
Action decision
   ↓
Command validation
   ↓
MQTT
   ↓
Device
```

------------------------------------------------------------------------

## 11. AI Architecture

AI should not replace the safety/control engine.

Recommended separation:

``` text
                    Sensor Data
                         │
                         ▼
                  Rules Engine
                         │
                  Safe Decision
                         │
                         ▼
                    Controller
                         │
                       MQTT
                         │
                       Device


Sensor + History + Weather + Growth Stage
                         │
                         ▼
                    AI Service
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
          Explanation Prediction Recommendation
```

AI responsibilities:

-   Explain decisions
-   Summarize conditions
-   Identify patterns
-   Generate farmer-friendly recommendations
-   Answer educational questions
-   Provide context around weather and trends

AI must not be allowed to bypass safety limits.

------------------------------------------------------------------------

## 12. Database Architecture

Core tables:

``` text
users
farms
sheds
devices
device_credentials
sensors
sensor_readings
light_readings
device_state
device_commands
control_events
growth_stages
environment_rules
weather_data
notifications
notification_preferences
ai_recommendations
audit_logs
```

### Relationship example

``` text
User
 └── Farm
      └── Shed
           ├── Device
           │    ├── Sensors
           │    └── Actuators
           ├── Growth Stage
           ├── Rules
           └── Readings
```

------------------------------------------------------------------------

## 13. Real-Time State

Redis can store:

-   Latest temperature
-   Latest humidity
-   Device online status
-   Current actuator state
-   Current control mode
-   Recent alert state

PostgreSQL remains the durable historical source.

------------------------------------------------------------------------

## 14. Weather Integration

A weather service can provide:

-   Current outside temperature
-   Outside humidity
-   Forecast
-   Weather condition
-   Trend

Weather data should be associated with the farm/shed location at a
suitable geographic resolution.

Do not make exact actuator control dependent solely on an external
weather API.

------------------------------------------------------------------------

## 15. Notifications

Notification service should support:

-   In-app notifications
-   Push notifications
-   Future SMS/WhatsApp integration if required

Events should be prioritized:

``` text
INFO
WARNING
CRITICAL
```

Avoid sending repetitive alerts for the same condition.

------------------------------------------------------------------------

## 16. Security Architecture

Security layers:

``` text
User Authentication
       ↓
Authorization
       ↓
Farm/Shed ownership check
       ↓
Device authorization
       ↓
Command validation
       ↓
Audit log
       ↓
MQTT
       ↓
Device authentication
       ↓
Local safety validation
```

Never trust the mobile app or device input blindly.

------------------------------------------------------------------------

## 17. Scalability

The initial deployment can be a modular Flask application.

As scale increases:

``` text
Nginx
 ↓
Flask API replicas
 ↓
PgBouncer
 ↓
PostgreSQL

Redis
 ↓
Celery workers

MQTT Broker
 ↓
IoT devices
```

Background tasks such as analytics, notifications and heavy AI
processing should be moved to workers rather than blocking API requests.

------------------------------------------------------------------------

## 18. Observability

Track:

-   API errors
-   MQTT connection failures
-   Device offline events
-   Sensor failures
-   Command failures
-   Command latency
-   Queue backlog
-   Database performance
-   Notification failures
-   AI service failures

Every important control action should have an audit trail.

------------------------------------------------------------------------

## 19. Recommended Deployment Evolution

### Prototype

``` text
ESP32 → MQTT → Flask → PostgreSQL
                    ↓
                  App
```

### Production

``` text
Load Balancer
      ↓
Flask API replicas
      ↓
Redis / PostgreSQL
      ↓
MQTT Broker
      ↓
IoT fleet
```

Use managed/production-grade services where appropriate.

------------------------------------------------------------------------

## 20. Architecture Golden Rule

The architecture must preserve:

> **Cloud intelligence can improve the system, but loss of cloud
> connectivity must not create an unsafe physical environment.**
