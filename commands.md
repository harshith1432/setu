#TEST
source .venv/bin/activate
pytest backend/tests -v


##Run backend
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload


#Run
cd /home/nihal-ubuntu/Desktop/Development/Seva First Innovation/setu/mobile
flutter pub get
flutter run

#Build 
flutter build apk --release
