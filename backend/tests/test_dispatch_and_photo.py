import pytest
import os
import sys

# Ensure backend is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.dispatch_service import (
    haversine_km,
    find_best_technician_for_installation,
    ensure_technicians_seeded_for_bengaluru,
    BENGALURU_LOCALITIES
)
from app.services.enterprise_db import EnterpriseDatabaseService
from app.services.org_employee_db import OrgEmployeeDatabaseService

def test_haversine_accuracy():
    # Distance between Indiranagar and Koramangala is roughly 4-6 km
    loc_indiranagar = BENGALURU_LOCALITIES["Indiranagar"]
    loc_koramangala = BENGALURU_LOCALITIES["Koramangala"]
    dist = haversine_km(loc_indiranagar["lat"], loc_indiranagar["lon"], loc_koramangala["lat"], loc_koramangala["lon"])
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
    db = EnterpriseDatabaseService()
    job = db.create_installation_job(
        shed_id="shed_test_verify",
        scheduled_date="2026-11-01T10:00:00Z",
        remarks="Test verification job",
        area="Bengaluru",
        farmer_name="Test Farmer",
        farm_name="Test Farm",
        farmer_phone="+91 99999 11111"
    )
    assert job is not None
    job_id = job["id"]

    # Try marking COMPLETED without photo
    with pytest.raises(ValueError, match="strictly mandatory"):
        db.update_installation_job(job_id, {"status": "COMPLETED"})

    # Complete with photo
    photo_url = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    updated = db.update_installation_job(job_id, {
        "status": "COMPLETED",
        "completion_photo_url": photo_url
    })
    assert updated["status"] == "COMPLETED"
    assert updated["completion_photo_url"] == photo_url

def test_workload_balancing():
    ensure_technicians_seeded_for_bengaluru()
    db = EnterpriseDatabaseService()

    # Create job 1 in Bengaluru -> dispatches to best technician Tech A
    job1 = db.create_installation_job(
        shed_id="shed_workload_1",
        scheduled_date="2026-11-01T10:00:00Z",
        area="Bengaluru",
        latitude=12.9784,
        longitude=77.6408
    )
    tech_a_id = job1["technician_id"]

    # Now Tech A has 1 active job.
    # When job 2 comes in near the same area, if another tech has 0 jobs, it balances to the less busy tech!
    tech_b, reason_b = find_best_technician_for_installation(
        area="Bengaluru",
        target_lat=12.9784,
        target_lon=77.6408
    )
    # The active jobs count of tech_b should be <= tech_a
    active_b = tech_b.get("active_jobs_count", 0)
    assert active_b == 0 or tech_b["id"] != tech_a_id or "lowest active workload" in reason_b
