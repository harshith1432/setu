from typing import Tuple, Dict, Any
from app.models.schemas import ActuatorStates

STAGE_THRESHOLDS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "1st Instar (Chawki)",
        "days": "Days 1–3",
        "temp_min": 27.0, "temp_max": 28.0,
        "hum_min": 80.0, "hum_max": 85.0,
        "hysteresis_temp": 0.5, "hysteresis_hum": 3.0,
        "fan_trigger_offset": 1.5,
        "description": "Chawki stage: Delicate larvae requiring high humidity and warm ambient temperatures to prevent desiccation."
    },
    2: {
        "name": "2nd Instar",
        "days": "Days 4–5",
        "temp_min": 26.5, "temp_max": 27.5,
        "hum_min": 75.0, "hum_max": 80.0,
        "hysteresis_temp": 0.5, "hysteresis_hum": 3.0,
        "fan_trigger_offset": 1.5,
        "description": "Post-first moult larvae. Transitioning to active feeding with moderate humidity requirements."
    },
    3: {
        "name": "3rd Instar",
        "days": "Days 6–9",
        "temp_min": 25.0, "temp_max": 26.5,
        "hum_min": 70.0, "hum_max": 75.0,
        "hysteresis_temp": 0.5, "hysteresis_hum": 3.0,
        "fan_trigger_offset": 1.5,
        "description": "Late chawki / adult transition. Increased voracity requires steady ventilation and balanced thermal envelope."
    },
    4: {
        "name": "4th Instar",
        "days": "Days 10–14",
        "temp_min": 24.0, "temp_max": 25.5,
        "hum_min": 65.0, "hum_max": 70.0,
        "hysteresis_temp": 0.5, "hysteresis_hum": 3.0,
        "fan_trigger_offset": 1.5,
        "description": "Exponential larval weight gain. High metabolic heat output necessitates active cooling and air exchange."
    },
    5: {
        "name": "5th Instar",
        "days": "Days 15–20",
        "temp_min": 23.0, "temp_max": 24.5,
        "hum_min": 60.0, "hum_max": 65.0,
        "hysteresis_temp": 0.5, "hysteresis_hum": 3.0,
        "fan_trigger_offset": 1.5,
        "description": "Final feeding instar preceding cocooning/spinning. Requires cooler, drier conditions and continuous fresh airflow."
    }
}

def sync_thresholds_from_db():
    try:
        from app.services.db_service import get_all_stage_thresholds
        db_stages = get_all_stage_thresholds()
        if db_stages:
            for s in db_stages:
                sid = int(s["stage_id"])
                STAGE_THRESHOLDS[sid] = {
                    "name": s["name"],
                    "days": s["days"],
                    "temp_min": float(s["temp_min"]),
                    "temp_max": float(s["temp_max"]),
                    "hum_min": float(s["hum_min"]),
                    "hum_max": float(s["hum_max"]),
                    "hysteresis_temp": float(s.get("hysteresis_temp", 0.5)),
                    "hysteresis_hum": float(s.get("hysteresis_hum", 3.0)),
                    "fan_trigger_offset": float(s.get("fan_trigger_offset", 1.5)),
                    "description": s.get("description", "")
                }
    except Exception:
        pass

# Attempt initial sync on load
sync_thresholds_from_db()

from datetime import datetime, timezone

class RulesEngine:
    def __init__(self, hysteresis_temp: float = 0.5, hysteresis_hum: float = 3.0):
        self.hysteresis_temp = hysteresis_temp
        self.hysteresis_hum = hysteresis_hum

    def evaluate(
        self,
        current_temp: float,
        current_hum: float,
        outside_temp: float,
        stage: int,
        is_auto_mode: bool,
        current_actuators: ActuatorStates,
        manual_temp_target: float = 26.0,
        manual_hum_target: float = 75.0,
        current_air_quality: float = 88.0,
        current_light_lux: float = 22.0,
        air_quality_target: float = 80.0,
        light_lux_target: float = 25.0,
        current_hour: int = None
    ) -> Tuple[str, str, str, ActuatorStates, str]:
        """
        Evaluates indoor conditions, outside weather, air quality, light photoperiod, stage targets, and hysteresis.
        Returns:
            (overall_status, status_headline, status_subline, next_actuators, photoperiod_mode)
        """
        thresholds = STAGE_THRESHOLDS.get(stage, STAGE_THRESHOLDS[3])
        target_temp_max = thresholds["temp_max"]
        target_temp_min = thresholds["temp_min"]
        target_hum_max = thresholds["hum_max"]
        target_hum_min = thresholds["hum_min"]

        new_actuators = ActuatorStates(
            cooler=current_actuators.cooler,
            fan=current_actuators.fan,
            heater=current_actuators.heater,
            light=current_actuators.light,
            light_brightness=current_actuators.light_brightness
        )

        overall_status = "IDEAL"
        headline = "Ideal for Silkworms"
        subline = "Everything is comfortable inside the shed. No action required."

        # Sensor validity check
        if current_temp < 5.0 or current_temp > 50.0 or current_hum < 10.0 or current_hum > 100.0:
            return ("CRITICAL", "Sensor Error", "Readings out of physical bounds. Check hardware.", current_actuators, "DAY")

        # Determine photoperiod phase (Day 06:00 - 22:00 vs Night 22:00 - 06:00)
        if current_hour is None:
            current_hour = datetime.now(timezone.utc).hour + 5  # approx IST (+5:30)
            if current_hour >= 24:
                current_hour -= 24

        is_daytime = 6 <= current_hour < 22
        photoperiod_mode = "DAY" if is_daytime else "NIGHT"
        if stage == 5 and is_daytime:
            # During 5th instar late spinning, silkworms require semi-darkness (dim light ~10 Lux)
            photoperiod_mode = "SPINNING"

        # Automatic Decision Making with Hysteresis
        if is_auto_mode:
            # 1. Temperature & Humidity Automation
            temp_requires_fan = False
            if current_temp > target_temp_max + 0.3:
                new_actuators.cooler = True
                new_actuators.heater = False  # HARD INTERLOCK
                if current_temp > target_temp_max + 1.5 or outside_temp > 35.0:
                    new_actuators.fan = True
                    temp_requires_fan = True
                overall_status = "TOO_WARM"
                headline = "Too Warm — Cooling Active"
                subline = f"Shed is {current_temp:.1f}°C (target max {target_temp_max}°C). Cooling running to prevent heat stress."
            
            elif current_temp < target_temp_min - 0.3:
                new_actuators.heater = True
                new_actuators.cooler = False  # HARD INTERLOCK
                new_actuators.fan = False
                overall_status = "TOO_COOL"
                headline = "Too Cool — Heating Active"
                subline = f"Shed is {current_temp:.1f}°C (target min {target_temp_min}°C). Heater running to maintain warmth."

            else:
                # Return to ideal with hysteresis
                if current_actuators.cooler and current_temp < (target_temp_max - self.hysteresis_temp):
                    new_actuators.cooler = False
                    new_actuators.fan = False
                
                if current_actuators.heater and current_temp > (target_temp_min + self.hysteresis_temp):
                    new_actuators.heater = False

                if not new_actuators.cooler and not new_actuators.heater:
                    overall_status = "IDEAL"
                    headline = "Ideal for Silkworms"
                    subline = "Everything is comfortable inside the shed. No action required."

            # 2. Air Quality Automation (Grounded in Sericulture Research: CO2 < 1% / safe air quality)
            # If air quality drops below the expected target (e.g. 80.0%), turn ON ventilation fan
            if current_air_quality < air_quality_target:
                new_actuators.fan = True
                if overall_status == "IDEAL":
                    overall_status = "AIR_LOW"
                    headline = "Air Quality Low — Ventilation Active"
                    subline = f"Air quality is {current_air_quality:.0f}% (target >= {air_quality_target:.0f}%). Exhaust fan running for fresh aeration."
            else:
                # Turn off fan if temp doesn't need it and air quality recovered past hysteresis (+4%)
                if not temp_requires_fan and current_air_quality >= (air_quality_target + 4.0):
                    if not (current_temp > target_temp_max + 1.5):
                        new_actuators.fan = False

            # 3. Light Intensity & Photoperiod Dimming Automation (Research: 15–30 Lux day, <5 Lux night)
            if photoperiod_mode == "NIGHT":
                # Night rest: silkworms require darkness (< 5 Lux)
                new_actuators.light = False
                new_actuators.light_brightness = 0
            elif photoperiod_mode == "SPINNING":
                # 5th instar cocooning: dim diffuse light (~10 Lux) to prevent wandering
                effective_lux_target = 10.0
                if current_light_lux < effective_lux_target:
                    new_actuators.light = True
                    new_actuators.light_brightness = 15
                else:
                    new_actuators.light = False
                    new_actuators.light_brightness = 0
            else:
                # Standard daytime photoperiod: target 15-30 Lux (default 25 Lux)
                if current_light_lux < light_lux_target:
                    new_actuators.light = True
                    # Proportional PWM dimming: boost brightness if darker
                    lux_deficit = max(0.0, light_lux_target - current_light_lux)
                    pwm = int(25 + (lux_deficit / light_lux_target) * 35)
                    new_actuators.light_brightness = min(100, max(20, pwm))
                else:
                    # Natural daylight inside shed meets or exceeds requirement
                    new_actuators.light = False
                    new_actuators.light_brightness = 0

        # Safety Interlock Enforcement
        if new_actuators.cooler and new_actuators.heater:
            if current_temp > target_temp_max:
                new_actuators.heater = False
            else:
                new_actuators.cooler = False

        return (overall_status, headline, subline, new_actuators, photoperiod_mode)

rules_engine = RulesEngine()

