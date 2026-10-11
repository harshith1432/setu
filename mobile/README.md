# Setu Mobile Application (Flutter)

A cross-platform native mobile application built with Flutter for silkworm farmers worldwide.

## Architecture & Features:
1. **Screen 0: Authentication & Google Sign-In (`lib/screens/auth_screen.dart`)**
   - Compact, scrollable card UI for Login and Registration.
   - Dual authentication options: direct username/password authentication and one-tap **Google Sign-In** (via Firebase Auth).
   - Automatic backend user sync (`/auth/google-sync`) to create or update profile data in PostgreSQL.
2. **Screen 1: Language Selection & Onboarding (`lib/screens/onboarding_screen.dart`)**
   - Trilingual support: English, Kannada (ಕನ್ನಡ), and Telugu (తెలుగు) with dynamic switching.
3. **Screen 2: Home Dashboard (`lib/screens/home_screen.dart`)**
   - Clean, farmer-friendly statuses ("Ideal for Silkworms", "Too Warm", "Too Cool") with minimal text overhead.
   - **4-Metric Real-Time Grid**:
     - **Temperature**: Current vs stage target range.
     - **Humidity**: Current RH% vs stage target range.
     - **Air Quality (CO₂)**: Indoor fresh air percentage; alerts when below safe threshold (`< 80%`).
     - **Light Intensity**: Real-time Lux reading and photoperiod phase (Day, Night Rest, Cocoon Spinning).
   - **Equipment Status Bar**: Live indicators for Evaporative Cooler, Exhaust Vent Fan, Heating Element, and **Dimmable Bulb (PWM %)**.
   - **Interactive Research Scenarios**: Quick simulation test buttons (Hot Noon 35°C, Cold Night 20°C, Stale Air Fan ON, Night Rest <5 Lux).
4. **Screen 3: Explainable AI Advisor (`lib/screens/ai_guidance_screen.dart`)**
   - Contextual explanation of automated actions ("Why cooling is ON", "Why exhaust fan is running for air quality").
5. **Screen 4: Environment Overview (`lib/screens/environment_screen.dart`)**
   - Visual charts with custom painted shaded ideal comfort bands for:
     - Temperature (°C)
     - Relative Humidity (% RH)
     - Air Quality (CO₂ concentration / fresh air %)
     - Light Intensity (Lux photoperiod)
   - Toggle between Simple View and Detailed View; Time filters (Today, 7D, 30D).
6. **Screen 5: Growth Stage Guidance (`lib/screens/growth_stage_screen.dart`)**
   - Instars 1 to 5 selector with stage-specific environmental targets.
7. **Screen 6: Research & Insights (`lib/screens/insights_screen.dart`)**
   - Research citations (SSRG 2020, IRJMETS 2024, IARJSET 2022), local microclimate tips, and 7-day stability bar chart.
8. **Advanced Modals & Location Settings (`lib/widgets/`)**
   - `advanced_mode_modal.dart`: Auto vs Manual mode, Temp & Humidity steppers, Air Quality target stepper, Light Lux target stepper, and **Bulb PWM Dimmer Slider (0–100%)** with quick presets (Dark 0%, Dim 25%, Active 40%, Full 100%).
   - `system_settings_modal.dart`: On-demand phone GPS permission acquisition (`geolocator`), manual worldwide city/region search, language selection, backend host configuration, and CSV telemetry export.
   - `user_profile_modal.dart`: Edit farmer profile, farm name, batch identifier, silkworm breed, and rearing shed coordinates.
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
