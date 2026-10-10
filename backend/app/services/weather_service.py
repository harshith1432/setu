import urllib.request
import urllib.parse
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Weather code descriptions from WMO Weather interpretation codes
WMO_WEATHER_MAP = {
    0: ("Clear sky", "Sunny & clear conditions. Optimal light levels."),
    1: ("Mainly clear", "Favorable ambient daylight with minimal clouding."),
    2: ("Partly cloudy", "Mild cloud cover. Steady ambient temperature."),
    3: ("Overcast", "Full cloud coverage. Low solar radiation."),
    45: ("Foggy", "Foggy conditions. High external humidity."),
    48: ("Depositing rime fog", "Persistent moisture fog. Moderate air flow."),
    51: ("Light drizzle", "Light precipitation outside. Humid surroundings."),
    53: ("Moderate drizzle", "Moist air with continuous light precipitation."),
    55: ("Dense drizzle", "Dense precipitation outside. High ambient moisture."),
    61: ("Slight rain", "Passing showers outside. Temperature cooling."),
    63: ("Moderate rain", "Moderate rainfall. Cool outside air."),
    65: ("Heavy rain", "Heavy rain storm. Exterior humidity saturated."),
    71: ("Slight snow", "Cold exterior temperatures. Keep heating monitored."),
    73: ("Moderate snow", "Cold exterior temperatures. Keep heating monitored."),
    75: ("Heavy snow", "Heavy snow and freezing air outside."),
    80: ("Slight rain showers", "Passing rain showers. Brief cool down."),
    81: ("Moderate rain showers", "Moderate showers outside."),
    82: ("Violent rain showers", "Intense storm showers."),
    95: ("Thunderstorm", "Thunderstorm active outside. Secure shed openings."),
    96: ("Thunderstorm with slight hail", "Severe weather with hail."),
    99: ("Thunderstorm with heavy hail", "Severe storm with hail.")
}

class WeatherService:
    def __init__(self, default_region: str = "Mulbagal, Kolar, Karnataka"):
        self.default_region = default_region

    def geocode_region(self, region_name: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes any global region name, city, district, or address using Open-Meteo's geocoding API.
        """
        if not region_name or not region_name.strip():
            return None
            
        clean_name = region_name.split(',')[0].strip()
        if not clean_name:
            clean_name = region_name.strip()

        try:
            encoded = urllib.parse.quote(clean_name)
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded}&count=1&language=en&format=json"
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Setu-Global/1.0"})
            with urllib.request.urlopen(req, timeout=4) as res:
                data = json.loads(res.read().decode())
                results = data.get("results", [])
                if results:
                    best = results[0]
                    name = best.get("name", clean_name)
                    admin1 = best.get("admin1", "")
                    country = best.get("country", "")
                    label_parts = [p for p in [name, admin1, country] if p]
                    formatted_region = ", ".join(label_parts)
                    return {
                        "latitude": float(best["latitude"]),
                        "longitude": float(best["longitude"]),
                        "formatted_region": formatted_region
                    }
        except Exception as e:
            logger.warning(f"Geocoding failed for '{region_name}': {e}")
        return None

    def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches live real-time weather from Open-Meteo for any latitude/longitude or region name anywhere in the world.
        """
        display_region = region.strip() if region and region.strip() else self.default_region
        latitude = lat
        longitude = lon

        # If lat/lon not provided, resolve via geocoding
        if latitude is None or longitude is None:
            if display_region:
                geo = self.geocode_region(display_region)
                if geo:
                    latitude = geo["latitude"]
                    longitude = geo["longitude"]
                    if not region:
                        display_region = geo["formatted_region"]

        # Default fallback coordinates (Mulbagal) only if resolution completely fails
        if latitude is None or longitude is None:
            latitude = 13.1633
            longitude = 78.3944

        try:
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}&longitude={longitude}&"
                f"current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            )
            req = urllib.request.Request(weather_url, headers={"User-Agent": "Setu-Global/1.0"})
            with urllib.request.urlopen(req, timeout=4) as res:
                payload = json.loads(res.read().decode())
                current = payload.get("current", {})
                
                temp = float(current.get("temperature_2m", 28.5))
                hum = float(current.get("relative_humidity_2m", 55.0))
                wind = float(current.get("wind_speed_10m", 12.0))
                code = int(current.get("weather_code", 0))

                condition, trend = WMO_WEATHER_MAP.get(code, ("Normal", "Ambient conditions steady."))
                if temp > 33.0:
                    trend = f"High outdoor heat ({temp}°C). Cooling system active to safeguard worms."
                elif temp < 20.0:
                    trend = f"Low outdoor temperature ({temp}°C). Thermal heating recommended."

                return {
                    "region": display_region,
                    "latitude": latitude,
                    "longitude": longitude,
                    "outside_temperature": round(temp, 1),
                    "outside_humidity": round(hum, 1),
                    "condition": condition,
                    "forecast_trend": trend,
                    "wind_speed_kmh": round(wind, 1),
                    "is_live": True
                }
        except Exception as e:
            logger.warning(f"Live Open-Meteo query failed for lat={latitude}, lon={longitude}: {e}")
            # Fallback graceful simulation if offline
            return {
                "region": display_region,
                "latitude": latitude,
                "longitude": longitude,
                "outside_temperature": 28.5,
                "outside_humidity": 55.0,
                "condition": "Clear Sky",
                "forecast_trend": "Ambient conditions steady.",
                "wind_speed_kmh": 12.0,
                "is_live": False
            }

weather_service = WeatherService()
