# SeriCare Mobile Application (Flutter)

A cross-platform native mobile application built with Flutter for silkworm farmers in the Mulbagal sericulture cluster.

## Architecture & Features Planned & Implemented:
1. **Screen 1: Language Selection & Onboarding (`lib/screens/onboarding_screen.dart`)**
   - Trilingual support: English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు).
2. **Screen 2: Home Dashboard (`lib/screens/home_screen.dart`)**
   - Simple, farmer-friendly statuses ("Ideal for Silkworms", "Too Warm", "Too Cool").
   - Live shed conditions, weather strip, and connected equipment status.
3. **Screen 3: Explainable AI Advisor (`lib/screens/ai_guidance_screen.dart`)**
   - Contextual explanation of automated actions ("Why cooling is ON", "What this means").
4. **Screen 4: Environment Overview (`lib/screens/environment_screen.dart`)**
   - Visual charts with custom painted shaded ideal comfort bands.
   - Toggle between Simple View and Detailed View; Time filters (Today, 7D, 30D).
5. **Screen 5: Growth Stage Guidance (`lib/screens/growth_stage_screen.dart`)**
   - Instars 1 to 5 selector with stage-specific environmental targets.
6. **Screen 6: Research & Insights (`lib/screens/insights_screen.dart`)**
   - Guides, research, Mulbagal microclimate tips, and 7-day stability bar chart.
7. **Advanced Modals (`lib/widgets/`)**
   - `advanced_mode_modal.dart`: Auto vs Manual mode, Temp setpoint stepper, Humidity setpoint stepper, and relay overrides with safety interlocks.
   - `detailed_metrics_modal.dart`: Exact sensor readings, outside weather, node connectivity.
   - `system_settings_modal.dart`: Notification switches, language selector, and CSV telemetry export.

## How to Run:
```bash
cd mobile
flutter pub get
flutter run
```
