# SeriCare --- Project Memory / AI Context

## 1. Purpose

This file is the persistent project context for SeriCare.

Any developer, AI coding assistant or future contributor should read
this document before making architectural or product changes.

The goal is to prevent repeated explanations and inconsistent
implementation decisions.

------------------------------------------------------------------------

# 2. Project Identity

**Product Name:** SeriCare

**Concept:** Smart IoT Sericulture Environment Management and Automated
Control System

**Target:** Silkworm rearing environment management

**Initial Region:** Mulbagal, Karnataka, India

**Initial Languages:**

-   English
-   Kannada
-   Telugu

------------------------------------------------------------------------

# 3. Core Product Idea

SeriCare is not simply a sensor dashboard.

It is an integrated:

``` text
IoT Monitoring
+
Automated Environmental Control
+
Growth-Stage Intelligence
+
Weather Awareness
+
Explainable AI
+
Farmer Mobile Interface
```

The product should help a farmer understand and manage the rearing
environment without requiring technical knowledge.

------------------------------------------------------------------------

# 4. Product Philosophy

The central philosophy is:

> **Don't make the farmer interpret the environment. Make the system
> interpret it for the farmer.**

Therefore:

Bad UX:

> Temperature = 26.8°C\
> Humidity = 74%

Better UX:

> 🟢 Ideal for Silkworms\
> Everything is normal.

And then allow exact values through Advanced Mode.

------------------------------------------------------------------------

# 5. Critical IoT Requirement

The system must support **two-way communication**.

### Device → App

``` text
Sensor
 ↓
ESP32
 ↓
MQTT
 ↓
Backend
 ↓
App
```

### App → Device

``` text
Phone
 ↓
Backend
 ↓
MQTT
 ↓
ESP32
 ↓
Relay
 ↓
Heater/Cooler/Fan
```

The farmer must be able to control the environment from the phone.

------------------------------------------------------------------------

# 6. Preferred Technology Direction

### Backend

Python / Flask

### Database

PostgreSQL

### Real-Time State

Redis

### Background Processing

Celery where needed

### IoT Controller

ESP32 or equivalent microcontroller

### IoT Communication

MQTT

### Frontend

Mobile-first web/app interface according to implementation choice

### Hardware

Temperature/humidity sensors + relays + environmental equipment

------------------------------------------------------------------------

# 7. Architecture Rule

Never make the mobile application communicate directly with MQTT
infrastructure using privileged credentials.

Correct:

``` text
App
 ↓
Backend
 ↓
MQTT
 ↓
Device
```

Not:

``` text
App
 ↓
MQTT
 ↓
Device
```

The backend must enforce authorization and safety validation.

------------------------------------------------------------------------

# 8. Control Philosophy

There are three control layers.

## Layer 1 --- Device Safety

Runs locally on the IoT device.

Purpose:

-   Prevent unsafe operation
-   Handle sensor failure
-   Handle communication failure
-   Provide emergency behavior

## Layer 2 --- Deterministic Backend Rules

Controls normal automation.

Inputs:

-   Temperature
-   Humidity
-   Growth stage
-   Trend
-   Weather
-   Configuration

## Layer 3 --- AI

Provides:

-   Explanations
-   Recommendations
-   Predictions
-   Farmer-friendly summaries
-   Educational assistance

AI does not bypass safety rules.

------------------------------------------------------------------------

# 9. Growth Stage Model

Initial stages:

1.  1st Instar
2.  2nd Instar
3.  3rd Instar
4.  4th Instar
5.  5th Instar

Each stage has configurable environmental requirements.

Never scatter growth-stage thresholds across source code.

Store them in a versioned rules/configuration system.

------------------------------------------------------------------------

# 10. Environmental Parameters

Primary:

-   Temperature
-   Humidity

Additional:

-   Outside temperature
-   Outside humidity
-   Weather forecast
-   Environmental trend
-   Equipment activity
-   Device health

Future:

-   Air quality
-   CO₂
-   Light
-   Additional biological/production indicators

------------------------------------------------------------------------

# 11. Main Modes

## User-Friendly Mode

Default.

Shows:

-   Simple status
-   Recommendations
-   Visual indicators
-   Current action
-   Growth stage
-   Alerts

## Advanced Mode

Optional.

Shows:

-   Exact values
-   Set points
-   Manual control
-   Device diagnostics
-   Historical data
-   Detailed configuration

------------------------------------------------------------------------

# 12. Automatic Mode

Automatic mode is the default recommended operating mode.

Conceptual flow:

``` text
Read sensor
 ↓
Validate
 ↓
Identify growth stage
 ↓
Load rules
 ↓
Check safety
 ↓
Analyze trend
 ↓
Consider weather
 ↓
Determine action
 ↓
Send command
 ↓
Verify device state
 ↓
Notify/explain
```

------------------------------------------------------------------------

# 13. Manual Mode

Manual mode is intended for experienced users.

Manual commands must still pass safety validation.

The farmer cannot use manual mode to bypass hardware safety limits.

------------------------------------------------------------------------

# 14. Explainable AI

When an automated action occurs, the farmer should be able to understand
it.

Example:

> **Cooling activated**
>
> Temperature is rising above the preferred range for the current growth
> stage. Cooling was activated automatically to bring the environment
> back toward the recommended range.

AI must use actual system data.

It must never invent:

-   Sensor readings
-   Device state
-   Weather
-   Actions
-   Scientific claims

------------------------------------------------------------------------

# 15. Weather-Aware Intelligence

The system should eventually anticipate environmental changes.

Example:

``` text
Indoor temperature: acceptable
Outside temperature: high
Indoor trend: rising
Forecast: hot
        ↓
Early warning / proactive recommendation
```

Weather should be a supporting signal, not the sole basis for
safety-critical control.

------------------------------------------------------------------------

# 16. Notifications

Preferred style:

Instead of:

> `TEMP > THRESHOLD`

Use:

> **Temperature is rising --- cooling has been activated.**

Notification categories:

-   Information
-   Warning
-   Critical
-   Recovery

Avoid notification spam using deduplication and cooldown logic.

------------------------------------------------------------------------

# 17. Offline Behavior

Internet failure must not make the physical system unsafe.

If cloud connectivity fails:

``` text
ESP32
 ↓
Local safe configuration
 ↓
Continue safe operation
```

When connectivity returns:

``` text
Reconnect
 ↓
Synchronize state
 ↓
Upload pending telemetry where supported
 ↓
Resume cloud communication
```

------------------------------------------------------------------------

# 18. Data Principles

Persistent records should include:

-   Sensor readings
-   Device status
-   Commands
-   Command acknowledgments
-   Control events
-   Notifications
-   Growth-stage changes
-   Rule versions
-   User actions
-   Audit logs

Every important physical control event should be traceable.

------------------------------------------------------------------------

# 19. Security Principles

Always:

-   Authenticate users
-   Authorize by farm/shed/device
-   Authenticate IoT devices
-   Encrypt network communication
-   Protect MQTT credentials
-   Validate commands
-   Log important control actions
-   Avoid hard-coded secrets
-   Apply rate limits
-   Protect APIs
-   Maintain firmware security

------------------------------------------------------------------------

# 20. Important UX Principle

The first dashboard should answer within seconds:

### What is the current condition?

> 🟢 Ideal

### What is the system doing?

> Cooling OFF

### What stage are the silkworms in?

> 3rd Instar

### Do I need to do anything?

> No action required.

------------------------------------------------------------------------

# 21. Initial Screens

The product concept includes:

1.  Language Selection & Onboarding
2.  Home Dashboard
3.  AI Assistant
4.  Environment Overview
5.  Growth Stage Guidance
6.  Research & Insights
7.  Advanced Manual Control
8.  Detailed Metrics
9.  System Settings
10. Notifications
11. Device Management
12. History/Insights

------------------------------------------------------------------------

# 22. Important Terminology

Use farmer-friendly terminology.

Preferred:

-   Ideal for Silkworms
-   Too Warm
-   Too Cool
-   Humidity Low
-   Cooling ON
-   Heating ON
-   Attention Required
-   Device Offline
-   Growth Stage

Avoid exposing internal technical identifiers to farmers.

------------------------------------------------------------------------

# 23. Engineering Principles

Prefer:

-   Modular services
-   Centralized configuration
-   Versioned rules
-   Strong typing/validation where practical
-   Automated tests
-   Clear logging
-   Idempotent device commands where possible
-   Explicit command states
-   Failure recovery
-   Observability

Avoid:

-   Business logic duplicated across frontend/backend/firmware
-   AI directly controlling relays
-   Hard-coded biological thresholds
-   Trusting client-provided device IDs
-   Treating stale data as live
-   Unbounded retries
-   Blocking API requests with long AI/hardware operations

------------------------------------------------------------------------

# 24. Source of Truth

### PostgreSQL

Persistent business and historical data.

### Redis

Fast/live state and transient coordination.

### MQTT

Messaging transport.

### ESP32

Immediate physical device state and local safety.

### Backend

Central application/business authority.

### AI

Interpretation and recommendation layer, not authoritative hardware
safety.

------------------------------------------------------------------------

# 25. Future Features

Possible future roadmap:

-   Multi-shed management
-   Multi-farm support
-   Predictive control
-   Energy optimization
-   Disease-risk prediction
-   Computer vision
-   Voice assistant
-   Local-language voice interaction
-   Expert knowledge base
-   Regional research insights
-   OTA firmware updates
-   Advanced analytics

------------------------------------------------------------------------

# 26. Development Rule for AI Coding Assistants

Before changing code, the AI/developer should:

1.  Read this file.
2.  Read `prd.md`.
3.  Read `architecture.md`.
4.  Read `rules.md`.
5.  Read `design.md`.
6.  Read `tasks.md`.
7.  Preserve existing architecture unless there is a documented reason
    to change it.
8.  Never invent scientific thresholds.
9.  Never let AI bypass safety logic.
10. Never expose device credentials to the frontend.
11. Update documentation when architecture changes.

------------------------------------------------------------------------

# 27. Project North Star

The project succeeds when a farmer can open SeriCare and immediately
understand:

> **"Is my silkworm environment safe, what is the system doing, and do I
> need to do anything?"**

The technology should stay behind the scenes as much as possible.

------------------------------------------------------------------------

# 28. One-Line Product Definition

> **SeriCare is a farmer-first IoT platform that senses, understands and
> automatically manages silkworm rearing environments while keeping the
> farmer informed and in control.**
