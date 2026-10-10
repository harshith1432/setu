import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';

class InsightsScreen extends StatefulWidget {
  const InsightsScreen({Key? key}) : super(key: key);

  @override
  State<InsightsScreen> createState() => _InsightsScreenState();
}

class _InsightsScreenState extends State<InsightsScreen> {
  String _selectedCat = 'guides';

  void _showArticleDetailModal(
    BuildContext context, {
    required IconData icon,
    required Color bgColor,
    required Color iconColor,
    required String title,
    required String subtitle,
    required List<String> takeaways,
    required String fullBody,
  }) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        padding: EdgeInsets.only(
          left: 20,
          right: 20,
          top: 16,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 20,
        ),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Handle Bar
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
              const SizedBox(height: 14),

              // Title Row
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: bgColor,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(icon, color: iconColor, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          title,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF1B5E20),
                          ),
                        ),
                        Text(
                          subtitle,
                          style: const TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color: Color(0xFF5A695C),
                          ),
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, size: 20),
                    onPressed: () => Navigator.pop(ctx),
                  ),
                ],
              ),
              const Divider(height: 24, color: Color(0xFFF0F4EF)),

              // Key Takeaways Box
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFFF5F7F2),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFE0E7DC)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Row(
                      children: [
                        Icon(Icons.stars, color: Color(0xFF2E7D32), size: 16),
                        SizedBox(width: 6),
                        Text(
                          'Key Recommendations for Farmers',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w800,
                            color: Color(0xFF1B5E20),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...takeaways.map(
                      (item) => Padding(
                        padding: const EdgeInsets.only(bottom: 6.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text('• ', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                            Expanded(
                              child: Text(
                                item,
                                style: const TextStyle(fontSize: 12, color: Color(0xFF2E7D32), fontWeight: FontWeight.w600),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),

              // Full Body Content
              const Text(
                'Detailed Guidance & Standard Procedures',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: Color(0xFF1C251D)),
              ),
              const SizedBox(height: 6),
              Text(
                fullBody,
                style: const TextStyle(
                  fontSize: 12,
                  height: 1.5,
                  color: Color(0xFF37474F),
                ),
              ),
              const SizedBox(height: 20),

              // Action Button
              SizedBox(
                height: 48,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Got It, Close Guide', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final provider = Provider.of<SetuProvider>(context);
    final currentRegion = provider.region.isNotEmpty ? provider.region : 'Local Rearing Shed';

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l10n.translate('learningInsights'),
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          const Text(
            'Farmer knowledge base and regional sericulture updates',
            style: TextStyle(fontSize: 12, color: Color(0xFF5A695C)),
          ),
          const SizedBox(height: 14),

          // Category Tabs: Guides | Research | Updates
          Row(
            children: [
              _buildCatTab('guides', 'Guides'),
              const SizedBox(width: 6),
              _buildCatTab('research', 'Research'),
              const SizedBox(width: 6),
              _buildCatTab('updates', 'Updates'),
            ],
          ),
          const SizedBox(height: 14),

          // Insights Cards List with Material Vector Icons
          _buildInsightCard(
            context,
            icon: Icons.menu_book_rounded,
            bgColor: const Color(0xFFE1F5FE),
            iconColor: const Color(0xFF0288D1),
            title: l10n.translate('bestPractices'),
            sub: 'Feeding standards & bed cleaning.',
            takeaways: [
              'Feed fresh mulberry leaves 4 times daily at equal intervals.',
              'Clean bed trays using lime powder disinfectant after every moult.',
              'Maintain 25.0°C–26.5°C temperature for Double Hybrid FC1 x FC2.'
            ],
            fullBody:
                'Optimal feeding hygiene is critical to prevent disease outbreaks in silkworms. Ensure mulberry leaves are harvested early morning (6 AM - 8 AM) to retain moisture and nutrition. During 3rd and 4th instars, space trays adequately to avoid overcrowding and ensure proper ventilation throughout the rearing shed.',
          ),
          const SizedBox(height: 8),

          _buildInsightCard(
            context,
            icon: Icons.eco_rounded,
            bgColor: const Color(0xFFE8F5E9),
            iconColor: const Color(0xFF2E7D32),
            title: l10n.translate('envTips'),
            sub: 'Summer shed cooling techniques.',
            takeaways: [
              'Activate fogger cooling when indoor temperature exceeds 27.5°C.',
              'Hang wet gunny bags on window mesh during afternoon heat peak.',
              'Run exhaust vent fans between 12 PM and 3 PM to extract trapped heat.'
            ],
            fullBody:
                'Hot summer afternoons often exceed 35°C outside. Direct high temperatures cause heat stress, reducing cocoon weight and filament quality. Automated relay systems trigger foggers in hysteresis mode to reduce indoor temperature by up to 6°C without saturating air moisture.',
          ),
          const SizedBox(height: 8),

          _buildInsightCard(
            context,
            icon: Icons.lightbulb_outline_rounded,
            bgColor: const Color(0xFFFFF8E1),
            iconColor: const Color(0xFFF57F17),
            title: l10n.translate('commonProblems'),
            sub: 'Preventing flacherie & heat stress.',
            takeaways: [
              'Dust Vijetha or RKO disinfectant powder during moulting periods.',
              'Isolate sluggish or discolored larvae immediately to prevent spread.',
              'Maintain relative humidity above 70% to prevent leaf drying on trays.'
            ],
            fullBody:
                'Flacherie and Grasserie are viral and bacterial diseases aggravated by sudden temperature swings and high humidity drops. Dusting approved bed disinfectants before feeding post-moult builds strong immunity and prevents crop failure.',
          ),
          const SizedBox(height: 8),

          // Regional Focus Card
          _buildInsightCard(
            context,
            icon: Icons.location_on_rounded,
            bgColor: const Color(0xFFFFEBEE),
            iconColor: const Color(0xFFC62828),
            title: l10n.translate('regionInsights'),
            sub: '$currentRegion weather & alerts.',
            borderColor: const Color(0xFFE53935),
            takeaways: [
              '$currentRegion live conditions: Real-time outdoor microclimate.',
              'Keep automatic cooling setpoints locked at 26.0°C Target.',
              'Check water supply levels for foggers before noon peak.'
            ],
            fullBody:
                'Local outdoor climate directly influences indoor rearing conditions. Setu IoT edge sensors continuously monitor local microclimate variations in $currentRegion to ensure automated relay interlocks react instantaneously to preserve ideal rearing conditions.',
          ),
          const SizedBox(height: 16),

          // Weekly Stability Card
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
                const Text(
                  'Shed Stability This Week',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                ),
                const SizedBox(height: 6),
                const Row(
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text('94%', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: Color(0xFF2E7D32))),
                    SizedBox(width: 8),
                    Text('Time spent in ideal comfort zone', style: TextStyle(fontSize: 11, color: Color(0xFF5A695C))),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    _buildBarCol('Mon', 0.88),
                    _buildBarCol('Tue', 0.94),
                    _buildBarCol('Wed', 0.90),
                    _buildBarCol('Thu', 0.96),
                    _buildBarCol('Fri', 0.92),
                    _buildBarCol('Sat', 0.98),
                    _buildBarCol('Sun', 0.95),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCatTab(String cat, String label) {
    final isSelected = _selectedCat == cat;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _selectedCat = cat),
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFF1B5E20) : Colors.white,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: isSelected ? const Color(0xFF1B5E20) : const Color(0xFFE0E7DC),
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                color: isSelected ? Colors.white : const Color(0xFF5A695C),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildInsightCard(
    BuildContext context, {
    required IconData icon,
    required Color bgColor,
    required Color iconColor,
    required String title,
    required String sub,
    required List<String> takeaways,
    required String fullBody,
    Color? borderColor,
  }) {
    return InkWell(
      onTap: () => _showArticleDetailModal(
        context,
        icon: icon,
        bgColor: bgColor,
        iconColor: iconColor,
        title: title,
        subtitle: sub,
        takeaways: takeaways,
        fullBody: fullBody,
      ),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: borderColor ?? const Color(0xFFE0E7DC), width: borderColor != null ? 1.5 : 1),
        ),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(color: bgColor, borderRadius: BorderRadius.circular(10)),
              child: Center(child: Icon(icon, color: iconColor, size: 20)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(sub, style: const TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Color(0xFFB0BEC5), size: 18),
          ],
        ),
      ),
    );
  }

  Widget _buildBarCol(String day, double heightFraction) {
    return Column(
      children: [
        Container(
          width: 14,
          height: 50 * heightFraction,
          decoration: BoxDecoration(
            color: const Color(0xFF4CAF50),
            borderRadius: BorderRadius.circular(3),
          ),
        ),
        const SizedBox(height: 4),
        Text(day, style: const TextStyle(fontSize: 9, color: Color(0xFF5A695C))),
      ],
    );
  }
}
