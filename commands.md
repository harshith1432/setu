#TEST
source .venv/bin/activate
pytest backend/tests -v


##Run backend
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload


##Firebase Android setup
# Put your Firebase Android config here before flutter run:
# mobile/android/app/google-services.json
# In Firebase console also keep Phone auth enabled and add SHA-1/SHA-256 for the Android app.


#Run
cd /home/nihal-ubuntu/Desktop/Development/Seva First Innovation/setu/mobile
flutter pub get
flutter run

#Build 
flutter build apk --release


#
flutter clean
flutter pub get
flutter run -d linux


#
flutter devices
flutter run -d <android-device-id>