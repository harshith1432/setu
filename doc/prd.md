# SeriCare --- Product Requirements Document (PRD)

**Project:** SeriCare -- Smart IoT Sericulture Environment Management &
Automated Control System\
**Initial Region:** Mulbagal, Karnataka, India\
**Initial Languages:** English, Kannada, Telugu\
**Primary Users:** Silkworm farmers / rearing-house operators\
**Document Status:** Product definition for MVP and future expansion

------------------------------------------------------------------------

## 1. Product Overview

SeriCare is an IoT-enabled sericulture management platform designed to
help silkworm farmers maintain suitable environmental conditions inside
rearing sheds.

The system combines:

-   Temperature and humidity sensors
-   IoT hardware such as ESP32
-   Heating, cooling, ventilation and other controllable equipment
-   MQTT-based device communication
-   A backend API and database
-   Growth-stage-specific environmental rules
-   Weather-aware intelligence
-   Explainable AI recommendations
-   Mobile/web access for farmers
-   Automatic and manual control
-   Notifications and historical insights

The central product principle is:

> **The farmer should not have to interpret technical sensor data.
> SeriCare should interpret the environment and tell the farmer what is
> happening, why it matters, and what action is being taken.**

------------------------------------------------------------------------

## 2. Problem Statement

Silkworm development is strongly affected by the rearing environment.
Farmers may need to continuously monitor temperature, humidity and
ventilation, while recommended conditions can vary by growth stage.

Traditional approaches create several problems:

1.  Farmers may rely on manual measurement.
2.  Raw sensor values do not immediately explain whether conditions are
    suitable.
3.  Environmental conditions can change quickly.
4.  Farmers may not be present inside the shed all the time.
5.  Manual switching of fans, coolers or heaters can be delayed.
6.  The correct range changes with the silkworm growth stage.
7.  Weather outside the shed can influence indoor conditions.
8.  Existing IoT dashboards can expose too many technical numbers
    without giving actionable guidance.

SeriCare addresses these problems by combining sensing, rules,
automation, remote control, notifications and explainable intelligence.

------------------------------------------------------------------------

## 3. Product Vision

Create a farmer-friendly system that can:

**Sense → Understand → Decide → Control → Explain → Learn**

The system should continuously understand the rearing environment and
help maintain suitable conditions while keeping the farmer in control.

------------------------------------------------------------------------

## 4. Goals

### Primary Goals

-   Monitor temperature and humidity in real time.
-   Display conditions using simple statuses such as:
    -   Ideal for Silkworms
    -   Too Warm
    -   Too Cool
    -   Humidity Too High
    -   Humidity Too Low
-   Automatically control connected environmental equipment.
-   Allow the farmer to control equipment remotely from a phone.
-   Adapt recommendations according to silkworm growth stage.
-   Consider outside weather when making decisions.
-   Explain why an action was taken.
-   Notify the farmer about important changes.
-   Maintain historical records.
-   Provide simple daily/weekly/monthly insights.
-   Support English, Kannada and Telugu.

### Secondary Goals

-   Support multiple farms and sheds.
-   Support multiple IoT devices.
-   Provide advanced technical readings.
-   Allow CSV data export.
-   Provide research and educational content.
-   Support future predictive models.

------------------------------------------------------------------------

## 5. Non-Goals for the First MVP

The first release should not attempt to solve everything.

The MVP does not need:

-   Full farm accounting
-   Marketplace functionality
-   Crop sales management
-   Financial management
-   Complex computer vision
-   Fully autonomous AI control without safety rules
-   Large-scale multi-country deployment
-   Advanced research analytics for every possible sericulture variable

These can be considered later.

------------------------------------------------------------------------

## 6. Target Users

### 6.1 Primary User --- Farmer

Needs:

-   Very simple interface
-   Current status
-   Clear recommendations
-   Remote control
-   Notifications
-   Local language
-   Confidence that the system is working

### 6.2 Advanced User

May be:

-   Experienced farmer
-   Farm supervisor
-   Technical operator

Needs:

-   Exact sensor values
-   Set points
-   Device status
-   Manual controls
-   Historical data
-   Configuration

### 6.3 Administrator

Needs:

-   User management
-   Farm/shed management
-   Device registration
-   Device health
-   Configuration
-   Logs
-   Data export
-   System monitoring

------------------------------------------------------------------------

## 7. Core User Journey

### Onboarding

1.  Install/open SeriCare.
2.  Select language.
3.  Create/login to account.
4.  Add farm.
5.  Add rearing shed.
6.  Pair/register IoT device.
7.  Select current silkworm growth stage.
8.  Review recommended settings.
9.  Enable Auto Mode if desired.

### Daily Usage

1.  Farmer opens dashboard.
2.  Sees overall environment status.
3.  Sees current growth stage.
4.  Sees temperature and humidity status.
5.  Sees active equipment.
6.  Reads recommendation if action is needed.
7.  Changes settings manually when permitted.
8.  Receives alerts when important events occur.

------------------------------------------------------------------------

## 8. Functional Requirements

### FR-01 Language Selection

The application must support:

-   English
-   Kannada
-   Telugu

Translations must be centralized so new languages can be added later.

### FR-02 Dashboard

The dashboard must show:

-   Overall environmental status
-   Temperature status
-   Humidity status
-   Current growth stage
-   Current action
-   Device connectivity
-   Last update time
-   Active heating/cooling state

### FR-03 Real-Time Monitoring

The system must receive sensor data from IoT devices and make recent
readings available to the application.

Target behavior:

-   Near real-time updates while connected
-   Clear last-updated timestamp
-   Offline/stale indication when data stops arriving

### FR-04 Remote Control

A farmer must be able to change supported controls from the phone.

Examples:

-   Temperature set point
-   Auto/manual mode
-   Cooling
-   Heating
-   Fan/ventilation
-   Humidity-related equipment where installed

Every command must be validated before being sent to hardware.

### FR-05 Automatic Control

In Auto Mode, the system must evaluate:

-   Current indoor temperature
-   Current indoor humidity
-   Growth stage
-   Configured safe ranges
-   Rate of environmental change
-   Outside weather where available
-   Device availability

The rules engine determines whether a control action is required.

### FR-06 Explainable Recommendations

Whenever the system recommends or performs an important action, the
application should explain:

-   What happened
-   Why it happened
-   What action was taken
-   Whether the farmer needs to do anything

Example:

> Cooling activated because the shed temperature exceeded the
> recommended range for the current growth stage.

### FR-07 Notifications

Examples:

-   Temperature is rising.
-   Cooling activated.
-   Temperature is now suitable.
-   Humidity is getting low.
-   Device connection lost.
-   Sensor data has not been received.
-   Manual control changed the automatic setting.
-   Critical safety condition detected.

### FR-08 Growth Stage

The system must support stage-specific configuration.

Initial stages:

1.  1st Instar
2.  2nd Instar
3.  3rd Instar
4.  4th Instar
5.  5th Instar

The architecture must allow additional stages or rearing phases later.

### FR-09 Weather Awareness

The system may use:

-   Outside temperature
-   Outside humidity
-   Weather forecast
-   Weather trend

Weather should influence anticipation and recommendations, not bypass
safety rules.

### FR-10 History

Store:

-   Sensor readings
-   Device status
-   Commands
-   Control events
-   Alerts
-   Growth-stage changes
-   User actions

### FR-11 Insights

Provide simple:

-   Daily trends
-   Weekly trends
-   Monthly trends
-   Time spent outside preferred range
-   Equipment activity
-   Environmental stability

### FR-12 Advanced Mode

Advanced Mode should expose:

-   Exact values
-   Set points
-   Device state
-   Manual controls
-   System status
-   Data download
-   Configuration

------------------------------------------------------------------------

## 9. IoT Requirements

The IoT system is a core part of SeriCare.

### Device Responsibilities

The IoT device should:

-   Read sensors
-   Publish readings
-   Receive commands
-   Control connected equipment
-   Report device state
-   Report errors
-   Maintain local safety behavior
-   Reconnect after network interruption

### Backend Responsibilities

The backend should:

-   Authenticate devices
-   Receive telemetry
-   Validate commands
-   Publish commands
-   Record commands and results
-   Detect stale devices
-   Synchronize state
-   Apply automation rules
-   Provide data to the application

### Communication

MQTT is the preferred communication protocol between the backend/device
layer because it is lightweight and well suited for bidirectional IoT
messaging.

------------------------------------------------------------------------

## 10. Reliability Requirements

The system must not assume that the internet is always available.

If cloud connectivity fails:

-   The device should retain safe operating settings.
-   Local safety controls should continue.
-   The device should attempt reconnection.
-   Data should be synchronized when connectivity returns.

The device should never depend exclusively on AI or a cloud connection
for basic safety.

------------------------------------------------------------------------

## 11. Security Requirements

-   Authenticated users
-   Device authentication
-   Authorization by farm/shed/device
-   TLS for network communication
-   Secure MQTT credentials
-   No hard-coded secrets in firmware
-   Audit logging of control actions
-   Input validation
-   Rate limiting for APIs
-   Secure session/token handling
-   Safe command validation
-   Firmware update strategy for production devices

------------------------------------------------------------------------

## 12. Success Metrics

Initial MVP metrics:

-   Sensor data successfully received
-   Device command delivery success rate
-   Device online availability
-   Time between sensor event and dashboard update
-   Control command response time
-   Number of false alerts
-   Percentage of time conditions remain within configured ranges
-   Farmer task completion without technical assistance
-   Notification delivery success

------------------------------------------------------------------------

## 13. Future Expansion

Potential future capabilities:

-   Multiple sheds per farm
-   Multiple farms per user
-   Predictive environmental control
-   Advanced weather forecasting
-   Energy optimization
-   Disease-risk alerts
-   Computer vision for silkworm/cocoon monitoring
-   Voice assistant in local languages
-   Research dashboards
-   Expert consultation
-   Firmware management
-   OTA device updates

------------------------------------------------------------------------

## 14. MVP Definition

The MVP is complete when a farmer can:

1.  Log in.
2.  Select a language.
3.  Register a farm and shed.
4.  Connect an IoT device.
5.  See live temperature and humidity.
6.  See a simple environmental status.
7.  Select the silkworm growth stage.
8.  Enable Auto Mode.
9.  See automatic control happen.
10. Change settings from a phone.
11. Receive important notifications.
12. View basic historical trends.
13. Understand why the system took an action.
14. Continue safe local operation during temporary internet loss.

------------------------------------------------------------------------

## 15. Product Principle

SeriCare should always prioritize:

**Simple for the farmer.\
Safe for the silkworms.\
Reliable for the hardware.\
Explainable for the user.\
Scalable for future farms.**
