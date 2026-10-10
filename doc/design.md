# Setu --- UI/UX and Product Design Specification

## 1. Design Philosophy

Setu is designed for farmers first, not engineers.

The interface should answer three questions immediately:

1.  **Is the environment okay?**
2.  **If not, what is happening?**
3.  **What should I do?**

The application should minimize technical language and emphasize visual
status, clear actions and simple explanations.

------------------------------------------------------------------------

## 2. Design Principles

### Principle 1 --- Status before numbers

Show:

> 🟢 Ideal for Silkworms

before:

> 26.8°C / 74%

Numbers remain available in Advanced Mode.

### Principle 2 --- One primary action

Every alert should have an obvious next step.

### Principle 3 --- Explain automation

Whenever the system turns equipment on/off, show why.

### Principle 4 --- Large touch targets

The app must be usable on low-end phones and by users who may not be
comfortable with small UI controls.

### Principle 5 --- Local language first

English, Kannada and Telugu must be treated as first-class languages.

------------------------------------------------------------------------

## 3. Visual Direction

Suggested style:

-   Clean
-   Agricultural
-   Calm
-   Trustworthy
-   High readability
-   White/light backgrounds
-   Green as a semantic positive/environment color
-   Red/orange only for warnings
-   Blue can be used sparingly for information/technology
-   Avoid excessive gradients
-   Avoid dense dashboards

Typography:

-   Inter
-   Plus Jakarta Sans
-   Or a suitable multilingual font stack for Kannada/Telugu

------------------------------------------------------------------------

## 4. Main Navigation

Suggested bottom navigation:

``` text
Home | Environment | Growth | Insights | Settings
```

AI Assistant can be accessible from Home and Environment rather than
necessarily occupying a permanent tab.

------------------------------------------------------------------------

## 5. Screen 1 --- Language & Onboarding

Purpose:

-   Select language
-   Explain the product
-   Establish trust

Layout:

``` text
        Setu
 Healthy Silkworms
  Happier Farmers

       [Visual]

Select Language

🇬🇧 English        >
ಕನ್ನಡ              >
తెలుగు              >

          Continue
```

Keep onboarding short.

------------------------------------------------------------------------

## 6. Screen 2 --- Home Dashboard

The most important screen.

Recommended layout:

``` text
┌─────────────────────────────┐
│ Setu              🔔    │
│                             │
│ 🟢 Ideal for Silkworms      │
│                             │
│ Everything is normal        │
│                             │
│        🌡 26.8°C            │
│        Temperature          │
│                             │
│        💧 74%               │
│        Humidity             │
│                             │
│  3rd Instar • Days 6–9      │
│                             │
│ ❄️ Cooling OFF              │
│                             │
│ [ View Details → ]          │
└─────────────────────────────┘
```

------------------------------------------------------------------------

## 7. Home Status States

### Ideal

``` text
🟢 Ideal for Silkworms
Everything is normal.
```

### Too Warm

``` text
🟠 Temperature is High
Cooling is active.
```

### Too Cool

``` text
🔵 Temperature is Low
Heating is active.
```

### Attention

``` text
🟡 Attention Required
Humidity is lower than recommended.
```

### Offline

``` text
⚫ Device Offline
Last update: 8 minutes ago
```

Do not show an old reading as though it were current.

------------------------------------------------------------------------

## 8. Screen 3 --- AI Assistant

The AI Assistant should be conversational but action-oriented.

Example:

``` text
AI Assistant

Outside temperature is high today.
Cooling is active to maintain a suitable
environment for the current growth stage.

Current Action

❄️ Cooling ON

Why?

• Shed temperature is rising
• Current stage requires stable conditions
• Outside temperature is high
```

The AI should avoid overwhelming the farmer with technical explanations.

------------------------------------------------------------------------

## 9. Screen 4 --- Environment Overview

Two modes:

### Simple View

-   Temperature status
-   Humidity status
-   Trend
-   Active equipment
-   Time range

### Detailed View

-   Exact temperature
-   Exact humidity
-   Outside temperature
-   Outside humidity
-   Device state
-   System state

Time filters:

-   Today
-   7 Days
-   30 Days

------------------------------------------------------------------------

## 10. Graph Design

Graphs should prioritize interpretation.

Use:

-   Simple line charts
-   Clearly marked preferred range
-   Warning areas
-   Tooltips for exact values
-   Minimal gridlines

Example concept:

``` text
Temperature

Too Hot  ─────────────────
              ╱╲
Ideal    ────╱──╲─────────
          ╱
Too Cool ─────────────────

       6A  12P  6P  12A
```

The user should be able to understand the chart without knowing
statistics.

------------------------------------------------------------------------

## 11. Screen 5 --- Growth Stage

Show current stage prominently:

``` text
1st → 2nd → [3rd] → 4th → 5th

             3rd Instar
             Days 6–9

Ideal conditions

• Moderate temperature
• Stable humidity
• Proper ventilation
• Avoid sudden changes
```

Show an AI recommendation below.

------------------------------------------------------------------------

## 12. Screen 6 --- Manual / Advanced Mode

Advanced Mode should be intentionally separate from the simple farmer
dashboard.

Example:

``` text
Advanced Mode

Auto Mode     ●
Manual Mode   ○

Temperature Set Point
        −    26.0°C    +

Humidity Set Point
        −     75%     +

Cooling       ON
Heating       OFF
Fan           AUTO
```

Safety restrictions must still apply.

------------------------------------------------------------------------

## 13. Screen 7 --- Device Status

Show:

-   Online/offline
-   Last seen
-   Firmware version
-   Sensor health
-   Wi-Fi/network state
-   MQTT state
-   Actuator state

Example:

``` text
Shed 01

🟢 Online

Temperature Sensor     ✓
Humidity Sensor        ✓
Cooling Relay          ✓
Heating Relay          ✓

Last updated
10:32:15 AM
```

------------------------------------------------------------------------

## 14. Screen 8 --- Notifications

Use clear action-oriented messages.

Example:

> 🌡 Temperature is rising\
> Cooling has been activated automatically.

> 💧 Humidity is getting low\
> Check ventilation and humidity equipment.

> 📡 Device connection lost\
> The system is using its local safety settings.

------------------------------------------------------------------------

## 15. Screen 9 --- History & Insights

Show:

-   Average temperature
-   Average humidity
-   Time in preferred range
-   Cooling activity
-   Heating activity
-   Alerts
-   Environmental stability

Example:

``` text
This Week

Temperature
████████████  92% in preferred range

Humidity
███████████   86% in preferred range

Cooling
3h 24m

Alerts
4
```

Avoid turning this into an enterprise analytics dashboard.

------------------------------------------------------------------------

## 16. Screen 10 --- Research & Learning

Sections:

-   Best Practices
-   Environmental Management
-   Common Problems & Solutions
-   Research Insights
-   Region-Specific Insights

Content should be educational and distinguish expert/validated guidance
from AI-generated suggestions.

------------------------------------------------------------------------

## 17. Settings

Settings should contain:

-   Notifications
-   Preferred ranges
-   Language
-   Data download
-   Farm/shed
-   Device management
-   Auto/manual preferences
-   Account
-   About

------------------------------------------------------------------------

## 18. Responsive Design

The app should work well on:

-   Mobile phones
-   Tablets
-   Desktop web if a web interface is used

Mobile is the primary experience.

------------------------------------------------------------------------

## 19. Accessibility

Requirements:

-   Large touch targets
-   Strong text contrast
-   Icons accompanied by text
-   Do not rely only on color
-   Readable font sizes
-   Clear error messages
-   Local-language support
-   Screen-reader-friendly labels where applicable

Example:

Do not communicate only:

> 🔴

Use:

> 🔴 Temperature Too High

------------------------------------------------------------------------

## 20. Interaction Feedback

Every remote control action should show state.

Example:

``` text
Turning cooling ON...
       ↓
Command sent
       ↓
Cooling ON ✓
```

If the device does not respond:

``` text
Cooling command could not be confirmed.

Device may be offline.
```

Never show a successful state merely because the API request was
accepted.

------------------------------------------------------------------------

## 21. Design System

Create reusable components:

``` text
StatusCard
SensorCard
GrowthStageCard
RecommendationCard
DeviceStatusCard
ControlCard
ChartCard
NotificationCard
ActionButton
MetricChip
BottomNavigation
LanguageSelector
```

This keeps the application visually consistent.

------------------------------------------------------------------------

## 22. Design Goal

The ideal user experience is:

> **Open the app → understand the situation in 3 seconds → know what the
> system is doing → take action only if necessary.**
