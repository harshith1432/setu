import pytest
import os
import sys

# Ensure backend is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.dispatch_service import (
    haversine_km,
    find_best_technician_for_installation,
    ensure_technicians_seeded_for_bengaluru,
    BENGALURU_LOCALITY_COORDINATES
)
from app.services.enterprise_db import create_installation_job, update_installation_job

def get_test_farmer_id():
    from app.services.db_service import get_db_cursor
    with get_db_cursor(dict_cursor=True) as cur:
        cur.execute("SELECT id FROM users WHERE role = 'farmer' ORDER BY id ASC LIMIT 1;")
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1;")
        row = cur.fetchone()
        return row["id"] if row else "usr_admin"


def test_haversine_accuracy():
    # Distance between Indiranagar and Koramangala is roughly 4-6 km
    loc_indiranagar = (12.9784, 77.6408)
    loc_koramangala = (12.9352, 77.6245)
    dist = haversine_km(loc_indiranagar[0], loc_indiranagar[1], loc_koramangala[0], loc_koramangala[1])
    assert 3.0 < dist < 8.0, f"Expected distance between 3 and 8 km, got {dist}"

def test_dispatch_proximity_when_workload_tied():
    ensure_technicians_seeded_for_bengaluru()
    
    # Target location in Indiranagar
    target_lat = 12.9784
    target_lon = 77.6408
    
    tech, reason = find_best_technician_for_installation(
        area="Bengaluru",
        target_lat=target_lat,
        target_lon=target_lon
    )
    assert tech is not None, "Technician should be dispatched"
    assert "Bengaluru" in reason
    print(f"Dispatched technician: {tech['full_name']}, reason: {reason}")

def test_job_completion_mandates_photo():
    # Test creating a job and attempting completion without photo
    job = create_installation_job({
        "shed_id": "shed_test_verify",
        "farmer_id": get_test_farmer_id(),
        "scheduled_date": "2026-11-01T10:00:00Z",
        "remarks": "Test verification job",
        "area": "Bengaluru",
        "farmer_name": "Ramesh Kumar",
        "farm_name": "Setu Smart Farm",
        "farmer_phone": "+91 99999 11111"
    })
    assert job is not None
    job_id = job["id"]

    # Try marking COMPLETED without photo -> MUST raise ValueError
    with pytest.raises(ValueError, match="strictly mandatory"):
        update_installation_job(
            job_id=job_id,
            new_status="COMPLETED",
            actor_id="admin",
            remarks="Trying to complete without photo proof"
        )

    # Complete with valid photo proof
    photo_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    updated = update_installation_job(
        job_id=job_id,
        new_status="COMPLETED",
        actor_id="admin",
        remarks="Hardware installed and verified with photo proof",
        completion_photo_url=photo_url
    )
    assert updated["status"] == "COMPLETED"
    assert updated["completion_photo_url"] == photo_url

def test_workload_balancing():
    ensure_technicians_seeded_for_bengaluru()

    # Create job 1 in Bengaluru -> dispatches to best technician
    job1 = create_installation_job({
        "shed_id": "shed_workload_1",
        "farmer_id": get_test_farmer_id(),
        "scheduled_date": "2026-11-01T10:00:00Z",
        "area": "Bengaluru",
        "latitude": 12.9784,
        "longitude": 77.6408
    })
    assert job1 is not None

    # Query next best technician
    tech_b, reason_b = find_best_technician_for_installation(
        area="Bengaluru",
        target_lat=12.9784,
        target_lon=77.6408
    )
    assert tech_b is not None
    assert "Bengaluru" in reason_b
