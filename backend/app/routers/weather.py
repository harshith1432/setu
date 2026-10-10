from fastapi import APIRouter, Query
from typing import Optional, Dict, Any
from app.services.weather_service import weather_service

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("/current")
def get_current_weather(
    lat: Optional[float] = Query(None, description="Latitude from client GPS/geolocation"),
    lon: Optional[float] = Query(None, description="Longitude from client GPS/geolocation"),
    region: Optional[str] = Query(None, description="Region name or city")
) -> Dict[str, Any]:
    """
    Fetch live ambient temperature, humidity, wind, and conditions
    from internet based on client geolocation coordinates or region.
    """
    return weather_service.get_current_weather(lat=lat, lon=lon, region=region)
