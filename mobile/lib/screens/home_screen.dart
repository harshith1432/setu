import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';
import '../widgets/live_weather_card.dart';

class HomeScreen extends StatelessWidget {
  final VoidCallback onOpenDetails;
  final VoidCallback onOpenAi;
  final VoidCallback onOpenManual;

  const HomeScreen({
    super.key,
    required this.onOpenDetails,
    required this.onOpenAi,
    required this.onOpenManual,
  });

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final shed = provider.shedData;
    final l10n = AppLocalizations.of(context);
    final stage = provider.currentStageInfo;

    Color heroCardBg = const Color(0xFFE8F5E9);
    Color heroCardBorder = const Color(0xFFA5D6A7);
    IconData heroIcon = Icons.check_circle_rounded;
    Color heroIconColor = const Color(0xFF2E7D32);

    if (shed.overallStatus == 'TOO_WARM') {
      heroCardBg = const Color(0xFFFFF3E0);
      heroCardBorder = const Color(0xFFFFB74D);
      heroIcon = Icons.warning_amber_rounded;
      heroIconColor = const Color(0xFFE65100);
    } else if (shed.overallStatus == 'TOO_COOL') {
      heroCardBg = const Color(0xFFE1F5FE);
      heroCardBorder = const Color(0xFF81D4FA);
      heroIcon = Icons.ac_unit_rounded;
      heroIconColor = const Color(0xFF0288D1);
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Live Location & Weather Feed
          const LiveWeatherCard(),
          const SizedBox(height: 12),

          // Big Friendly Status Card
          Container(
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
            decoration: BoxDecoration(
              color: heroCardBg,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: heroCardBorder, width: 2),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              children: [
                Icon(heroIcon, size: 48, color: heroIconColor),
                const SizedBox(height: 8),
                Text(
                  shed.overallStatus == 'TOO_WARM'
                      ? l10n.translate('tooWarmHeadline')
                      : (shed.overallStatus == 'TOO_COOL'
                          ? l10n.translate('tooCoolHeadline')
                          : l10n.translate('idealForSilkworms')),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF1B5E20),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.grass, color: Color(0xFF2E7D32), size: 14),
                          const SizedBox(width: 4),
                          Text(
                            l10n.translate('stage_${provider.currentGrowthStage}'),
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF1C251D),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.circle, color: Color(0xFF2E7D32), size: 8),
                          const SizedBox(width: 5),
                          Text(
                            l10n.translate('shedNo'),
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                              color: Color(0xFF1B5E20),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Sensor Indicators: 4-Metric Grid (Temp, Humidity, Air Quality, Light Lux)
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFE0E7DC)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Icon(Icons.thermostat_rounded, color: Color(0xFFE65100), size: 22),
                          Text(
                            '${shed.indoorTemp}°C',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.translate('temperature'),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                      ),
                      Text(
                        '${l10n.translate('target')}: ${stage.tempMin.toStringAsFixed(0)}-${stage.tempMax.toStringAsFixed(0)}°C',
                        style: const TextStyle(fontSize: 10, color: Color(0xFF2E7D32), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFE0E7DC)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Icon(Icons.water_drop_rounded, color: Color(0xFF0288D1), size: 22),
                          Text(
                            '${shed.indoorHumidity.toInt()}%',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.translate('humidity'),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                      ),
                      Text(
                        '${l10n.translate('target')}: ${stage.humMin.toInt()}-${stage.humMax.toInt()}%',
                        style: const TextStyle(fontSize: 10, color: Color(0xFF2E7D32), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),

          Row(
            children: [
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(
                      color: shed.indoorAirQuality < shed.airQualityTarget
                          ? const Color(0xFFFFB74D)
                          : const Color(0xFFE0E7DC),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Icon(
                            Icons.air_rounded,
                            color: shed.indoorAirQuality < shed.airQualityTarget ? const Color(0xFFE65100) : const Color(0xFF00897B),
                            size: 22,
                          ),
                          Text(
                            '${shed.indoorAirQuality.toInt()}%',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w800,
                              color: shed.indoorAirQuality < shed.airQualityTarget ? const Color(0xFFE65100) : const Color(0xFF1B5E20),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.translate('airQuality'),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                      ),
                      Text(
                        shed.indoorAirQuality < shed.airQualityTarget
                            ? 'CO₂ High • Fan Active'
                            : 'Clean • Target: >=${shed.airQualityTarget.toInt()}%',
                        style: TextStyle(
                          fontSize: 10,
                          color: shed.indoorAirQuality < shed.airQualityTarget ? const Color(0xFFD84315) : const Color(0xFF2E7D32),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFFE0E7DC)),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Icon(
                            Icons.lightbulb_rounded,
                            color: shed.actuators.light ? const Color(0xFFF57F17) : const Color(0xFF9E9E9E),
                            size: 22,
                          ),
                          Text(
                            '${shed.indoorLightLux.toInt()} Lux',
                            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF1B5E20)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        l10n.translate('lightIntensity'),
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                      ),
                      Text(
                        '${shed.photoperiodMode} • 15–30 Lux',
                        style: const TextStyle(fontSize: 10, color: Color(0xFF2E7D32), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // AI Quick Banner (Concise)
          InkWell(
            onTap: onOpenAi,
            borderRadius: BorderRadius.circular(18),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFFEDE7F6),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: const Color(0xFFD1C4E9)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_awesome, color: Color(0xFF7B1FA2), size: 22),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          shed.actuators.cooler
                              ? l10n.translate('coolingIsOn')
                              : (shed.actuators.heater
                                  ? l10n.translate('heatingIsOn')
                                  : (shed.actuators.fan ? l10n.translate('ventilationIsOn') : l10n.translate('allNormal'))),
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF4A148C)),
                        ),
                        Text(
                          shed.indoorAirQuality < shed.airQualityTarget
                              ? 'Low air quality detected. Exhaust fan active for fresh air circulation.'
                              : l10n.translate('everythingNormal'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11, color: Color(0xFF512DA8)),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.arrow_forward_ios, size: 14, color: Color(0xFF512DA8)),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // View Details Button
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white,
              foregroundColor: const Color(0xFF1B5E20),
              elevation: 1,
              side: const BorderSide(color: Color(0xFF2E7D32), width: 1.5),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: onOpenDetails,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  l10n.translate('viewDetails'),
                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 8),
                const Icon(Icons.arrow_forward, size: 18),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Connected Equipment
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: const Color(0xFFE0E7DC)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        l10n.translate('equipmentStatus'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        l10n.translate('autoActive'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.end,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF2E7D32)),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildEquipmentChip(Icons.ac_unit_rounded, 'Cooler', shed.actuators.cooler ? 'Running' : 'Off', shed.actuators.cooler),
                      const SizedBox(width: 8),
                      _buildEquipmentChip(Icons.air_rounded, 'Vent Fan', shed.actuators.fan ? 'Running' : 'Standby', shed.actuators.fan),
                      const SizedBox(width: 8),
                      _buildEquipmentChip(Icons.local_fire_department_rounded, 'Heater', shed.actuators.heater ? 'Running' : 'Off', shed.actuators.heater),
                      const SizedBox(width: 8),
                      _buildEquipmentChip(
                        Icons.lightbulb_rounded,
                        'Bulb (PWM)',
                        shed.actuators.light ? '${shed.actuators.lightBrightness}%' : 'Off',
                        shed.actuators.light,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Scenario Simulator (Farmer / Demo scenarios)
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: const Color(0xFFF0F4EF),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFA5D6A7), style: BorderStyle.solid),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.science_outlined, size: 14, color: Color(0xFF5A695C)),
                    SizedBox(width: 4),
                    Text(
                      'Test Shed Scenarios (Simulation):',
                      style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      _buildSimBtn('Ideal Day', () => provider.applyScenario('normal')),
                      const SizedBox(width: 6),
                      _buildSimBtn('Hot Noon (35°C)', () => provider.applyScenario('hot')),
                      const SizedBox(width: 6),
                      _buildSimBtn('Cold Night (20°C)', () => provider.applyScenario('cold')),
                      const SizedBox(width: 6),
                      _buildSimBtn('Stale Air (Fan ON)', () => provider.applyScenario('stale_air')),
                      const SizedBox(width: 6),
                      _buildSimBtn('Night Rest (<5 Lux)', () => provider.applyScenario('night_mode')),
                    ],
                  ),
                ),
              ],
            ),
          ),

        ],
      ),
    );
  }

  Widget _buildEquipmentChip(IconData icon, String name, String state, bool active) {
    return Container(
      width: 100,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: active ? const Color(0xFFE0F2F1) : const Color(0xFFF9FBF8),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: active ? const Color(0xFF80CBC4) : const Color(0xFFE0E7DC),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 20, color: active ? const Color(0xFF00695C) : const Color(0xFF5A695C)),
          const SizedBox(height: 4),
          Text(name, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700), maxLines: 1, overflow: TextOverflow.ellipsis),
          Text(
            state,
            style: TextStyle(
              fontSize: 9,
              fontWeight: active ? FontWeight.w700 : FontWeight.normal,
              color: active ? const Color(0xFF00695C) : const Color(0xFF5A695C),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  Widget _buildSimBtn(String label, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFE0E7DC)),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF1B5E20)),
        ),
      ),
    );
  }
}
