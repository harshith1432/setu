import math
from typing import Optional, Dict, Any, Tuple, List
from app.services.db_service import get_db_cursor

KNOWN_AREA_COORDINATES = {
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "ramanagara": (12.7209, 77.2799),
    "mandya": (12.5218, 76.8951),
    "mysuru": (12.2958, 76.6394),
    "mysore": (12.2958, 76.6394),
    "kolar": (13.1362, 78.1291),
    "tumakuru": (13.3422, 77.1017),
    "chikkaballapura": (13.4325, 77.7275),
}

# Sub-locality sample offsets in Bengaluru to ensure diverse technician geolocations
BENGALURU_LOCALITY_COORDINATES = [
    ("Indiranagar", 12.9784, 77.6408),
    ("Koramangala", 12.9352, 77.6245),
    ("Jayanagar", 12.9308, 77.5838),
    ("Whitefield", 12.9698, 77.7500),
    ("Electronic City", 12.8452, 77.6602),
    ("Hebbal", 13.0358, 77.5970),
    ("Peenya", 13.0285, 77.5197),
    ("Malleshwaram", 13.0031, 77.5643),
    ("HSR Layout", 12.9121, 77.6446),
    ("Yelahanka", 13.1007, 77.5963),
    ("Kengeri", 12.9177, 77.4838),
    ("Rajajinagar", 12.9982, 77.5530),
]

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(R * c, 2)


def normalize_area_name(area_str: Optional[str]) -> str:
    if not area_str:
        return "Bengaluru"
    clean = area_str.strip().title()
    if clean.lower() in ("bangalore", "bengaluru south", "bengaluru north", "bengaluru urban", "bengaluru rural"):
        return "Bengaluru"
    if clean.lower() == "mysore":
        return "Mysuru"
    return clean


def ensure_technicians_seeded_for_bengaluru():
    """
    Ensures Bengaluru has active installation technicians with assigned coordinates
    so that workload and proximity algorithms can operate smoothly.
    """
    with get_db_cursor(commit=True, dict_cursor=True) as cursor:
        cursor.execute("""
        SELECT COUNT(*) as count 
        FROM employees e 
        JOIN users u ON e.user_id = u.id 
        WHERE (e.role_code = 'technician' OR u.role = 'technician')
          AND (e.assigned_area ILIKE '%Bengaluru%' OR u.region ILIKE '%Bengaluru%')
          AND e.employment_status = 'ACTIVE'
        """)
        row = cursor.fetchone()
        count = row["count"] if row else 0

        # Update existing technicians without coordinates
        cursor.execute("""
        SELECT e.id as emp_id, u.id as user_id, u.username
        FROM employees e
        JOIN users u ON e.user_id = u.id
        WHERE (e.role_code = 'technician' OR u.role = 'technician')
        """)
        existing_techs = cursor.fetchall()
        for idx, t in enumerate(existing_techs):
            loc_idx = idx % len(BENGALURU_LOCALITY_COORDINATES)
            loc_name, lat, lon = BENGALURU_LOCALITY_COORDINATES[loc_idx]
            cursor.execute("""
            UPDATE employees 
            SET assigned_area = 'Bengaluru', latitude = %s, longitude = %s
            WHERE id = %s AND (latitude IS NULL OR assigned_area IS NULL OR assigned_area = '');
            """, (lat, lon, t["emp_id"]))
            cursor.execute("""
            UPDATE users 
            SET region = 'Bengaluru', latitude = %s, longitude = %s
            WHERE id = %s AND (latitude IS NULL OR region IS NULL OR region = '');
            """, (lat, lon, t["user_id"]))


def find_best_technician_for_installation(
    area: Optional[str] = "Bengaluru",
    target_lat: Optional[float] = None,
    target_lon: Optional[float] = None
) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Smart Workload & Proximity Dispatcher:
    1. Filters technicians serving the requested territory/area.
    2. Determines active workload (jobs currently pending or in progress).
    3. Selects technician with the minimum active workload.
    4. If multiple technicians share the same minimum workload (or all have 0 jobs),
       calculates geospatial Haversine distance and dispatches to the nearest technician.
    """
    norm_area = normalize_area_name(area)
    
    # Resolve target coordinate
    if target_lat is None or target_lon is None:
        target_lat, target_lon = KNOWN_AREA_COORDINATES.get(norm_area.lower(), (12.9716, 77.5946))

    with get_db_cursor(dict_cursor=True) as cursor:
        # Fetch active technicians in or covering this area
        cursor.execute("""
        SELECT u.id as user_id, u.username, u.full_name, u.phone, u.region as user_region,
               e.id as employee_id, e.employee_id as employee_code, e.designation,
               COALESCE(e.assigned_area, u.region, 'Bengaluru') as assigned_area,
               COALESCE(e.latitude, u.latitude, 12.9716) as latitude,
               COALESCE(e.longitude, u.longitude, 77.5946) as longitude,
               (
                   SELECT COUNT(*) 
                   FROM installation_jobs j 
                   WHERE j.technician_id = u.id AND j.status NOT IN ('COMPLETED', 'CANCELLED')
               ) as active_jobs
        FROM users u
        JOIN employees e ON e.user_id = u.id
        WHERE (e.role_code = 'technician' OR u.role = 'technician' OR e.designation ILIKE '%technician%' OR e.designation ILIKE '%installation%')
          AND e.employment_status = 'ACTIVE' 
          AND u.is_active = TRUE
          AND (
              e.assigned_area ILIKE %s 
              OR u.region ILIKE %s 
              OR e.assigned_area = 'All' 
              OR e.access_scope = 'GLOBAL'
          )
        ORDER BY active_jobs ASC, u.full_name ASC
        """, (f"%{norm_area}%", f"%{norm_area}%"))

        candidates = [dict(r) for r in cursor.fetchall()]

        # If no area-specific candidates, fallback to all active technicians
        if not candidates:
            cursor.execute("""
            SELECT u.id as user_id, u.username, u.full_name, u.phone, u.region as user_region,
                   e.id as employee_id, e.employee_id as employee_code, e.designation,
                   COALESCE(e.assigned_area, u.region, 'Bengaluru') as assigned_area,
                   COALESCE(e.latitude, u.latitude, 12.9716) as latitude,
                   COALESCE(e.longitude, u.longitude, 77.5946) as longitude,
                   (
                       SELECT COUNT(*) 
                       FROM installation_jobs j 
                       WHERE j.technician_id = u.id AND j.status NOT IN ('COMPLETED', 'CANCELLED')
                   ) as active_jobs
            FROM users u
            JOIN employees e ON e.user_id = u.id
            WHERE (e.role_code = 'technician' OR u.role = 'technician' OR e.designation ILIKE '%technician%' OR e.designation ILIKE '%installation%')
              AND e.employment_status = 'ACTIVE' 
              AND u.is_active = TRUE
            ORDER BY active_jobs ASC, u.full_name ASC
            """)
            candidates = [dict(r) for r in cursor.fetchall()]

    if not candidates:
        return None, f"No active technicians available for {norm_area} territory."

    # Step 1: Workload Check
    min_workload = min(c["active_jobs"] for c in candidates)
    least_loaded_candidates = [c for c in candidates if c["active_jobs"] == min_workload]

    # Step 2: Proximity Check among least-loaded candidates
    for c in least_loaded_candidates:
        c["distance_km"] = haversine_km(target_lat, target_lon, float(c["latitude"]), float(c["longitude"]))

    # Sort primarily by lowest distance
    least_loaded_candidates.sort(key=lambda x: x["distance_km"])
    best_candidate = least_loaded_candidates[0]

    assigned_reason = (
        f"Smart Dispatch in {norm_area}: Assigned to {best_candidate['full_name']} "
        f"(Workload: {min_workload} active jobs, Proximity: {best_candidate['distance_km']:.2f} km from site)"
    )

    return best_candidate, assigned_reason
