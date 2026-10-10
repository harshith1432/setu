import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';
import '../widgets/visual_comfort_chart.dart';

class EnvironmentScreen extends StatefulWidget {
  final VoidCallback onOpenManual;

  const EnvironmentScreen({Key? key, required this.onOpenManual}) : super(key: key);

  @override
  State<EnvironmentScreen> createState() => _EnvironmentScreenState();
}

class _EnvironmentScreenState extends State<EnvironmentScreen> {
  bool _isDetailedView = false;
  String _selectedPeriod = 'today';

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final shed = provider.shedData;
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Segmented Control: Simple View vs Detailed View
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: const Color(0xFFE0E7DC),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () => setState(() => _isDetailedView = false),
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: !_isDetailedView ? Colors.white : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: !_isDetailedView
                            ? [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 4)]
                            : null,
                      ),
                      child: Center(
                        child: Text(
                          l10n.translate('simpleView'),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: !_isDetailedView ? const Color(0xFF1C251D) : const Color(0xFF5A695C),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: InkWell(
                    onTap: () => setState(() => _isDetailedView = true),
                    borderRadius: BorderRadius.circular(10),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      decoration: BoxDecoration(
                        color: _isDetailedView ? Colors.white : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                        boxShadow: _isDetailedView
                            ? [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 4)]
                            : null,
                      ),
                      child: Center(
                        child: Text(
                          l10n.translate('detailedView'),
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: _isDetailedView ? const Color(0xFF1C251D) : const Color(0xFF5A695C),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // Period Filters: Today / 7 Days / 30 Days
          Row(
            children: [
              _buildPeriodTab('today', l10n.translate('today')),
              const SizedBox(width: 6),
              _buildPeriodTab('7days', l10n.translate('sevenDays')),
              const SizedBox(width: 6),
              _buildPeriodTab('30days', l10n.translate('thirtyDays')),
            ],
          ),
          const SizedBox(height: 14),

          // Visual Temperature Chart with Shaded Band
          VisualComfortChart(
            title: l10n.translate('temperature'),
            currentVal: '${shed.indoorTemp}°C',
            idealZoneText: 'Ideal Zone (24°–27°)',
            topLabel: l10n.translate('tooHot'),
            midLabel: l10n.translate('ideal'),
            bottomLabel: l10n.translate('tooCool'),
            lineColor: const Color(0xFFE65100),
            normalizedPoints: const [0.55, 0.60, 0.52, 0.35, 0.48, 0.58],
          ),
          const SizedBox(height: 14),

          // Visual Humidity Chart with Shaded Band
          VisualComfortChart(
            title: l10n.translate('humidity'),
            currentVal: '${shed.indoorHumidity.toInt()}%',
            idealZoneText: 'Ideal Zone (70%–80%)',
            topLabel: l10n.translate('tooHigh'),
            midLabel: l10n.translate('ideal'),
            bottomLabel: l10n.translate('tooLow'),
            lineColor: const Color(0xFF0288D1),
            normalizedPoints: const [0.45, 0.42, 0.50, 0.55, 0.48, 0.50],
          ),
          const SizedBox(height: 14),

          // Detailed Metrics Section (shown if detailed view is toggled)
          if (_isDetailedView) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: const Color(0xFFE0E7DC)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Exact Sensor Readings',
                        style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: const Color(0xFFA5D6A7)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.location_on, size: 10, color: Color(0xFF2E7D32)),
                            const SizedBox(width: 3),
                            Text(
                              provider.liveWeather?.locationName ?? provider.region,
                              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  GridView.count(
                    crossAxisCount: 2,
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisSpacing: 8,
                    mainAxisSpacing: 8,
                    childAspectRatio: 2.2,
                    children: [
                      _buildMetricCell('Indoor Temp', '${shed.indoorTemp} °C'),
                      _buildMetricCell('Indoor Humidity', '${shed.indoorHumidity.toInt()} %'),
                      _buildMetricCell('Outside Temp (Live)', '${shed.outsideTemp} °C'),
                      _buildMetricCell('Outside Humidity (Live)', '${shed.outsideHumidity.toInt()} %'),
                      _buildMetricCell('Device Node', 'ESP32 Online', isGreen: true),
                      _buildMetricCell('Cooling Relay', shed.actuators.cooler ? 'Active (Fogger)' : 'Standby', isGreen: shed.actuators.cooler),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 14),
          ],

          // Manual Control Override Banner
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFFFF8E1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFFFE082)),
            ),
            child: Row(
              children: [
                const Icon(Icons.tune_rounded, color: Color(0xFFF57F17), size: 22),
                const SizedBox(width: 8),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Need manual override?',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFFF57F17)),
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        'Adjust setpoints or relays',
                        style: TextStyle(fontSize: 10, color: Color(0xFF795548)),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: const Color(0xFFE65100),
                    elevation: 0,
                    side: const BorderSide(color: Color(0xFFFFA000)),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: widget.onOpenManual,
                  child: const Text('Open Controls', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPeriodTab(String period, String label) {
    final isSelected = _selectedPeriod == period;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _selectedPeriod = period),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFFE8F5E9) : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected ? const Color(0xFF2E7D32) : const Color(0xFFE0E7DC),
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                color: isSelected ? const Color(0xFF1B5E20) : const Color(0xFF5A695C),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetricCell(String label, String value, {bool isGreen = false}) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F7F2),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: isGreen ? const Color(0xFF2E7D32) : const Color(0xFF1C251D),
            ),
          ),
        ],
      ),
    );
  }
}
