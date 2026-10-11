import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';

class AdvancedModeModal extends StatelessWidget {
  const AdvancedModeModal({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final l10n = AppLocalizations.of(context);
    final isAuto = provider.isAutoMode;
    final actuators = provider.shedData.actuators;
    final preset = provider.currentStageInfo;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
          // Drag handle
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFFCFD8DC),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Head
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Simple and Advanced Controls',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Simple Mode vs Advanced Mode switch
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () => provider.setAutoMode(true),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: isAuto ? const Color(0xFF2E7D32) : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Center(
                        child: Text(
                          'Simple Mode',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: isAuto ? Colors.white : const Color(0xFF5A695C),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: InkWell(
                    onTap: () => provider.setAutoMode(false),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: !isAuto ? const Color(0xFF2E7D32) : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Center(
                        child: Text(
                          'Advanced Mode',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: !isAuto ? Colors.white : const Color(0xFF5A695C),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          if (isAuto) ...[
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFE8F5E9),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFA5D6A7)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Simple mode preset: ${preset.name}',
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'Farmers get stage-wise defaults from the lifecycle chart for temperature, humidity, air quantity, and light.',
                    style: TextStyle(fontSize: 11, color: Color(0xFF4E5D50)),
                  ),
                  const SizedBox(height: 10),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _buildPresetBadge('Temp', '${provider.tempSetPoint.toStringAsFixed(1)} C'),
                      _buildPresetBadge('Humidity', '${provider.humSetPoint.toInt()}%'),
                      _buildPresetBadge('Air Quality', '>= ${provider.airQualitySetPoint.toInt()}%'),
                      _buildPresetBadge('Light Target', '${provider.lightLuxSetPoint.toInt()} Lux'),
                      _buildPresetBadge('Bulb PWM', '${provider.lightBrightness}%'),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          // Temperature Set Point Stepper
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.translate('tempSetPoint'),
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  const Text('Target cooling/heating activation', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                ],
              ),
              Row(
                children: [
                  _buildStepBtn('-', () => provider.adjustTempSetPoint(-0.5)),
                  const SizedBox(width: 8),
                  Text(
                    provider.tempSetPoint.toStringAsFixed(1),
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  _buildStepBtn('+', () => provider.adjustTempSetPoint(0.5)),
                ],
              ),
            ],
          ),
          const Divider(height: 20),

          // Humidity Set Point Stepper
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.translate('humiditySetPoint'),
                    style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  const Text('Target fogger/dehumidifier range', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                ],
              ),
              Row(
                children: [
                  _buildStepBtn('-', () => provider.adjustHumSetPoint(-5.0)),
                  const SizedBox(width: 8),
                  Text(
                    '${provider.humSetPoint.toInt()}',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  _buildStepBtn('+', () => provider.adjustHumSetPoint(5.0)),
                ],
              ),
            ],
          ),
          const Divider(height: 20),

          // Air Quality Threshold Stepper (CO2 protection)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Air Quality Threshold (%)',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  Text('Triggers ventilation fan if below target', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                ],
              ),
              Row(
                children: [
                  _buildStepBtn('-', () => provider.adjustAirQualitySetPoint(-5.0)),
                  const SizedBox(width: 8),
                  Text(
                    '${provider.airQualitySetPoint.toInt()}%',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  _buildStepBtn('+', () => provider.adjustAirQualitySetPoint(5.0)),
                ],
              ),
            ],
          ),
          const Divider(height: 20),

          // Light Target Stepper (Research 15-30 Lux)
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Light Intensity Target (Lux)',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  Text('Research photoperiod (15–30 Lux)', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                ],
              ),
              Row(
                children: [
                  _buildStepBtn('-', () => provider.adjustLightLuxSetPoint(-5.0)),
                  const SizedBox(width: 8),
                  Text(
                    '${provider.lightLuxSetPoint.toInt()}',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  _buildStepBtn('+', () => provider.adjustLightLuxSetPoint(5.0)),
                ],
              ),
            ],
          ),
          const Divider(height: 20),

          // Dimmable Light Bulb PWM Brightness Slider
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'Bulb Brightness (PWM Dimmer)',
                    style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF3E0),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFFFFB74D)),
                    ),
                    child: Text(
                      '${provider.lightBrightness}% PWM',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFFE65100)),
                    ),
                  ),
                ],
              ),
              Slider(
                value: provider.lightBrightness.toDouble(),
                min: 0,
                max: 100,
                divisions: 20,
                activeColor: const Color(0xFFF57F17),
                inactiveColor: const Color(0xFFFFE082),
                label: '${provider.lightBrightness}%',
                onChanged: (val) => provider.setLightBrightness(val.round()),
              ),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  _buildPresetSliderBtn('Dark (0%)', 0, provider),
                  _buildPresetSliderBtn('Dim (25%)', 25, provider),
                  _buildPresetSliderBtn('Active (40%)', 40, provider),
                  _buildPresetSliderBtn('Full (100%)', 100, provider),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Manual Relays Overrides with Safety Interlock
          Opacity(
            opacity: isAuto ? 0.5 : 1.0,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF5F7F2),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.translate('manualRelays'),
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 8),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        _buildRelayBtn('❄️ Cooler', actuators.cooler, () => provider.toggleActuator('cooler')),
                        const SizedBox(width: 6),
                        _buildRelayBtn('🌀 Fan', actuators.fan, () => provider.toggleActuator('fan')),
                        const SizedBox(width: 6),
                        _buildRelayBtn('🔥 Heater', actuators.heater, () => provider.toggleActuator('heater')),
                        const SizedBox(width: 6),
                        _buildRelayBtn('💡 Bulb (${actuators.lightBrightness}%)', actuators.light, () => provider.toggleActuator('light')),
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    '⚠️ Safety interlock: Heater and Cooler can never run at the same time.',
                    style: TextStyle(fontSize: 9, color: Color(0xFFC62828)),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),


          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF2E7D32),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: () => Navigator.pop(context),
            child: Text(
              l10n.translate('saveApply'),
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700, color: Colors.white),
            ),
          ),
          const SizedBox(height: 10),
        ],
        ),
      ),
    );
  }

  Widget _buildPresetBadge(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFC8E6C9)),
      ),
      child: RichText(
        text: TextSpan(
          style: const TextStyle(fontSize: 11, color: Color(0xFF1C251D)),
          children: [
            TextSpan(text: '$label: ', style: const TextStyle(fontWeight: FontWeight.w600)),
            TextSpan(text: value, style: const TextStyle(fontWeight: FontWeight.w800)),
          ],
        ),
      ),
    );
  }

  Widget _buildStepBtn(String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: const Color(0xFFE8F5E9),
          border: Border.all(color: const Color(0xFF2E7D32)),
          shape: BoxShape.circle,
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
          ),
        ),
      ),
    );
  }

  Widget _buildPresetSliderBtn(String label, int val, SetuProvider provider) {
    final isSelected = provider.lightBrightness == val;
    return InkWell(
      onTap: () => provider.setLightBrightness(val),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFF57F17) : const Color(0xFFFFF8E1),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSelected ? const Color(0xFFE65100) : const Color(0xFFFFD54F)),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w700,
            color: isSelected ? Colors.white : const Color(0xFF5D4037),
          ),
        ),
      ),
    );
  }

  Widget _buildRelayBtn(String label, bool isOn, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        margin: const EdgeInsets.only(right: 6),
        decoration: BoxDecoration(
          color: isOn ? const Color(0xFFE8F5E9) : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: isOn ? const Color(0xFF2E7D32) : const Color(0xFFE0E7DC),
            width: isOn ? 1.5 : 1,
          ),
        ),
        child: Column(
          children: [
            Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
            Text(
              isOn ? 'ON' : 'OFF',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: isOn ? const Color(0xFF2E7D32) : const Color(0xFF5A695C),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

