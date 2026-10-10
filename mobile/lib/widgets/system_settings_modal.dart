import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sericare_provider.dart';

class SystemSettingsModal extends StatefulWidget {
  const SystemSettingsModal({Key? key}) : super(key: key);

  @override
  State<SystemSettingsModal> createState() => _SystemSettingsModalState();
}

class _SystemSettingsModalState extends State<SystemSettingsModal> {
  bool _notificationsEnabled = true;

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SeriCareProvider>(context);

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
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'System Settings',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Notifications
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Row(
                  children: [
                    Icon(Icons.notifications_active_outlined, color: Color(0xFF2E7D32), size: 20),
                    SizedBox(width: 10),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Smart Notifications', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                        Text('Alerts on heat rise and dry air', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                      ],
                    ),
                  ],
                ),
                Switch(
                  value: _notificationsEnabled,
                  activeThumbColor: const Color(0xFF2E7D32),
                  onChanged: (val) => setState(() => _notificationsEnabled = val),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Language Selector
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => _showLanguageSelector(context, provider),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.language_rounded, color: Color(0xFF2E7D32), size: 20),
                      SizedBox(width: 10),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Language / ಭಾಷೆ', style: TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                          Text('Change application dialect', style: TextStyle(fontSize: 10, color: Color(0xFF5A695C))),
                        ],
                      ),
                    ],
                  ),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFC8E6C9)),
                        ),
                        child: Text(
                          provider.locale.languageCode == 'kn'
                              ? 'ಕನ್ನಡ'
                              : (provider.locale.languageCode == 'te' ? 'తెలుగు' : 'English'),
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32)),
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Icon(Icons.arrow_drop_down, color: Color(0xFF2E7D32)),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),

          // Logout Button
          SizedBox(
            width: double.infinity,
            height: 46,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFFC62828),
                side: const BorderSide(color: Color(0xFFEF9A9A), width: 1.5),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              icon: const Icon(Icons.logout, size: 18),
              label: const Text(
                'Log Out',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
              ),
              onPressed: () async {
                Navigator.pop(context);
                await provider.logout();
              },
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  void _showLanguageSelector(BuildContext context, SeriCareProvider provider) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      backgroundColor: Colors.white,
      builder: (ctx) {
        final currentCode = provider.locale.languageCode;
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'Select Language / ಭಾಷೆ ಆಯ್ಕೆ',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF1B5E20)),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close, size: 20),
                      onPressed: () => Navigator.pop(ctx),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('English', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'en' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('en'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('ಕನ್ನಡ (Kannada)', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'kn' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('kn'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.language, color: Color(0xFF2E7D32)),
                  title: const Text('తెలుగు (Telugu)', style: TextStyle(fontWeight: FontWeight.w700)),
                  trailing: currentCode == 'te' ? const Icon(Icons.check_circle, color: Color(0xFF2E7D32)) : null,
                  onTap: () {
                    provider.setLocale(const Locale('te'));
                    Navigator.pop(ctx);
                    if (mounted) setState(() {});
                  },
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        );
      },
    );
  }
}
