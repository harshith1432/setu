import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sericare_provider.dart';
import '../l10n/app_localizations.dart';

class AdvancedModeModal extends StatelessWidget {
  const AdvancedModeModal({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SeriCareProvider>(context);
    final l10n = AppLocalizations.of(context);
    final isAuto = provider.isAutoMode;
    final actuators = provider.shedData.actuators;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
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
                'Advanced Mode (Manual Control)',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Auto Mode vs Manual Mode switch
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
                          'Auto Mode',
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
                          'Manual Mode',
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
                    '${provider.tempSetPoint.toStringAsFixed(1)}',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 8),
                  _buildStepBtn('+', () => provider.adjustTempSetPoint(0.5)),
                ],
              ),
            ],
          ),
          const Divider(height: 24),

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
                  Row(
                    children: [
                      _buildRelayBtn('❄️ Cooler', actuators.cooler, () => provider.toggleActuator('cooler')),
                      const SizedBox(width: 6),
                      _buildRelayBtn('🌀 Fan', actuators.fan, () => provider.toggleActuator('fan')),
                      const SizedBox(width: 6),
                      _buildRelayBtn('🔥 Heater', actuators.heater, () => provider.toggleActuator('heater')),
                    ],
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

  Widget _buildRelayBtn(String label, bool isOn, VoidCallback onTap) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
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
      ),
    );
  }
}
