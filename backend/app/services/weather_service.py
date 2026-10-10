import random
from typing import Dict, Any

class WeatherService:
    def __init__(self, region: str = "Mulbagal, Kolar, Karnataka"):
        self.region = region

    def get_current_weather(self) -> Dict[str, Any]:
        """
        Simulates / fetches microclimate conditions for Mulbagal.
        During afternoon (typical high temp 32-36°C, humidity 45-60%).
        """
        return {
            "region": self.region,
            "outside_temperature": 34.2,
            "outside_humidity": 58.0,
            "condition": "Mostly Sunny",
            "forecast_trend": "Afternoon heat peak anticipated. High evaporation rate.",
            "wind_speed_kmh": 14.5
        }

weather_service = WeatherService()
