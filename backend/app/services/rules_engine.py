from typing import Tuple, Dict, Any
from app.models.schemas import ActuatorStates

STAGE_THRESHOLDS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "1st Instar (Chawki)",
        "days": "Days 1–3",
        "temp_min": 27.0, "temp_max": 28.0,
        "hum_min": 80.0, "hum_max": 85.0
    },
    2: {
        "name": "2nd Instar",
        "days": "Days 4–5",
        "temp_min": 26.5, "temp_max": 27.5,
        "hum_min": 75.0, "hum_max": 80.0
    },
    3: {
        "name": "3rd Instar",
        "days": "Days 6–9",
        "temp_min": 25.0, "temp_max": 26.5,
        "hum_min": 70.0, "hum_max": 75.0
    },
    4: {
        "name": "4th Instar",
        "days": "Days 10–14",
        "temp_min": 24.0, "temp_max": 25.5,
        "hum_min": 65.0, "hum_max": 70.0
    },
    5: {
        "name": "5th Instar",
        "days": "Days 15–20",
        "temp_min": 23.0, "temp_max": 24.5,
        "hum_min": 60.0, "hum_max": 65.0
    }
}

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
        manual_hum_target: float = 75.0
    ) -> Tuple[str, str, str, ActuatorStates]:
        """
        Evaluates indoor conditions, outside weather, stage targets, and hysteresis.
        Returns:
            (overall_status, status_headline, status_subline, next_actuators)
        """
        thresholds = STAGE_THRESHOLDS.get(stage, STAGE_THRESHOLDS[3])
        target_temp_max = thresholds["temp_max"]
        target_temp_min = thresholds["temp_min"]
        target_hum_max = thresholds["hum_max"]
        target_hum_min = thresholds["hum_min"]

        new_actuators = ActuatorStates(
            cooler=current_actuators.cooler,
            fan=current_actuators.fan,
            heater=current_actuators.heater
        )

        overall_status = "IDEAL"
        headline = "Ideal for Silkworms"
        subline = "Everything is comfortable inside the shed. No action required."

        # Sensor validity check
        if current_temp < 5.0 or current_temp > 50.0 or current_hum < 10.0 or current_hum > 100.0:
            return ("CRITICAL", "Sensor Error", "Readings out of physical bounds. Check hardware.", current_actuators)

        # Automatic Decision Making with Hysteresis
        if is_auto_mode:
            # High Temperature Logic
            if current_temp > target_temp_max + 0.3:
                new_actuators.cooler = True
                new_actuators.heater = False  # HARD INTERLOCK
                if current_temp > target_temp_max + 1.5 or outside_temp > 35.0:
                    new_actuators.fan = True
                overall_status = "TOO_WARM"
                headline = "Too Warm — Cooling Active"
                subline = f"Shed is {current_temp:.1f}°C (target max {target_temp_max}°C). Cooling running to prevent heat stress."
            
            # Low Temperature Logic
            elif current_temp < target_temp_min - 0.3:
                new_actuators.heater = True
                new_actuators.cooler = False  # HARD INTERLOCK
                new_actuators.fan = False
                overall_status = "TOO_COOL"
                headline = "Too Cool — Heating Active"
                subline = f"Shed is {current_temp:.1f}°C (target min {target_temp_min}°C). Heater running to maintain warmth."

            # Hysteresis return to ideal
            else:
                # If cooler was on, turn off only when cooled down below target max - hysteresis
                if current_actuators.cooler and current_temp < (target_temp_max - self.hysteresis_temp):
                    new_actuators.cooler = False
                    new_actuators.fan = False
                
                # If heater was on, turn off only when warmed up above target min + hysteresis
                if current_actuators.heater and current_temp > (target_temp_min + self.hysteresis_temp):
                    new_actuators.heater = False

                if not new_actuators.cooler and not new_actuators.heater:
                    overall_status = "IDEAL"
                    headline = "Ideal for Silkworms"
                    subline = "Everything is comfortable inside the shed. No action required."

        # Safety Interlock Enforcement
        if new_actuators.cooler and new_actuators.heater:
            # Mutual exclusion: Priority to cooling if hot, otherwise shut both
            if current_temp > target_temp_max:
                new_actuators.heater = False
            else:
                new_actuators.cooler = False

        return (overall_status, headline, subline, new_actuators)

rules_engine = RulesEngine()
