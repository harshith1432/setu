# SeriCare --- Rules, Automation & Control Specification

## 1. Purpose

This document defines how SeriCare decides environmental status,
generates recommendations and controls connected equipment.

The most important architectural rule is:

> **The deterministic rules and safety layer controls physical
> equipment. AI explains and enhances decisions but does not bypass
> safety constraints.**

------------------------------------------------------------------------

## 2. Rule Hierarchy

Rules should be evaluated in this order:

``` text
1. Hardware Safety
        ↓
2. Sensor Validity
        ↓
3. Emergency Conditions
        ↓
4. Growth-Stage Safety Range
        ↓
5. Farmer Configuration
        ↓
6. Automatic Control Logic
        ↓
7. Weather/Trend Intelligence
        ↓
8. AI Explanation
```

------------------------------------------------------------------------

## 3. Three Range Types

Each environmental parameter should have three conceptual ranges.

### 3.1 Safety Range

Absolute boundaries beyond which equipment must not operate or must
enter a safe state.

### 3.2 Preferred Range

The desired range for the current growth stage.

### 3.3 Warning Range

A range near the preferred limits where the system can warn or pre-act.

The actual numerical thresholds must be established from authoritative
sericulture guidance and validated experimentally. The software must not
hard-code arbitrary biological thresholds.

------------------------------------------------------------------------

## 4. Environmental Status

Possible temperature statuses:

``` text
IDEAL
SLIGHTLY_WARM
TOO_WARM
SLIGHTLY_COOL
TOO_COOL
UNKNOWN
```

Humidity:

``` text
IDEAL
LOW
HIGH
CRITICAL_LOW
CRITICAL_HIGH
UNKNOWN
```

Overall status:

``` text
IDEAL
ATTENTION_REQUIRED
ACTION_ACTIVE
CRITICAL
OFFLINE
UNKNOWN
```

------------------------------------------------------------------------

## 5. Hysteresis

Do not switch equipment on/off every time a reading crosses one
boundary.

Example:

``` text
Cooling ON threshold
       ↓
       28°C

Cooling OFF threshold
       ↓
       26.5°C
```

The gap prevents rapid cycling.

The actual values should be configurable per growth stage and validated
during field testing.

------------------------------------------------------------------------

## 6. Minimum Run Time

Equipment should not repeatedly start and stop within seconds.

The controller may use:

-   Minimum ON time
-   Minimum OFF time
-   Cooldown period
-   Maximum continuous runtime

These values depend on the actual hardware and should be configurable.

------------------------------------------------------------------------

## 7. Temperature Control Logic

Conceptual algorithm:

``` text
IF sensor invalid:
    do not perform normal automatic control
    enter safe state
    notify if necessary

ELSE IF critical safety condition:
    execute emergency rule

ELSE:
    determine current growth-stage preferred range

    IF temperature > preferred_high:
        cooling may be required

    IF temperature < preferred_low:
        heating may be required

    IF temperature within preferred range:
        maintain current safe state
```

Add hysteresis and minimum runtime constraints before changing actuator
state.

------------------------------------------------------------------------

## 8. Humidity Logic

Conceptual behavior:

``` text
IF humidity below preferred range:
    recommend humidity increase
    activate humidification if installed and safe

IF humidity above preferred range:
    recommend ventilation/dehumidification if available

IF humidity is acceptable:
    maintain
```

Do not activate incompatible actuators simultaneously without explicit
control logic.

------------------------------------------------------------------------

## 9. Light / Lighting Logic

Light conditions should be monitored separately from temperature and humidity. Where controllable lighting is installed, the rules engine may recommend or control it according to the current growth/rearing stage, configured operating schedule and validated biological requirements.

Conceptual behavior:

```text
IF light is below the configured acceptable condition:
    recommend or activate lighting if installed

IF light is above the configured acceptable condition:
    recommend reduction/shading if supported

IF light changes suddenly:
    evaluate whether farmer attention is required
```

The exact light intensity, duration and timing must not be invented in software; they should come from validated sericulture requirements.

## 10. Heating and Cooling Interlock

Heating and cooling should normally have a hardware/software interlock.

``` text
IF heating == ON:
    cooling == OFF

IF cooling == ON:
    heating == OFF
```

Unless the physical installation explicitly supports another safe
configuration.

------------------------------------------------------------------------

## 11. Auto Mode

In Auto Mode:

``` text
Read sensors
 ↓
Validate readings
 ↓
Read growth stage
 ↓
Load configured ranges
 ↓
Evaluate current condition
 ↓
Evaluate trend
 ↓
Evaluate device availability
 ↓
Apply safety rules
 ↓
Determine action
 ↓
Publish command
 ↓
Wait for acknowledgment
 ↓
Verify resulting state
```

------------------------------------------------------------------------

## 12. Manual Mode

Manual Mode allows experienced users to request actions.

However:

> Manual mode does not disable safety rules.

Example:

``` text
User requests heater ON
        ↓
Backend validation
        ↓
Safety check
        ↓
Allowed?
   /         \
 YES          NO
 ↓             ↓
MQTT         Reject
 ↓
Device
```

The application must explain rejected commands.

------------------------------------------------------------------------

## 12. Growth Stage Rules

Every stage should have configurable:

-   Preferred temperature range
-   Warning limits
-   Safety limits
-   Preferred humidity range
-   Warning limits
-   Ventilation guidance
-   Equipment preferences
-   Notification severity

Initial stages:

``` text
1st Instar
2nd Instar
3rd Instar
4th Instar
5th Instar
```

The stage configuration should live in the database/configuration layer,
not be scattered throughout application code.

------------------------------------------------------------------------

## 13. Trend Detection

The system should not only look at the current value.

It should also calculate:

-   Rate of change
-   Direction
-   Stability
-   Time outside preferred range

Example:

``` text
Current temperature = acceptable

BUT

Temperature has increased continuously
for the last several readings

→ issue early warning
```

This enables proactive control.

------------------------------------------------------------------------

## 14. Weather-Aware Rules

Weather should provide context.

Example:

``` text
Current indoor temperature = acceptable
Outside temperature = high
Indoor temperature trend = rising
Forecast = continued heat

→ prepare/anticipate cooling
```

The system should avoid unnecessary equipment activation if the
environment remains safe.

------------------------------------------------------------------------

## 15. Device Offline Rules

If the device stops reporting:

``` text
No telemetry
   ↓
Grace period
   ↓
Device marked STALE
   ↓
Notify user
```

Do not falsely show the last value as live.

The UI should show:

> Last updated 8 minutes ago

instead of pretending the reading is current.

------------------------------------------------------------------------

## 16. Command Lifecycle

Every command should have a state:

``` text
CREATED
VALIDATED
QUEUED
SENT
RECEIVED
EXECUTED
FAILED
EXPIRED
REJECTED
```

Example:

``` text
Farmer changes target
        ↓
CREATED
        ↓
VALIDATED
        ↓
SENT
        ↓
ESP32 ACK
        ↓
RECEIVED
        ↓
EXECUTED
```

------------------------------------------------------------------------

## 17. Command Timeout

If the device does not acknowledge a command within a configured
timeout:

``` text
Command SENT
     ↓
No ACK
     ↓
Retry policy
     ↓
Still no ACK
     ↓
Command FAILED
     ↓
Notify farmer
```

The retry policy must avoid repeatedly issuing dangerous commands.

------------------------------------------------------------------------

## 18. Sensor Validation

Reject or flag readings that are:

-   Missing
-   Non-numeric
-   Outside physically plausible sensor limits
-   Unchanged for an abnormal period
-   Timestamp-invalid
-   Duplicated
-   Corrupted

Sensor failure should never cause the controller to assume a dangerous
value.

------------------------------------------------------------------------

## 19. AI Rules

AI may:

-   Explain
-   Summarize
-   Recommend
-   Predict
-   Answer questions

AI must not:

-   Directly bypass safety limits
-   Issue arbitrary hardware commands
-   Override device safety
-   Invent sensor readings
-   Claim an action happened without confirmation

Example:

**Good**

> Temperature is above the preferred range for the current stage.
> Cooling has been activated by the control system.

**Bad**

> I think the temperature should be 20°C, so I turned the heater off.

------------------------------------------------------------------------

## 20. Alert Deduplication

Do not send repeated alerts every few seconds.

Use:

-   Alert state
-   Cooldown
-   Recovery event

Example:

``` text
Temperature high
      ↓
Send ONE alert
      ↓
Keep monitoring
      ↓
Temperature returns to normal
      ↓
Send recovery notification
```

------------------------------------------------------------------------

## 21. Recovery Rules

Every significant warning should ideally have a recovery event.

Example:

> ⚠️ Temperature too high. Cooling activated.

Later:

> ✅ Temperature has returned to the preferred range.

------------------------------------------------------------------------

## 22. Farmer-Friendly Messages

Avoid:

> `TEMP_HIGH_THRESHOLD_EXCEEDED`

Use:

> **Temperature is getting high. Cooling has been activated.**

Avoid:

> `HUMIDITY < X`

Use:

> **Humidity is lower than recommended for the current growth stage.**

------------------------------------------------------------------------

## 23. Safety Principle

If there is uncertainty:

``` text
Sensor failure
+
Communication failure
+
Invalid command
+
Conflicting control request
        ↓
Do not perform unsafe action
        ↓
Use local safe behavior
        ↓
Notify when appropriate
```

------------------------------------------------------------------------

## 24. Rule Configuration

Rules should eventually be configurable through an administrative
interface.

Avoid hard-coding values in:

-   Flask routes
-   JavaScript
-   ESP32 firmware
-   AI prompts

Instead use versioned configuration.

------------------------------------------------------------------------

## 25. Rule Versioning

Each configuration should have:

``` text
rule_set_id
growth_stage
version
effective_from
created_by
approved_by
```

This makes field testing and future scientific updates traceable.

------------------------------------------------------------------------

## 26. Rule Testing

Every rule must have tests for:

-   Lower boundary
-   Upper boundary
-   Exactly at boundary
-   Hysteresis boundary
-   Sensor failure
-   Device offline
-   Manual override
-   Growth-stage change
-   Conflicting actions
-   Command timeout
-   Recovery

------------------------------------------------------------------------

## 27. Final Control Principle

The control chain is:

``` text
DATA
 ↓
VALIDATION
 ↓
SAFETY
 ↓
GROWTH-STAGE RULES
 ↓
AUTOMATION
 ↓
DEVICE COMMAND
 ↓
DEVICE SAFETY
 ↓
ACTUATOR
 ↓
VERIFY
 ↓
RECORD
```

This chain must remain deterministic and auditable.
