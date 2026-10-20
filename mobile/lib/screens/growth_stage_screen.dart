import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/growth_stage.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';

class GrowthStageScreen extends StatelessWidget {
  const GrowthStageScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final currentInfo = provider.currentStageInfo;
    final l10n = AppLocalizations.of(context);

    return RefreshIndicator(
      color: const Color(0xFF2E7D32),
      backgroundColor: Colors.white,
      onRefresh: () => provider.refreshAllData(userInitiated: true),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Screen Head
          Text(
            l10n.translate('growthStageTitle'),
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          const Text(
            'Recommended conditions adapt automatically to the rearing cycle.',
            style: TextStyle(fontSize: 12, color: Color(0xFF5A695C)),
          ),
          const SizedBox(height: 16),

          // Lifecycle selector: incubation through cocoon preservation
          Wrap(
            spacing: 10,
            runSpacing: 12,
            children: GrowthStageModel.allStages.map((stage) {
              final isSelected = provider.currentGrowthStage == stage.stageNumber;
              return InkWell(
                onTap: () => provider.setGrowthStage(stage.stageNumber),
                borderRadius: BorderRadius.circular(20),
                child: SizedBox(
                  width: 72,
                  child: Column(
                    children: [
                      Container(
                        width: 48,
                        height: 48,
                        decoration: BoxDecoration(
                          color: isSelected ? const Color(0xFF2E7D32) : Colors.white,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: isSelected ? const Color(0xFF2E7D32) : const Color(0xFFE0E7DC),
                            width: 2,
                          ),
                          boxShadow: isSelected
                              ? [
                                  BoxShadow(
                                    color: const Color(0xFF2E7D32).withValues(alpha: 0.35),
                                    blurRadius: 8,
                                    offset: const Offset(0, 3),
                                  )
                                ]
                              : null,
                        ),
                        child: Center(
                          child: Text(
                            stage.shortLabel,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w800,
                              color: isSelected ? Colors.white : const Color(0xFF5A695C),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        stage.name,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                          color: isSelected ? const Color(0xFF1B5E20) : const Color(0xFF5A695C),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),

          // Active Stage Detail Card
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: const Color(0xFFE0E7DC)),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        '${currentInfo.name} (${currentInfo.daysRange})',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w800,
                          color: Color(0xFF1B5E20),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Text(
                        'Active',
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: Color(0xFF1B5E20),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),

                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _buildTargetTile('Target Temp', '${currentInfo.tempMin}C - ${currentInfo.tempMax}C'),
                    _buildTargetTile('Target Humidity', '${currentInfo.humMin.toInt()}% - ${currentInfo.humMax.toInt()}%'),
                    _buildTargetTile('Air Quantity', '${currentInfo.airflowPercent}%'),
                    _buildTargetTile('Light Level', '${currentInfo.lightPercent}%'),
                  ],
                ),
                const SizedBox(height: 14),

                // Guidance Bullets (Short)
                const Text(
                  'Key Focus:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                ...currentInfo.guidancePoints.take(2).map((pt) => Padding(
                      padding: const EdgeInsets.only(bottom: 6.0),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('✓ ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: Color(0xFF2E7D32))),
                          Expanded(
                            child: Text(
                              pt,
                              style: const TextStyle(fontSize: 12, color: Color(0xFF37474F)),
                            ),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Set as Current Stage Button
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFE8F5E9),
              foregroundColor: const Color(0xFF1B5E20),
              elevation: 0,
              side: const BorderSide(color: Color(0xFF2E7D32), width: 1.5),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Shed 01 set to ${currentInfo.name}. Target thresholds adapted.')),
              );
            },
            child: Text(
              l10n.translate('setAsCurrentStage'),
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
            ),
          ),
        ],
      ),
      ),
    );
  }

  Widget _buildTargetTile(String label, String value) {
    return SizedBox(
      width: 140,
      child: Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: const Color(0xFFF5F7F2),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
            Text(
              value,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ],
        ),
      ),
    );
  }
}
