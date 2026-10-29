import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:provider/provider.dart';
import 'firebase_options.dart';
import 'providers/setu_provider.dart';
import 'l10n/app_localizations.dart';
import 'screens/splash_screen.dart';
import 'screens/auth_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/home_screen.dart';
import 'screens/ai_guidance_screen.dart';
import 'screens/environment_screen.dart';
import 'screens/growth_stage_screen.dart';
import 'screens/insights_screen.dart';
import 'screens/products_screen.dart';
import 'screens/orders_screen.dart';
import 'widgets/advanced_mode_modal.dart';
import 'widgets/system_settings_modal.dart';
import 'widgets/user_profile_modal.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );
  } catch (e) {
    debugPrint('Firebase.initializeApp notice: $e');
  }
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

    if (!provider.hasCompletedOnboarding) {
      return OnboardingScreen(
        onProceed: provider.completeOnboarding,
      );
    }

    // If user is not logged in, prompt Login / Sign Up
    if (!provider.isLoggedIn) {
      return AuthScreen(
        onLoginSuccess: () => setState(() {}),
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
            Image.asset(
              'assets/images/app_logo.png',
              width: 38,
              height: 38,
              fit: BoxFit.contain,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                '${provider.shedData.shedId.toUpperCase()} · ${provider.region.split(',')[0]}',
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF1B5E20),
                ),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.storefront_outlined, color: Color(0xFF1B5E20), size: 23),
            tooltip: 'Hardware Store',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ProductsScreen()),
              );
            },
          ),
          IconButton(
            icon: const Icon(Icons.local_shipping_outlined, color: Color(0xFF1B5E20), size: 23),
            tooltip: 'My Orders',
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const OrdersScreen()),
              );
            },
          ),
          PopupMenuButton<String>(
            icon: const Icon(
              Icons.more_vert,
              color: Color(0xFF1C251D),
              size: 24,
            ),
            tooltip: 'Menu',
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
            ),
            elevation: 4,
            color: Colors.white,
            offset: const Offset(0, 48),
            onSelected: (value) {
              if (value == 'profile') {
                _openProfileSheet(context);
              } else if (value == 'products') {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const ProductsScreen()),
                );
              } else if (value == 'orders') {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (_) => const OrdersScreen()),
                );
              } else if (value == 'advanced') {
                _openAdvancedSheet(context);
              } else if (value == 'settings') {
                _openSettingsSheet(context);
              }
            },
            itemBuilder: (BuildContext ctx) => [
              PopupMenuItem<String>(
                value: 'products',
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.storefront_outlined,
                        size: 16,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Hardware Store',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF1C251D),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              PopupMenuItem<String>(
                value: 'orders',
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE0F2FE),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.local_shipping_outlined,
                        size: 16,
                        color: Color(0xFF0288D1),
                      ),
                    ),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'My Orders',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF1C251D),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const PopupMenuDivider(height: 1),
              PopupMenuItem<String>(
                value: 'profile',
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 13,
                      backgroundColor: const Color(0xFF2E7D32),
                      child: Text(
                        provider.userName.isNotEmpty
                            ? provider.userName[0].toUpperCase()
                            : 'R',
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            l10n.translate('profile'),
                            style: const TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF1C251D),
                            ),
                          ),
                          if (provider.userName.isNotEmpty)
                            Text(
                              provider.userName,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 11,
                                color: Color(0xFF757575),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const PopupMenuDivider(height: 1),
              PopupMenuItem<String>(
                value: 'advanced',
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F5E9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.tune,
                        size: 16,
                        color: Color(0xFF1B5E20),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        l10n.translate('advMode'),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF1C251D),
                        ),
                      ),
                    ),
                    if (provider.isAdvancedMode)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1B5E20),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Text(
                          'ON',
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
              PopupMenuItem<String>(
                value: 'settings',
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(5),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF1F5F9),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.settings_outlined,
                        size: 16,
                        color: Color(0xFF475569),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        l10n.translate('settings'),
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF1C251D),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(width: 4),
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
