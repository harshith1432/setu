import json
import logging
import time
from typing import Dict, Any, Optional
import httpx

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
    def __init__(self, default_region: str = "Global Sericulture Network"):
        self.default_region = default_region
        self._weather_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._geocode_cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._client = httpx.Client(timeout=4.0, headers={"User-Agent": "Setu-Global/1.0"})

    def geocode_region(self, region_name: str) -> Optional[Dict[str, Any]]:
        """
        Geocodes any global region name, city, district, or address using Open-Meteo's geocoding API.
        Caches results for 24 hours to avoid external API rate limits.
        """
        if not region_name or not region_name.strip():
            return None
            
        clean_name = region_name.split(',')[0].strip()
        if not clean_name:
            clean_name = region_name.strip()

        cache_key = clean_name.lower()
        now = time.time()
        if cache_key in self._geocode_cache:
            expires, cached_val = self._geocode_cache[cache_key]
            if now < expires:
                return cached_val

        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={clean_name}&count=1&language=en&format=json"
            res = self._client.get(geo_url)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results:
                    best = results[0]
                    name = best.get("name", clean_name)
                    admin1 = best.get("admin1", "")
                    country = best.get("country", "")
                    label_parts = [p for p in [name, admin1, country] if p]
                    formatted_region = ", ".join(label_parts)
                    result_data = {
                        "latitude": float(best["latitude"]),
                        "longitude": float(best["longitude"]),
                        "formatted_region": formatted_region
                    }
                    self._geocode_cache[cache_key] = (now + 86400, result_data)  # 24 hours
                    return result_data
        except Exception as e:
            logger.warning(f"Geocoding failed for '{region_name}': {e}")
        return None

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """
        Reverse geocodes GPS coordinates to city, state, country anywhere in the world.
        """
        cache_key = f"{round(lat, 2)}:{round(lon, 2)}"
        now = time.time()
        if cache_key in self._geocode_cache:
            expires, cached_val = self._geocode_cache[cache_key]
            if now < expires:
                return cached_val.get("formatted_region")

        # 1. Try OpenStreetMap Nominatim for exact, modern local place names
        try:
            nom_url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
            res = self._client.get(nom_url, headers={"User-Agent": "SetuApp/1.0"}, timeout=3.5)
            if res.status_code == 200:
                data = res.json()
                addr = data.get("address", {})
                local = (
                    addr.get("village")
                    or addr.get("town")
                    or addr.get("city")
                    or addr.get("suburb")
                    or addr.get("neighbourhood")
                    or addr.get("residential")
                )
                broader = (
                    addr.get("county")
                    or addr.get("state_district")
                    or addr.get("city")
                    or addr.get("town")
                )
                country = addr.get("country")
                parts = [p for p in [local, broader if broader != local else None, country] if p]
                if parts:
                    region_str = ", ".join(parts)
                    self._geocode_cache[cache_key] = (now + 86400, {"formatted_region": region_str})
                    return region_str
        except Exception as e:
            logger.debug(f"Nominatim reverse geocode error: {e}")

        # 2. Fallback to BigDataCloud
        try:
            url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat}&longitude={lon}&localityLanguage=en"
            res = self._client.get(url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                city = data.get("city") or data.get("locality") or ""
                subdiv = data.get("principalSubdivision") or ""
                country = data.get("countryName") or ""
                parts = [p for p in [city, subdiv, country] if p]
                if parts:
                    region_str = ", ".join(parts)
                    self._geocode_cache[cache_key] = (now + 86400, {"formatted_region": region_str})
                    return region_str
        except Exception as e:
            logger.warning(f"Reverse geocode failed for {lat}, {lon}: {e}")
        return None

    def get_current_weather(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        region: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches live real-time weather from Open-Meteo for any latitude/longitude or region name.
        Uses in-memory TTL caching (15 minutes) to prevent thread starvation and rate-limiting.
        """
        display_region = region.strip() if region and region.strip() else None
        latitude = lat
        longitude = lon

        # If coordinates provided but region name is missing, reverse geocode to find exact place name
        if latitude is not None and longitude is not None and not display_region:
            display_region = self.reverse_geocode(latitude, longitude) or f"Coordinates ({latitude:.2f}, {longitude:.2f})"

        # If lat/lon not provided, resolve via geocoding
        if latitude is None or longitude is None:
            if display_region:
                geo = self.geocode_region(display_region)
                if geo:
                    latitude = geo["latitude"]
                    longitude = geo["longitude"]
                    if not region:
                        display_region = geo["formatted_region"]
            else:
                display_region = self.default_region

        # If still missing coordinates, resolve via secure IP geolocation (HTTPS)
        if latitude is None or longitude is None:
            try:
                ip_res = self._client.get("https://ipapi.co/json/", timeout=3.0)
                if ip_res.status_code == 200:
                    ip_data = ip_res.json()
                    latitude = float(ip_data.get("latitude", 0.0))
                    longitude = float(ip_data.get("longitude", 0.0))
                    if not region:
                        city = ip_data.get("city", "")
                        reg = ip_data.get("region", "")
                        parts = [p for p in [city, reg] if p]
                        display_region = ", ".join(parts) if parts else "Live Location"
            except Exception as e:
                logger.warning(f"Live IP geolocation failed: {e}")
                latitude = latitude or 13.08
                longitude = longitude or 77.58

        # Check weather cache by coordinate bucket (0.01 deg ~= 1.1 km)
        cache_key = f"weather:{round(latitude or 0.0, 2)}:{round(longitude or 0.0, 2)}"
        now = time.time()
        if cache_key in self._weather_cache:
            expires, cached_weather = self._weather_cache[cache_key]
            if now < expires:
                cached_copy = dict(cached_weather)
                if display_region:
                    cached_copy["region"] = display_region
                return cached_copy

        try:
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={latitude}&longitude={longitude}&"
                f"current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            )
            res = self._client.get(weather_url, timeout=4.0)
            if res.status_code == 200:
                payload = res.json()
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

                weather_data = {
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
                # Cache for 15 minutes (900 seconds)
                self._weather_cache[cache_key] = (now + 900, weather_data)
                return weather_data
        except Exception as e:
            logger.warning(f"Live Open-Meteo query failed for lat={latitude}, lon={longitude}: {e}")

        # Fallback graceful simulation if offline
        fallback_data = {
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
        return fallback_data

weather_service = WeatherService()
