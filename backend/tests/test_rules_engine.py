import pytest
from app.services.rules_engine import rules_engine, STAGE_THRESHOLDS
from app.models.schemas import ActuatorStates

def test_stage_thresholds_instar_3():
    # 3rd Instar target temp is 25.0 - 26.5
    stage_3 = STAGE_THRESHOLDS[3]
    assert stage_3["temp_min"] == 25.0
    assert stage_3["temp_max"] == 26.5
    assert stage_3["hum_min"] == 70.0
    assert stage_3["hum_max"] == 75.0

def test_cooling_activation_on_high_temperature():
    actuators = ActuatorStates(cooler=False, heater=False, fan=False)
    # Temp 28.0 is well above 3rd instar max of 26.5
    status, headline, subline, next_actuators = rules_engine.evaluate(
        current_temp=28.0,
        current_hum=72.0,
        outside_temp=35.0,
        stage=3,
        is_auto_mode=True,
        current_actuators=actuators
    )
    assert status == "TOO_WARM"
    assert next_actuators.cooler is True
    assert next_actuators.heater is False  # Must not run heater

def test_heating_activation_on_low_temperature():
    actuators = ActuatorStates(cooler=False, heater=False, fan=False)
    # Temp 21.0 is below 3rd instar min of 25.0
    status, headline, subline, next_actuators = rules_engine.evaluate(
        current_temp=21.0,
        current_hum=72.0,
        outside_temp=18.0,
        stage=3,
        is_auto_mode=True,
        current_actuators=actuators
    )
    assert status == "TOO_COOL"
    assert next_actuators.heater is True
    assert next_actuators.cooler is False  # Must not run cooler

def test_safety_interlock_mutual_exclusion():
    # If somehow both cooler and heater were flagged True, rule engine enforces mutual exclusion
    actuators = ActuatorStates(cooler=True, heater=True, fan=False)
    _, _, _, next_actuators = rules_engine.evaluate(
        current_temp=29.0,
        current_hum=70.0,
        outside_temp=34.0,
        stage=3,
        is_auto_mode=True,
        current_actuators=actuators
    )
    # Simultaneous operation is strictly prohibited
    assert not (next_actuators.cooler and next_actuators.heater)
