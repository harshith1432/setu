from typing import Dict, Any, List
from app.models.schemas import AIExplanation, ActuatorStates

EXPLANATION_TEMPLATES = {
    "cooling": {
        "en": {
            "why": 'High outside heat ({out_temp:.1f}°C). Cooling active.',
            "action": "Cooling is ON",
            "target": "Target: Below {target_max:.1f}°C for {stage_name}.",
            "bullets": [
                "Keeps shed comfortable and prevents heat stress.",
                "Maintains regular feeding and healthy growth."
            ]
        },
        "kn": {
            "why": 'ಹೊರಗೆ ಹೆಚ್ಚಿನ ಬಿಸಿಲು ({out_temp:.1f}°C). ಕೂಲಿಂಗ್ ಆನ್ ಆಗಿದೆ.',
            "action": "ಕೂಲಿಂಗ್ ಆನ್ ಆಗಿದೆ",
            "target": "{stage_name} ಗುರಿ: {target_max:.1f}°C ಗಿಂತ ಕಡಿಮೆ.",
            "bullets": [
                "ಶಾಖದ ಒತ್ತಡವನ್ನು ತಡೆಯುತ್ತದೆ.",
                "ಹುಳುಗಳು ಸರಿಯಾಗಿ ಮೇವು ತಿನ್ನಲು ನೆರವಾಗುತ್ತದೆ."
            ]
        },
        "te": {
            "why": 'బయట అధిక వేడి ({out_temp:.1f}°C). కూలింగ్ ఆన్ చేయబడింది.',
            "action": "కూలింగ్ ఆన్‌లో ఉంది",
            "target": "{stage_name} లక్ష్యం: {target_max:.1f}°C కంటే తక్కువ.",
            "bullets": [
                "పురుగులకు వేడి ఒత్తిడిని తగ్గిస్తుంది.",
                "ఆరోగ్యకరమైన ఎదుగుదలను కాపాడుతుంది."
            ]
        }
    },
    "heating": {
        "en": {
            "why": 'Outside chill ({out_temp:.1f}°C). Heater active.',
            "action": "Heater is ON",
            "target": "Target: Above {target_min:.1f}°C for {stage_name}.",
            "bullets": [
                "Protects worms from cold shock.",
                "Ensures regular feeding and digestion."
            ]
        },
        "kn": {
            "why": 'ಹೊರಗೆ ಚಳಿ ({out_temp:.1f}°C). ಹೀಟರ್ ಆನ್ ಆಗಿದೆ.',
            "action": "ಹೀಟರ್ ಆನ್ ಆಗಿದೆ",
            "target": "{stage_name} ಗುರಿ: {target_min:.1f}°C ಗಿಂತ ಹೆಚ್ಚು.",
            "bullets": [
                "ಚಳಿಯಿಂದ ಹುಳುಗಳನ್ನು ರಕ್ಷಿಸುತ್ತದೆ.",
                "ಮೇವು ಜೀರ್ಣಕ್ರಿಯೆ ಸರಿಯಾಗಿರಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ."
            ]
        },
        "te": {
            "why": 'బయట చలి ({out_temp:.1f}°C). హీటర్ ఆన్ చేయబడింది.',
            "action": "హీటర్ ఆన్‌లో ఉంది",
            "target": "{stage_name} లక్ష్యం: {target_min:.1f}°C కంటే ఎక్కువ.",
            "bullets": [
                "చలి నుండి పురుగులను కాపాడుతుంది.",
                "ఆహారం తీసుకోవడం సాధారణంగా ఉండేలా చేస్తుంది."
            ]
        }
    },
    "ideal": {
        "en": {
            "why": 'Shed environment is balanced and ideal for {stage_name}.',
            "action": "Normal Standby",
            "target": "Target: {target_min:.1f}°C–{target_max:.1f}°C.",
            "bullets": [
                "Temperature and humidity in optimal zone.",
                "Normal feeding and active growth."
            ]
        },
        "kn": {
            "why": '{stage_name} ರೇಷ್ಮೆ ಹುಳುಗಳಿಗೆ ಪರಿಸರ ಸೂಕ್ತವಾಗಿದೆ.',
            "action": "ಸಾಮಾನ್ಯ ಸ್ಥಿತಿ",
            "target": "ಗುರಿ: {target_min:.1f}°C–{target_max:.1f}°C.",
            "bullets": [
                "ತಾಪಮಾನ ಮತ್ತು ತೇವಾಂಶ ನಿಗದಿತ ಮಿತಿಯಲ್ಲಿದೆ.",
                "ಹುಳುಗಳು ಆರೋಗ್ಯಕರವಾಗಿ ಬೆಳೆಯುತ್ತಿವೆ."
            ]
        },
        "te": {
            "why": '{stage_name} పురుగులకు షెడ్ వాతావరణం అనుకూలంగా ఉంది.',
            "action": "సాధారణ స్థితి",
            "target": "లక్ష్యం: {target_min:.1f}°C–{target_max:.1f}°C.",
            "bullets": [
                "ఉష్ణోగ్రత మరియు తేమ సరైన పరిధిలో ఉన్నాయి.",
                "పురుగులు ఆరోగ్యంగా పెరుగుతున్నాయి."
            ]
        }
    }
}

class AIExplainerService:
    def generate_explanation(
        self,
        overall_status: str,
        actuators: ActuatorStates,
        indoor_temp: float,
        indoor_hum: float,
        out_temp: float,
        stage: int,
        lang: str = "en",
        is_advanced_mode: bool = False,
        temp_target: float = None
    ) -> AIExplanation:
        from app.services.rules_engine import STAGE_THRESHOLDS
        thresholds = STAGE_THRESHOLDS.get(stage, STAGE_THRESHOLDS[3])
        stage_name = thresholds["name"]
        
        mode = "ideal"
        if actuators.cooler:
            mode = "cooling"
        elif actuators.heater:
            mode = "heating"

        selected_lang = lang if lang in ["en", "kn", "te"] else "en"
        tpl = EXPLANATION_TEMPLATES[mode][selected_lang]

        target_max = (temp_target + 0.5) if (is_advanced_mode and temp_target) else thresholds["temp_max"]
        target_min = (temp_target - 0.5) if (is_advanced_mode and temp_target) else thresholds["temp_min"]

        why_text = tpl["why"].format(
            out_temp=out_temp,
            target_max=target_max,
            target_min=target_min,
            stage_name=stage_name
        )
        target_desc = tpl["target"].format(
            target_max=target_max,
            target_min=target_min,
            stage_name=stage_name
        )
        if is_advanced_mode and temp_target and selected_lang == "en":
            target_desc = f"Target: Maintain {temp_target:.1f}°C (Farmer Setpoint)"

        return AIExplanation(
            why_text=why_text,
            current_action=tpl["action"],
            target_description=target_desc,
            bullet_points=tpl["bullets"],
            language=selected_lang
        )

ai_explainer = AIExplainerService()
