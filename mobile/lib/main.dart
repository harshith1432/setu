import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'providers/setu_provider.dart';
import 'l10n/app_localizations.dart';
import 'screens/splash_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/starting_page_screen.dart';
import 'screens/home_screen.dart';
import 'screens/ai_guidance_screen.dart';
import 'screens/environment_screen.dart';
import 'screens/growth_stage_screen.dart';
import 'screens/insights_screen.dart';
import 'widgets/advanced_mode_modal.dart';
import 'widgets/system_settings_modal.dart';
import 'widgets/user_profile_modal.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => SetuProvider()),
      ],
      child: const SetuApp(),
    ),
  );
}

class SetuApp extends StatelessWidget {
  const SetuApp({super.key});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);

    return MaterialApp(
      title: 'Setu',
      debugShowCheckedModeBanner: false,
      locale: provider.locale,
      supportedLocales: const [
        Locale('en', ''),
        Locale('kn', ''),
        Locale('te', ''),
      ],
      localizationsDelegates: const [
        _AppLocalizationsDelegate(),
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        primaryColor: const Color(0xFF2E7D32),
        scaffoldBackgroundColor: const Color(0xFFF5F7F2),
        fontFamily: 'Roboto',
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF2E7D32),
          primary: const Color(0xFF2E7D32),
        ),
      ),
      home: const AppRootFlow(),
    );
  }
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) => ['en', 'kn', 'te'].contains(locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) async => AppLocalizations(locale);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

class AppRootFlow extends StatefulWidget {
  const AppRootFlow({super.key});

  @override
  State<AppRootFlow> createState() => _AppRootFlowState();
}

class _AppRootFlowState extends State<AppRootFlow> {
  bool _showSplash = true;
  bool _hasPassedStartingPage = false;

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);

    // Show custom branded Setu splash screen on startup
    if (_showSplash) {
      return SplashScreen(
        onFinish: () {
          setState(() {
            _showSplash = false;
          });
        },
      );
    }

    if (!provider.isInitialized) {
      return const Scaffold(
        backgroundColor: Color(0xFF1B5E20),
        body: Center(
          child: CircularProgressIndicator(color: Colors.white),
        ),
      );
    }

    // If user is not logged in, prompt Login / Sign Up
    if (!provider.isLoggedIn) {
      return AuthScreen(
        onLoginSuccess: () {
          setState(() {
            _hasPassedStartingPage = true;
          });
        },
      );
    }

    if (!_hasPassedStartingPage) {
      return StartingPageScreen(
        onStart: () => setState(() => _hasPassedStartingPage = true),
      );
    }

    return const MainNavigationShell();
  }
}

class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({super.key});

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  void _openAdvancedSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const AdvancedModeModal(),
    );
  }

  void _openSettingsSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const SystemSettingsModal(),
    );
  }

  void _openProfileSheet(BuildContext context) {
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

    final screens = [
      HomeScreen(
        onOpenDetails: () => provider.setBottomNavIndex(2),
        onOpenAi: () => provider.setBottomNavIndex(1),
        onOpenManual: () => _openAdvancedSheet(context),
      ),
      const AiGuidanceScreen(),
      EnvironmentScreen(
        onOpenManual: () => _openAdvancedSheet(context),
      ),
      const GrowthStageScreen(),
      const InsightsScreen(),
    ];

    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.white,
        elevation: 0.5,
        title: Row(
          children: [
            const Icon(Icons.eco, color: Color(0xFF2E7D32), size: 22),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    l10n.translate('appName'),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF1B5E20),
                    ),
                  ),
                  Text(
                    '${provider.shedData.shedId.toUpperCase()} · ${provider.region.split(',')[0]}',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF5A695C),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: CircleAvatar(
              radius: 13,
              backgroundColor: const Color(0xFF2E7D32),
              child: Text(
                provider.userName.isNotEmpty ? provider.userName[0].toUpperCase() : 'R',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white),
              ),
            ),
            tooltip: 'User Profile',
            onPressed: () => _openProfileSheet(context),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 10.0),
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFE8F5E9),
                foregroundColor: const Color(0xFF1B5E20),
                elevation: 0,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              ),
              icon: const Icon(Icons.tune, size: 14),
              label: Text(
                l10n.translate('advMode'),
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
              ),
              onPressed: () => _openAdvancedSheet(context),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.settings_outlined, color: Color(0xFF1C251D)),
            onPressed: () => _openSettingsSheet(context),
          ),
          const SizedBox(width: 2),
        ],
      ),
      body: SafeArea(
        child: screens[provider.currentBottomNavIndex],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: provider.currentBottomNavIndex,
        onTap: (index) => provider.setBottomNavIndex(index),
        selectedItemColor: const Color(0xFF1B5E20),
        unselectedItemColor: const Color(0xFF5A695C),
        type: BottomNavigationBarType.fixed,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11),
        unselectedLabelStyle: const TextStyle(fontWeight: FontWeight.w500, fontSize: 10),
        items: [
          BottomNavigationBarItem(
            icon: const Icon(Icons.home_outlined, size: 22),
            activeIcon: const Icon(Icons.home, size: 22),
            label: l10n.translate('home'),
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.auto_awesome_outlined, size: 22),
            activeIcon: const Icon(Icons.auto_awesome, size: 22),
            label: l10n.translate('ai'),
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.analytics_outlined, size: 22),
            activeIcon: const Icon(Icons.analytics, size: 22),
            label: l10n.translate('shed'),
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.grass_outlined, size: 22),
            activeIcon: const Icon(Icons.grass, size: 22),
            label: l10n.translate('stage'),
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.menu_book_outlined, size: 22),
            activeIcon: const Icon(Icons.menu_book, size: 22),
            label: l10n.translate('insights'),
          ),
        ],
      ),
    );
  }
}
