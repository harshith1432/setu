# Setu Mobile Application (Flutter)

A cross-platform native mobile application built with Flutter for silkworm farmers worldwide.

## Architecture & Features:
1. **Screen 1: Language Selection & Onboarding (`lib/screens/onboarding_screen.dart`)**
   - Trilingual support: English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు) with dynamic switching.
2. **Screen 2: Home Dashboard (`lib/screens/home_screen.dart`)**
   - Clean, farmer-friendly statuses ("Ideal for Silkworms", "Too Warm", "Too Cool") with minimal text overhead.
   - Live shed conditions, dynamic regional weather strip, and connected equipment status.
3. **Screen 3: Explainable AI Advisor (`lib/screens/ai_guidance_screen.dart`)**
   - Contextual explanation of automated actions ("Why cooling is ON", "What this means").
4. **Screen 4: Environment Overview (`lib/screens/environment_screen.dart`)**
   - Visual charts with custom painted shaded ideal comfort bands.
   - Toggle between Simple View and Detailed View; Time filters (Today, 7D, 30D).
5. **Screen 5: Growth Stage Guidance (`lib/screens/growth_stage_screen.dart`)**
   - Instars 1 to 5 selector with stage-specific environmental targets.
6. **Screen 6: Research & Insights (`lib/screens/insights_screen.dart`)**
   - Guides, research, local microclimate tips, and 7-day stability bar chart.
7. **Advanced Modals & Location Settings (`lib/widgets/`)**
   - `system_settings_modal.dart`: On-demand phone GPS permission acquisition (`geolocator`), manual worldwide city/region search, language selection, and CSV telemetry export.
   - `user_profile_modal.dart`: Edit farmer profile, farm name, and custom rearing shed coordinates.
   - `advanced_mode_modal.dart`: Auto vs Manual mode, Temp setpoint stepper, Humidity setpoint stepper, and relay overrides with safety interlocks.
   - `detailed_metrics_modal.dart`: Exact sensor readings, outside weather, node connectivity.

## How to Run:
```bash
cd mobile
flutter pub get
flutter run
```

If the backend is running on the same machine:
- Android emulator: the app will try `10.0.2.2:8000` automatically.
- Desktop/web: the app will try `127.0.0.1:8000` automatically.
- Physical Android phone: open the in-app settings and enter your computer's LAN IP, for example `192.168.1.25:8000`.

## Build APK:
```bash
cd mobile
flutter build apk --release
```

Release APK output:
```bash
build/app/outputs/flutter-apk/app-release.apk
```
