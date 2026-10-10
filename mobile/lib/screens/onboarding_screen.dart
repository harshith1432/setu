import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sericare_provider.dart';
import '../l10n/app_localizations.dart';

class OnboardingScreen extends StatelessWidget {
  final VoidCallback onProceed;

  const OnboardingScreen({Key? key, required this.onProceed}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SeriCareProvider>(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF5F7F2),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 20.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // Hero Branding
              Column(
                children: [
                  const SizedBox(height: 16),
                  Container(
                    width: 90,
                    height: 90,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFC8E6C9), Color(0xFF81C784)],
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: const Color(0xFF4CAF50).withOpacity(0.3),
                          blurRadius: 18,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Text('🐛', style: TextStyle(fontSize: 44)),
                    ),
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'SeriCare',
                    style: TextStyle(
                      fontSize: 32,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF1B5E20),
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    l10n.translate('tagline'),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF5A695C),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFFF3E0),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Text('📍 ', style: TextStyle(fontSize: 13)),
                        Text(
                          l10n.translate('region'),
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: Color(0xFFB26A00),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              // Language Selector Card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: const Color(0xFFE0E7DC)),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.04),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.translate('chooseLang'),
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.translate('chooseLangSub'),
                      style: const TextStyle(
                        fontSize: 11,
                        color: Color(0xFF5A695C),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // English
                    _buildLangButton(
                      context,
                      flag: '🌐',
                      title: 'English',
                      sub: 'Default · Technical & Simple',
                      code: 'en',
                      isSelected: provider.locale.languageCode == 'en',
                      onTap: () => provider.setLocale(const Locale('en')),
                    ),
                    const SizedBox(height: 8),

                    // Kannada
                    _buildLangButton(
                      context,
                      flag: '🌾',
                      title: 'ಕನ್ನಡ (Kannada)',
                      sub: 'ಮುಳಬಾಗಿಲು ಪ್ರಾದೇಶಿಕ ಆವೃತ್ತಿ',
                      code: 'kn',
                      isSelected: provider.locale.languageCode == 'kn',
                      onTap: () => provider.setLocale(const Locale('kn')),
                    ),
                    const SizedBox(height: 8),

                    // Telugu
                    _buildLangButton(
                      context,
                      flag: '🌱',
                      title: 'తెలుగు (Telugu)',
                      sub: 'రైతు అనుకూల ఇంటర్‌ఫేస్',
                      code: 'te',
                      isSelected: provider.locale.languageCode == 'te',
                      onTap: () => provider.setLocale(const Locale('te')),
                    ),
                  ],
                ),
              ),

              // Enter Dashboard Button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF2E7D32),
                    elevation: 3,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  onPressed: onProceed,
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        l10n.translate('enterApp'),
                        style: const TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(width: 8),
                      const Icon(Icons.arrow_forward, color: Colors.white, size: 20),
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

  Widget _buildLangButton(
    BuildContext context, {
    required String flag,
    required String title,
    required String sub,
    required String code,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFFE8F5E9) : const Color(0xFFF9FBF8),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? const Color(0xFF2E7D32) : const Color(0xFFE0E7DC),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Text(flag, style: const TextStyle(fontSize: 22)),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    sub,
                    style: const TextStyle(
                      fontSize: 10,
                      color: Color(0xFF5A695C),
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              const Icon(Icons.check_circle, color: Color(0xFF2E7D32), size: 20),
          ],
        ),
      ),
    );
  }
}
