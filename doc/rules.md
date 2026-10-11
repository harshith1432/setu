# Setu --- Rules, Automation & Control Specification

## 1. Purpose

This document defines how Setu decides environmental status,
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

## 8.1 Air Quality & CO₂ Ventilation Automation

Silkworms consume high volumes of oxygen and respire carbon dioxide, especially in 4th and 5th instars. In crowded sheds, CO₂ concentration must remain strictly below 1% (< 1,000 ppm) or larval mortality and flacherie outbreaks rise rapidly (SSRG 2020 & IRJMETS 2024 research).

```text
Threshold:
- Safe Indoor Air Quality Target: >= 80% fresh air (CO₂ <= 1,000 ppm)
- Stale Air Threshold: < 80%

Control Logic:
IF indoor_air_quality < air_quality_target (e.g. < 80%):
    ventilation fan = ON (Active fresh air circulation)
    status = ATTENTION_REQUIRED ("Low air quality detected")

Recovery with Hysteresis (+4%):
IF ventilation fan is ON:
    Keep fan running until indoor_air_quality >= (air_quality_target + 4.0%) (e.g. >= 84%)
    Only then shut off fan or return to thermal-only regulation
```

------------------------------------------------------------------------

## 9. Research-Backed Photoperiod Lighting & Dimming Logic

Silkworms are sensitive to light variations and require regulated photoperiods for optimal feeding activity and cocoon spinning (SSRG 2020, GAU 2023, IARJSET 2022).

### 9.1 Circadian Photoperiod Regimes
1. **Daytime Feeding Phase (06:00 – 22:00)**:
   - Target Lux: **15 – 30 Lux** (optimal 20–25 Lux).
   - Dimming Bulb PWM: Modulates at **25% – 40%** duty cycle to maintain uniform illumination across all rearing trays without generating radiant heat.
2. **Nighttime Resting Phase (22:00 – 06:00)**:
   - Target Lux: **< 5 Lux** (Physiological darkness).
   - Dimming Bulb PWM: **0% (OFF)**.
3. **Late 5th Instar Spinning Stage (Cocooning on Mountages)**:
   - Target Lux: **~10 Lux** (Semi-darkness).
   - Dimming Bulb PWM: **15%**.
   - Bright light during spinning causes larvae to crowd together and spin unmarketable double/flimsy cocoons.

```text
Photoperiod Evaluation Algorithm:
IF current_hour in [06..21]:
    mode = "DAY"
    target_lux = 25.0
    IF ambient_lux < 15.0:
        light = ON, light_brightness = 35% (PWM)
    ELSE IF ambient_lux > 35.0:
        light = OFF, light_brightness = 0%
ELSE:
    mode = "NIGHT"
    target_lux = 0.0
    light = OFF, light_brightness = 0% (PWM)

IF stage == 5 AND days_in_stage >= 6 (Spinning):
    mode = "SPINNING"
    target_lux = 10.0
    light = ON, light_brightness = 15% (PWM)
```

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
