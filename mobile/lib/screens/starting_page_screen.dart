import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../l10n/app_localizations.dart';
import '../widgets/user_profile_modal.dart';

class StartingPageScreen extends StatelessWidget {
  final VoidCallback onStart;

  const StartingPageScreen({Key? key, required this.onStart}) : super(key: key);

  void _openProfileModal(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const UserProfileModal(),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Top Bar: Location Badge + Profile Chip
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.location_on, size: 14, color: Color(0xFF1B5E20)),
                        SizedBox(width: 4),
                        Text(
                          'Mulbagal Cluster',
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
                        ),
                      ],
                    ),
                  ),
                  InkWell(
                    onTap: () => _openProfileModal(context),
                    borderRadius: BorderRadius.circular(20),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: const Color(0xFFC8E6C9)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          CircleAvatar(
                            radius: 12,
                            backgroundColor: const Color(0xFF2E7D32),
                            child: Text(
                              provider.userName.isNotEmpty ? provider.userName[0].toUpperCase() : 'R',
                              style: const TextStyle(fontSize: 11, color: Colors.white, fontWeight: FontWeight.bold),
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            provider.userName.split(' ')[0],
                            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),

              // Hero Branding Area
              Center(
                child: Column(
                  children: [
                    Container(
                      width: 86,
                      height: 86,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF81C784), Color(0xFF2E7D32)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        shape: BoxShape.circle,
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF2E7D32).withValues(alpha: 0.25),
                            blurRadius: 18,
                            offset: const Offset(0, 8),
                          ),
                        ],
                      ),
                      child: const Center(
                        child: Icon(Icons.eco_rounded, size: 46, color: Colors.white),
                      ),
                    ),
                    const SizedBox(height: 14),
                    Text(
                      l10n.translate('appName'),
                      style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w900,
                        color: Color(0xFF1B5E20),
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.translate('tagline'),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Color(0xFF5A695C),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 22),

              // Live Shed Summary Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(22),
                  border: Border.all(color: const Color(0xFFE0E7DC)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.03),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Welcome, ${provider.userName}',
                                overflow: TextOverflow.ellipsis,
                                maxLines: 1,
                                style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Color(0xFF1C251D)),
                              ),
                              Text(
                                'Shed 01 · Batch ${provider.batchId}',
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 11, color: Color(0xFF5A695C)),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFE8F5E9),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.circle, color: Color(0xFF2E7D32), size: 8),
                              SizedBox(width: 4),
                              Text(
                                'Live IoT',
                                style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32)),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const Divider(height: 22, color: Color(0xFFF0F4EF)),
                    Row(
                      children: [
                        Expanded(child: _buildQuickMetric('Indoor Temp', '${provider.shedData.indoorTemp}°C', 'Ideal')),
                        Container(width: 1, height: 32, color: const Color(0xFFE0E7DC)),
                        Expanded(child: _buildQuickMetric('Humidity', '${provider.shedData.indoorHumidity.toInt()}%', 'Balanced')),
                        Container(width: 1, height: 32, color: const Color(0xFFE0E7DC)),
                        Expanded(child: _buildQuickMetric('Stage', '3rd Instar', 'Targets Met')),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),

              // CTA Action Button
              SizedBox(
                height: 52,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    elevation: 2,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: onStart,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        l10n.translate('enterApp'),
                        style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.white),
                      ),
                      const SizedBox(width: 8),
                      const Icon(Icons.arrow_forward, color: Colors.white, size: 18),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuickMetric(String title, String val, String sub) {
    return Column(
      children: [
        Text(val, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900, color: Color(0xFF1B5E20))),
        const SizedBox(height: 2),
        Text(title, style: const TextStyle(fontSize: 10, color: Color(0xFF5A695C), fontWeight: FontWeight.w600)),
        Text(sub, style: const TextStyle(fontSize: 9, color: Color(0xFF388E3C), fontWeight: FontWeight.w500)),
      ],
    );
  }
}
