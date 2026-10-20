import 'dart:async';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/shed_data.dart';
import '../models/growth_stage.dart';
import '../models/ai_advice.dart';
import '../models/live_weather_data.dart';
import '../services/api_service.dart';
import '../services/location_weather_service.dart';

class SetuProvider with ChangeNotifier {
  static const _secureStorage = FlutterSecureStorage();
  final ApiService _apiService = ApiService();
  final LocationWeatherService _weatherService = LocationWeatherService();
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: ['email', 'profile']);

  LiveWeatherData? _liveWeather;
  bool _isLoadingWeather = false;
  String? _weatherErrorMessage;

  Locale _locale = const Locale('en');
  int _currentBottomNavIndex = 0;
  int _currentGrowthStage = 4;
  bool _isAdvancedMode = false;
  bool _isAutoMode = true;
  double _tempSetPoint = 26.0;
  double _humSetPoint = 80.0;
  int _airflowSetPoint = 50;
  int _lightSetPoint = 35;
  double _airQualitySetPoint = 80.0;
  double _lightLuxSetPoint = 25.0;
  int _lightBrightness = 35;

  // Session & Auth state
  bool _isLoggedIn = false;
  bool _isInitialized = false;
  bool _hasCompletedOnboarding = false;
  String? _authToken;
  String _backendHost = 'https://setu-8vh9.onrender.com';
  String? _phoneVerificationId;

  // User Profile Data
  String _userId = 'usr_001';
  String _username = 'ramesh_farmer';
  String _userName = 'Ramesh Gowda';
  String _userPhone = '+91 98450 12345';
  String _batchId = 'SERI-2026-M04';
  String _dflCapacity = '200 DFL';
  String _breed = 'Double Hybrid (FC1 x FC2)';
  String _farmName = 'Green Valley Sericulture Farm';
  String _region = 'My Rearing Shed';
  double? _latitude;
  double? _longitude;
  bool _isDeviceLocation = false;
  final String _experience = '12 Yrs Exp.';

  ShedData _shedData = ShedData(
    shedId: 'shed_01',
    farmName: 'Green Valley Sericulture Farm',
    region: 'My Rearing Shed',
    overallStatus: 'IDEAL',
    statusHeadline: 'Ideal for Silkworms',
    statusSubline: 'Everything is comfortable inside the shed. No action required.',
    currentStage: 4,
    stageName: 'III Instar',
    indoorTemp: 26.2,
    indoorHumidity: 80.0,
    indoorAirQuality: 88.0,
    indoorLightLux: 22.0,
    outsideTemp: 34.2,
    outsideHumidity: 58.0,
    actuators: ActuatorStates(cooler: true, fan: true, heater: false, light: true, lightBrightness: 35),
    isAutoMode: true,
    tempTarget: 26.0,
    humidityTarget: 80.0,
    airflowTarget: 50.0,
    lightTarget: 35.0,
    airQualityTarget: 80.0,
    lightLuxTarget: 25.0,
    photoperiodMode: 'DAY',
    lastUpdated: DateTime.now(),
  );

  AIAdvice _aiAdvice = AIAdvice(
    whyText: 'Outside temperature is high (34.2°C) today, so cooling is activated to keep the shed comfortable for silkworms.',
    currentAction: 'Cooling is ON',
    targetDescription: 'To maintain stable temperature, humidity, airflow, and light for III instar silkworms.',
    bulletPoints: [
      'Outside temperature is high and heat permeates through the shed roof.',
      'Silkworms can get stressed and lose appetite in high heat (>28°C).',
      'Cooling helps maintain a safe environment and prevents cocoon quality loss.'
    ],
    language: 'en',
  );

  SetuProvider() {
    _loadSessionFromPreferences();
  }

  // Getters
  Locale get locale => _locale;
  int get currentBottomNavIndex => _currentBottomNavIndex;
  int get currentGrowthStage => _currentGrowthStage;
  bool get isAdvancedMode => _isAdvancedMode;
  bool get isAutoMode => _isAutoMode;
  double get tempSetPoint => _tempSetPoint;
  double get humSetPoint => _humSetPoint;
  int get airflowSetPoint => _airflowSetPoint;
  int get lightSetPoint => _lightSetPoint;
  double get airQualitySetPoint => _airQualitySetPoint;
  double get lightLuxSetPoint => _lightLuxSetPoint;
  int get lightBrightness => _lightBrightness;
  ShedData get shedData => _shedData;
  AIAdvice get aiAdvice => _aiAdvice;
  GrowthStageModel get currentStageInfo => GrowthStageModel.allStages[_currentGrowthStage - 1];


  bool get isLoggedIn => _isLoggedIn;
  bool get isInitialized => _isInitialized;
  bool get hasCompletedOnboarding => _hasCompletedOnboarding;
  bool get isFirebaseReady => Firebase.apps.isNotEmpty;
  FirebaseAuth? get _firebaseAuthSafe => isFirebaseReady ? FirebaseAuth.instance : null;
  String? get authToken => _authToken;
  String get backendHost => _backendHost;

  String get userId => _userId;
  String get username => _username;
  String get userName => _userName;
  String get userPhone => _userPhone;
  String get batchId => _batchId;
  String get dflCapacity => _dflCapacity;
  String get breed => _breed;
  String get farmName => _farmName;
  String get region => _region;
  double? get latitude => _latitude;
  double? get longitude => _longitude;
  bool get isDeviceLocation => _isDeviceLocation;
  String get experience => _experience;

  // Live Location & Weather Getters
  LiveWeatherData? get liveWeather => _liveWeather;
  bool get isLoadingWeather => _isLoadingWeather;
  String? get weatherErrorMessage => _weatherErrorMessage;

  // --- Persistent Session Management ---
  Future<void> _loadSessionFromPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _hasCompletedOnboarding = prefs.getBool('onboarding_completed') ?? false;
      _isLoggedIn = prefs.getBool('is_logged_in') ?? false;

      // SEC-04: Read token from Keystore / Keychain secure storage
      String? secureToken;
      try {
        secureToken = await _secureStorage.read(key: 'auth_token');
      } catch (_) {}
      _authToken = secureToken ?? prefs.getString('auth_token');
      if (_authToken != null) {
        _apiService.setToken(_authToken);
      }
      // Purge any legacy plaintext credentials cache
      await prefs.remove('registered_farmers_cache');

      final savedHost = prefs.getString('backend_host');
      if (savedHost != null && savedHost.trim().isNotEmpty && !savedHost.contains('127.0.0.1')) {
        _backendHost = savedHost;
      } else {
        _backendHost = 'https://setu-8vh9.onrender.com';
        await prefs.setString('backend_host', _backendHost);
      }
      _apiService.setCustomHost(_backendHost);
      
      _userId = prefs.getString('user_id') ?? _userId;
      _username = prefs.getString('username') ?? _username;
      _userName = prefs.getString('full_name') ?? _userName;
      _userPhone = prefs.getString('phone') ?? _userPhone;
      _farmName = prefs.getString('farm_name') ?? _farmName;
      _region = prefs.getString('region') ?? _region;
      _latitude = prefs.getDouble('latitude');
      _longitude = prefs.getDouble('longitude');
      _isDeviceLocation = prefs.getBool('is_device_location') ?? false;
      _batchId = prefs.getString('batch_id') ?? _batchId;
      _dflCapacity = prefs.getString('dfl_capacity') ?? _dflCapacity;
      _breed = prefs.getString('breed') ?? _breed;
      final lang = prefs.getString('preferred_language') ?? 'en';
      _locale = Locale(lang);

      final firebaseAuth = _firebaseAuthSafe;
      if (firebaseAuth?.currentUser != null) {
        await _applyFirebaseUser(firebaseAuth!.currentUser!);
      }

      if (_isLoggedIn && _authToken != null) {
        _apiService.getMe().then((me) {
          if (me != null) {
            _userName = me['full_name'] ?? _userName;
            _farmName = me['farm_name'] ?? _farmName;
            _region = me['region'] ?? _region;
            if (me['latitude'] != null) _latitude = (me['latitude'] as num).toDouble();
            if (me['longitude'] != null) _longitude = (me['longitude'] as num).toDouble();
            _batchId = me['batch_id'] ?? _batchId;
            _dflCapacity = me['dfl_capacity'] ?? _dflCapacity;
            _breed = me['breed'] ?? _breed;
            final userShed = me['shed_id'] ?? _shedData.shedId;
            _shedData = _shedData.copyWith(
              shedId: userShed,
              farmName: _farmName,
              region: _region,
            );
            notifyListeners();
            refreshLiveWeather();
          }
        });
      }
    } catch (_) {
      // Default fallback
    } finally {
      _isInitialized = true;
      notifyListeners();
      // Fetch live real-time ambient weather for the saved location
      refreshLiveWeather();
    }
  }

  Future<void> completeOnboarding() async {
    _hasCompletedOnboarding = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarding_completed', true);
    notifyListeners();
  }

  String _firebaseMessage(Object error) {
    if (error is FirebaseAuthException) {
      switch (error.code) {
        case 'invalid-phone-number':
          return 'Enter a valid phone number with country code.';
        case 'invalid-verification-code':
          return 'The OTP you entered is invalid.';
        case 'too-many-requests':
          return 'Too many attempts. Please try again later.';
        case 'network-request-failed':
          return 'Network error while contacting Firebase.';
        case 'captcha-check-failed':
          return 'App verification failed. Reopen the app and try again.';
      }
      return error.message ?? 'Firebase authentication failed.';
    }
    return error.toString();
  }

  Future<void> _applyFirebaseUser(
    User user, {
    String? preferredName,
    String? preferredPhone,
  }) async {
    final token = await user.getIdToken().catchError((_) => null) ?? 'firebase_${user.uid}';
    _isLoggedIn = true;
    _authToken = token;
    _apiService.setToken(_authToken);
    _userId = user.uid;
    _username = user.email?.trim().isNotEmpty == true
        ? user.email!
        : (preferredPhone?.trim().isNotEmpty == true ? preferredPhone!.trim() : user.phoneNumber ?? _username);
    _userName = preferredName?.trim().isNotEmpty == true
        ? preferredName!.trim()
        : (user.displayName?.trim().isNotEmpty == true ? user.displayName!.trim() : _userName);
    _userPhone = preferredPhone?.trim().isNotEmpty == true
        ? preferredPhone!.trim()
        : (user.phoneNumber?.trim().isNotEmpty == true ? user.phoneNumber!.trim() : _userPhone);

    // Sync with backend immediately to obtain valid backend JWT and latest profile
    _apiService.googleSync(
      fullName: _userName,
      email: user.email,
      googleId: user.uid,
      phone: _userPhone,
      farmName: _farmName,
      region: _region,
      batchId: _batchId,
      dflCapacity: _dflCapacity,
      breed: _breed,
      preferredLanguage: _locale.languageCode,
    ).then((syncRes) {
      if (syncRes['success'] == true && syncRes['data'] != null) {
        final data = syncRes['data'];
        final userMap = data['user'] ?? {};
        _authToken = data['access_token'];
        _apiService.setToken(_authToken);
        _userId = userMap['id'] ?? _userId;
        _farmName = userMap['farm_name'] ?? _farmName;
        _region = userMap['region'] ?? _region;
        final userShed = userMap['shed_id'] ?? _shedData.shedId;
        _shedData = _shedData.copyWith(
          shedId: userShed,
          farmName: _farmName,
          region: _region,
        );
        _saveSessionToPreferences(token: _authToken!, userMap: userMap);
        notifyListeners();
        _syncTelemetryToBackend();
      }
    });

    await _saveSessionToPreferences(token: _authToken!, userMap: {
      'id': _userId,
      'username': _username,
      'full_name': _userName,
      'phone': _userPhone,
      'farm_name': _farmName,
      'region': _region,
      'batch_id': _batchId,
      'dfl_capacity': _dflCapacity,
      'breed': _breed,
      'preferred_language': _locale.languageCode,
    });
  }

  Future<({bool success, String message, bool codeSent})> startPhoneAuthentication(String phoneNumber) async {
    if (!isFirebaseReady) {
      return (
        success: false,
        message: 'Firebase is not configured yet. Add google-services.json under mobile/android/app and rebuild.',
        codeSent: false,
      );
    }

    final cleanPhone = phoneNumber.trim();
    if (cleanPhone.isEmpty) {
      return (success: false, message: 'Enter your phone number first.', codeSent: false);
    }

    final completer = Completer<({bool success, String message, bool codeSent})>();

    final firebaseAuth = _firebaseAuthSafe;
    if (firebaseAuth == null) {
      return (
        success: false,
        message: 'Firebase is not configured for this platform.',
        codeSent: false,
      );
    }

    await firebaseAuth.verifyPhoneNumber(
      phoneNumber: cleanPhone,
      timeout: const Duration(seconds: 60),
      verificationCompleted: (credential) async {
        final result = await signInWithPhoneCode(code: null, preferredPhone: cleanPhone, credential: credential);
        if (!completer.isCompleted) {
          completer.complete((success: result.success, message: result.message, codeSent: false));
        }
      },
      verificationFailed: (e) {
        if (!completer.isCompleted) {
          completer.complete((success: false, message: _firebaseMessage(e), codeSent: false));
        }
      },
      codeSent: (verificationId, resendToken) {
        _phoneVerificationId = verificationId;
        if (!completer.isCompleted) {
          completer.complete((success: true, message: 'Verification code sent to $cleanPhone.', codeSent: true));
        }
      },
      codeAutoRetrievalTimeout: (verificationId) {
        _phoneVerificationId = verificationId;
      },
    );

    return completer.future;
  }

  Future<({bool success, String message})> signInWithPhoneCode({
    String? code,
    String? preferredName,
    String? preferredPhone,
    PhoneAuthCredential? credential,
  }) async {
    if (!isFirebaseReady) {
      return (success: false, message: 'Firebase is not configured yet.');
    }

    final firebaseAuth = _firebaseAuthSafe;
    if (firebaseAuth == null) {
      return (success: false, message: 'Firebase is not configured for this platform.');
    }

    try {
      final authCredential = credential ?? PhoneAuthProvider.credential(
        verificationId: _phoneVerificationId ?? '',
        smsCode: code?.trim() ?? '',
      );
      final userCredential = await firebaseAuth.signInWithCredential(authCredential);
      if (userCredential.user == null) {
        return (success: false, message: 'Phone authentication did not return a user.');
      }
      await _applyFirebaseUser(
        userCredential.user!,
        preferredName: preferredName,
        preferredPhone: preferredPhone,
      );
      return (success: true, message: 'Phone number verified. Welcome to Setu.');
    } catch (e) {
      return (success: false, message: _firebaseMessage(e));
    }
  }

  User? _pendingGoogleUser;
  User? get pendingGoogleUser => _pendingGoogleUser;

  Future<({bool success, bool needsFarmSetup, String message, String? defaultName, String? email})> signInWithGoogle() async {
    if (!isFirebaseReady) {
      return (
        success: false,
        needsFarmSetup: false,
        message: 'Firebase is not configured yet. Add google-services.json under mobile/android/app and rebuild.',
        defaultName: null,
        email: null,
      );
    }

    final firebaseAuth = _firebaseAuthSafe;
    if (firebaseAuth == null) {
      return (
        success: false,
        needsFarmSetup: false,
        message: 'Firebase is not configured for this platform.',
        defaultName: null,
        email: null,
      );
    }

    try {
      final googleUser = await _googleSignIn.signIn();
      if (googleUser == null) {
        return (
          success: false,
          needsFarmSetup: false,
          message: 'Google sign-in was cancelled.',
          defaultName: null,
          email: null,
        );
      }

      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      final userCredential = await firebaseAuth.signInWithCredential(credential);
      final user = userCredential.user;
      if (user == null) {
        return (
          success: false,
          needsFarmSetup: false,
          message: 'Google sign-in did not return a user.',
          defaultName: null,
          email: null,
        );
      }

      final lookupKey = (user.email?.trim().isNotEmpty == true) ? user.email!.trim().toLowerCase() : user.uid;
      final check = await _apiService.checkFarmer(lookupKey);

      if (check != null && check['exists'] == true && check['has_profile'] == true) {
        // Existing registered farmer with completed profile -> sync immediately
        final syncRes = await _apiService.googleSync(
          fullName: user.displayName ?? '',
          email: user.email,
          googleId: user.uid,
          preferredLanguage: _locale.languageCode,
        );
        if (syncRes['success'] == true && syncRes['data'] != null) {
          final data = syncRes['data'];
          final userMap = data['user'] ?? {};
          _authToken = data['access_token'];
          _apiService.setToken(_authToken);
          _isLoggedIn = true;
          _userId = userMap['id'] ?? user.uid;
          _username = userMap['username'] ?? lookupKey;
          _userName = userMap['full_name'] ?? (user.displayName ?? 'Farmer');
          _userPhone = userMap['phone'] ?? '';
          _farmName = userMap['farm_name'] ?? '';
          _region = userMap['region'] ?? 'Local Rearing Shed';
          _batchId = userMap['batch_id'] ?? '';
          _dflCapacity = userMap['dfl_capacity'] ?? '';
          _breed = userMap['breed'] ?? 'Double Hybrid (FC1 x FC2)';
          await _saveSessionToPreferences(token: _authToken!, userMap: userMap);
          notifyListeners();
          return (
            success: true,
            needsFarmSetup: false,
            message: 'Welcome back, $_userName!',
            defaultName: _userName,
            email: user.email,
          );
        }
      }

      // New farmer or profile incomplete -> Needs farm data input
      _pendingGoogleUser = user;
      return (
        success: true,
        needsFarmSetup: true,
        message: 'Please complete your farm details.',
        defaultName: user.displayName ?? '',
        email: user.email,
      );
    } catch (e) {
      return (
        success: false,
        needsFarmSetup: false,
        message: _firebaseMessage(e),
        defaultName: null,
        email: null,
      );
    }
  }

  Future<({bool success, String message})> completeGoogleFarmSetup({
    required String fullName,
    required String phone,
    required String farmName,
    required String batchId,
    required String dflCapacity,
    String? region,
    String? breed,
  }) async {
    final user = _pendingGoogleUser ?? _firebaseAuthSafe?.currentUser;
    final email = user?.email;
    final googleId = user?.uid;

    final syncRes = await _apiService.googleSync(
      fullName: fullName.trim(),
      email: email,
      googleId: googleId,
      phone: phone.trim(),
      farmName: farmName.trim(),
      batchId: batchId.trim(),
      dflCapacity: dflCapacity.trim(),
      region: (region != null && region.trim().isNotEmpty) ? region.trim() : 'Local Rearing Shed',
      breed: (breed != null && breed.trim().isNotEmpty) ? breed.trim() : 'Double Hybrid (FC1 x FC2)',
      preferredLanguage: _locale.languageCode,
    );

    if (syncRes['success'] == true && syncRes['data'] != null) {
      final data = syncRes['data'];
      final userMap = data['user'] ?? {};
      _authToken = data['access_token'];
      _apiService.setToken(_authToken);
      _isLoggedIn = true;
      _userId = userMap['id'] ?? (googleId ?? 'usr_google');
      _username = userMap['username'] ?? (email ?? phone.trim());
      _userName = userMap['full_name'] ?? fullName.trim();
      _userPhone = userMap['phone'] ?? phone.trim();
      _farmName = userMap['farm_name'] ?? farmName.trim();
      _region = userMap['region'] ?? 'Local Rearing Shed';
      _batchId = userMap['batch_id'] ?? batchId.trim();
      _dflCapacity = userMap['dfl_capacity'] ?? dflCapacity.trim();
      _breed = userMap['breed'] ?? 'Double Hybrid (FC1 x FC2)';
      _pendingGoogleUser = null;

      await _saveSessionToPreferences(token: _authToken!, userMap: userMap);
      notifyListeners();
      return (success: true, message: 'Welcome $_userName! Farm successfully registered.');
    }

    final err = syncRes['error']?.toString() ?? 'Failed to enroll farm on server.';
    return (success: false, message: err);
  }

  /// Refreshes live ambient weather from Open-Meteo for the current region/coordinates
  Future<void> refreshLiveWeather({bool requestGps = false}) async {
    _isLoadingWeather = true;
    _weatherErrorMessage = null;
    notifyListeners();

    try {
      if (requestGps || _latitude == null || _longitude == null) {
        final liveLoc = await _weatherService.resolveLiveLocation();
        if (liveLoc != null) {
          _latitude = liveLoc['lat'];
          _longitude = liveLoc['lon'];
          _region = liveLoc['locationName'];
          _isDeviceLocation = liveLoc['isGps'] ?? false;
        }
      }

      final weather = await _weatherService.fetchLiveWeather(
        latitude: _latitude,
        longitude: _longitude,
        customLocationName: (_region.isNotEmpty && _region != 'My Rearing Shed') ? _region : null,
      );
      _liveWeather = weather;
      _latitude = weather.latitude;
      _longitude = weather.longitude;
      _region = weather.locationName;
      _isDeviceLocation = weather.isGps;

      // Sync detected GPS location with backend profile so Admin Web and API stay in sync
      if (_isLoggedIn && _latitude != null && _longitude != null) {
        _apiService.updateProfile({
          'region': _region,
          'latitude': _latitude,
          'longitude': _longitude,
        });
      }

      // Sync real-time microclimate and IoT sensor readings from backend
      if (_isLoggedIn) {
        try {
          final serverShed = await _apiService.getShedStatus(
            _shedData.shedId,
            lat: _latitude,
            lon: _longitude,
            region: _region,
          );
          _shedData = serverShed.copyWith(
            outsideTemp: weather.temperature,
            outsideHumidity: weather.humidity,
            region: weather.locationName,
          );
        } catch (_) {
          _shedData = _shedData.copyWith(
            outsideTemp: weather.temperature,
            outsideHumidity: weather.humidity,
            region: weather.locationName,
          );
        }
      } else {
        _shedData = _shedData.copyWith(
          outsideTemp: weather.temperature,
          outsideHumidity: weather.humidity,
          region: weather.locationName,
        );
      }
      _updateAdviceForWeather();
      _syncTelemetryToBackend();
    } catch (e) {
      _weatherErrorMessage = e.toString();
    } finally {
      _isLoadingWeather = false;
      notifyListeners();
    }
  }

  /// Sets location manually (city, town, district, country) anywhere worldwide
  Future<({bool success, String message})> setLocationManual(String locationName) async {
    final clean = locationName.trim();
    if (clean.isEmpty) {
      return (success: false, message: 'Please enter a valid location name.');
    }

    _isLoadingWeather = true;
    notifyListeners();

    try {
      final geo = await _weatherService.geocodeAddress(clean);
      if (geo != null) {
        _region = geo['region'] ?? clean;
        _latitude = geo['lat'];
        _longitude = geo['lon'];
        _isDeviceLocation = false;
      } else {
        _region = clean;
        _latitude = null;
        _longitude = null;
        _isDeviceLocation = false;
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('region', _region);
      if (_latitude != null) {
        await prefs.setDouble('latitude', _latitude!);
      } else {
        await prefs.remove('latitude');
      }
      if (_longitude != null) {
        await prefs.setDouble('longitude', _longitude!);
      } else {
        await prefs.remove('longitude');
      }
      await prefs.setBool('is_device_location', false);

      // Sync with backend if logged in
      _apiService.updateProfile({
        'region': _region,
        'latitude': _latitude,
        'longitude': _longitude,
      });

      // Update weather immediately
      await refreshLiveWeather();
      return (success: true, message: 'Location set to $_region');
    } catch (e) {
      return (success: false, message: 'Error setting location: $e');
    } finally {
      _isLoadingWeather = false;
      notifyListeners();
    }
  }

  /// Requests phone GPS permission and updates location from device GPS
  Future<({bool success, String message})> detectAndSetDeviceLocation() async {
    _isLoadingWeather = true;
    notifyListeners();

    try {
      final res = await _weatherService.acquireDeviceLocation();
      if (!res['success']) {
        final String errMsg = res['error']?.toString() ?? 'Could not detect device location.';
        return (success: false, message: errMsg);
      }

      _latitude = res['lat'] as double;
      _longitude = res['lon'] as double;
      _region = res['region'] as String;
      _isDeviceLocation = true;

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('region', _region);
      await prefs.setDouble('latitude', _latitude!);
      await prefs.setDouble('longitude', _longitude!);
      await prefs.setBool('is_device_location', true);

      // Sync with backend
      _apiService.updateProfile({
        'region': _region,
        'latitude': _latitude,
        'longitude': _longitude,
      });

      // Fetch weather for acquired coordinates
      await refreshLiveWeather();
      return (success: true, message: 'Device location updated: $_region');
    } catch (e) {
      return (success: false, message: 'Failed to obtain GPS: $e');
    } finally {
      _isLoadingWeather = false;
      notifyListeners();
    }
  }

  void _updateAdviceForWeather() {
    if (_liveWeather != null) {
      final t = _liveWeather!.temperature;
      final h = _liveWeather!.humidity.toInt();
      final loc = _liveWeather!.locationName;
      final isCoolerOn = _shedData.actuators.cooler;
      final isHeaterOn = _shedData.actuators.heater;

      _aiAdvice = AIAdvice(
        whyText: 'Live outside weather at $loc is $t°C, $h% RH (${_liveWeather!.condition}). ${_liveWeather!.silkwormAdvisory}',
        currentAction: isCoolerOn ? 'Cooling is ON' : (isHeaterOn ? 'Heating is ON' : 'Microclimate Balanced'),
        targetDescription: 'Maintaining optimal conditions for ${currentStageInfo.name} silkworms.',
        bulletPoints: [
          'Outside temperature is currently $t°C with $h% relative humidity.',
          _liveWeather!.silkwormAdvisory,
          'Setu dynamically accounts for outside microclimate to protect rearing trays.',
        ],
        language: _locale.languageCode,
      );
    }
  }

  Future<void> setBackendHost(String host) async {
    _backendHost = host.trim();
    _apiService.setCustomHost(_backendHost);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('backend_host', _backendHost);
    notifyListeners();
  }

  Future<void> _saveSessionToPreferences({
    required String token,
    required Map<String, dynamic> userMap,
  }) async {
    // SEC-04: Persist sensitive token in Android Keystore / iOS Keychain
    try {
      await _secureStorage.write(key: 'auth_token', value: token);
    } catch (_) {}

    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_logged_in', true);
    await prefs.setString('auth_token', token);
    await prefs.setString('user_id', userMap['id'] ?? _userId);
    await prefs.setString('username', userMap['username'] ?? _username);
    await prefs.setString('full_name', userMap['full_name'] ?? _userName);
    await prefs.setString('phone', userMap['phone'] ?? _userPhone);
    await prefs.setString('farm_name', userMap['farm_name'] ?? _farmName);
    await prefs.setString('region', userMap['region'] ?? _region);
    await prefs.setString('batch_id', userMap['batch_id'] ?? _batchId);
    await prefs.setString('dfl_capacity', userMap['dfl_capacity'] ?? _dflCapacity);
    await prefs.setString('breed', userMap['breed'] ?? _breed);
    await prefs.setString('preferred_language', userMap['preferred_language'] ?? _locale.languageCode);
  }

  // --- Authenticated Server Login (SEC-03 & SEC-04 Hardened) ---
  Future<bool> login(String uname, String pwd) async {
    final cleanUname = uname.trim();
    final cleanPwd = pwd.trim();
    if (cleanUname.isEmpty || cleanPwd.isEmpty) return false;

    final res = await _apiService.login(cleanUname, cleanPwd);
    if (res != null && res['access_token'] != null) {
      _authToken = res['access_token'];
      final user = res['user'] ?? {};
      _isLoggedIn = true;
      _userId = user['id'] ?? _userId;
      _username = user['username'] ?? cleanUname;
      _userName = user['full_name'] ?? _userName;
      _userPhone = user['phone'] ?? _userPhone;
      _farmName = user['farm_name'] ?? _farmName;
      _region = user['region'] ?? _region;
      _batchId = user['batch_id'] ?? _batchId;
      _dflCapacity = user['dfl_capacity'] ?? _dflCapacity;
      _breed = user['breed'] ?? _breed;
      if (user['preferred_language'] != null) {
        _locale = Locale(user['preferred_language']);
      }
      
      await _saveSessionToPreferences(token: _authToken!, userMap: user);
      notifyListeners();
      return true;
    }

    _isLoggedIn = false;
    _authToken = null;
    notifyListeners();
    return false;
  }

  Future<({bool success, String? message})> register({
    required String uname,
    required String pwd,
    required String fullName,
    required String phone,
    String? farmName,
    String? region,
    String? batchId,
    String? dflCapacity,
    String? breed,
  }) async {
    final cleanUname = uname.trim();
    final cleanPwd = pwd.trim();
    if (cleanUname.isEmpty || cleanPwd.isEmpty) {
      return (success: false, message: 'Please provide both username and password.');
    }

    final res = await _apiService.register(
      username: cleanUname,
      password: cleanPwd,
      fullName: fullName.trim(),
      phone: phone.trim(),
      preferredLanguage: _locale.languageCode,
      farmName: farmName?.trim(),
      region: region?.trim(),
      batchId: batchId?.trim(),
      dflCapacity: dflCapacity?.trim(),
      breed: breed?.trim(),
    );

    if (res['success'] == true && res['data'] != null) {
      final data = res['data'];
      _authToken = data['access_token'];
      final user = data['user'] ?? {};
      _isLoggedIn = true;
      _userId = user['id'] ?? _userId;
      _username = user['username'] ?? cleanUname;
      _userName = user['full_name'] ?? fullName;
      _userPhone = user['phone'] ?? phone;
      _farmName = user['farm_name'] ?? _farmName;
      _region = user['region'] ?? _region;
      _batchId = user['batch_id'] ?? _batchId;
      _dflCapacity = user['dfl_capacity'] ?? _dflCapacity;
      _breed = user['breed'] ?? _breed;
      if (user['preferred_language'] != null) {
        _locale = Locale(user['preferred_language']);
      }

      await _saveSessionToPreferences(token: _authToken!, userMap: user);
      notifyListeners();
      return (success: true, message: 'Welcome $_userName! Farm registered successfully.');
    }

    final errorMsg = res['error']?.toString();
    return (success: false, message: errorMsg ?? 'Could not register account. Please check network connection.');
  }

  Future<void> logout() async {
    _isLoggedIn = false;
    _authToken = null;
    _apiService.setToken(null);
    try {
      await _secureStorage.delete(key: 'auth_token');
    } catch (_) {}
    final firebaseAuth = _firebaseAuthSafe;
    if (firebaseAuth != null) {
      await firebaseAuth.signOut();
      await _googleSignIn.signOut();
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('is_logged_in');
    await prefs.remove('auth_token');
    await prefs.remove('registered_farmers_cache');
    notifyListeners();
  }

  void updateUserProfile({
    required String name,
    required String phone,
    required String batch,
    required String capacity,
    String? farmName,
    String? region,
  }) => updateFarmerProfile(name: name, phone: phone, batch: batch, capacity: capacity, farmName: farmName, region: region);

  void updateFarmerProfile({
    required String name,
    required String phone,
    required String batch,
    required String capacity,
    String? farmName,
    String? region,
  }) {
    _userName = name;
    _userPhone = phone;
    _batchId = batch;
    _dflCapacity = capacity;
    if (farmName != null && farmName.trim().isNotEmpty) _farmName = farmName.trim();
    if (region != null && region.trim().isNotEmpty) _region = region.trim();

    SharedPreferences.getInstance().then((prefs) {
      prefs.setString('full_name', name);
      prefs.setString('phone', phone);
      prefs.setString('batch_id', batch);
      prefs.setString('dfl_capacity', capacity);
      if (farmName != null && farmName.trim().isNotEmpty) prefs.setString('farm_name', _farmName);
      if (region != null && region.trim().isNotEmpty) prefs.setString('region', _region);
    });

    _shedData = _shedData.copyWith(
      farmName: _farmName,
      region: _region,
    );

    _apiService.updateProfile({
      'full_name': name,
      'phone': phone,
      'batch_id': batch,
      'dfl_capacity': capacity,
      if (farmName != null && farmName.trim().isNotEmpty) 'farm_name': _farmName,
      if (region != null && region.trim().isNotEmpty) 'region': _region,
      'current_stage': _currentGrowthStage,
    });

    _syncTelemetryToBackend();
    notifyListeners();
  }

  void setLocale(Locale loc) {
    _locale = loc;
    SharedPreferences.getInstance().then((prefs) {
      prefs.setString('preferred_language', loc.languageCode);
    });
    notifyListeners();
  }

  void setBottomNavIndex(int index) {
    _currentBottomNavIndex = index;
    notifyListeners();
  }

  void toggleAdvancedMode() {
    _isAdvancedMode = !_isAdvancedMode;
    notifyListeners();
  }

  void _syncTargetsIntoShedData({
    bool? isAutoMode,
    ActuatorStates? actuators,
  }) {
    final auto = isAutoMode ?? _isAutoMode;
    final curTemp = _shedData.indoorTemp;
    final curHum = _shedData.indoorHumidity;
    final curAqi = _shedData.indoorAirQuality;
    final curLux = _shedData.indoorLightLux;

    String overallStatus = 'IDEAL';
    String headline = 'Ideal for Silkworms';
    String subline = 'Microclimate is stable and within target boundaries.';

    bool cooler = actuators?.cooler ?? _shedData.actuators.cooler;
    bool heater = actuators?.heater ?? _shedData.actuators.heater;
    bool fan = actuators?.fan ?? _shedData.actuators.fan;
    bool light = actuators?.light ?? _shedData.actuators.light;
    int brightness = actuators?.lightBrightness ?? _lightBrightness;

    if (auto) {
      // Dynamic precaution evaluation against user setpoints
      if (curTemp > _tempSetPoint + 0.5) {
        overallStatus = 'TOO_WARM';
        headline = 'Too Warm — Cooling Active';
        subline = 'Indoor temperature (${curTemp.toStringAsFixed(1)}°C) exceeds target (${_tempSetPoint.toStringAsFixed(1)}°C). Automated cooling active.';
        cooler = true;
        heater = false;
        fan = true;
      } else if (curTemp < _tempSetPoint - 0.5) {
        overallStatus = 'TOO_COOL';
        headline = 'Too Cool — Shed Heater ON';
        subline = 'Indoor temperature (${curTemp.toStringAsFixed(1)}°C) is below target (${_tempSetPoint.toStringAsFixed(1)}°C). Heating activated safely.';
        heater = true;
        cooler = false;
        fan = false;
      } else if (curHum > _humSetPoint + 5.0) {
        overallStatus = 'HIGH_HUMIDITY';
        headline = 'High Humidity — Exhaust Active';
        subline = 'Indoor humidity (${curHum.toInt()}%) is above target (${_humSetPoint.toInt()}%). Exhaust fan active.';
        fan = true;
        cooler = false;
        heater = false;
      } else if (curHum < _humSetPoint - 5.0) {
        overallStatus = 'LOW_HUMIDITY';
        headline = 'Low Humidity — Foggers Active';
        subline = 'Indoor humidity (${curHum.toInt()}%) is below target (${_humSetPoint.toInt()}%). Fogger humidification running.';
        fan = false;
        cooler = false;
        heater = false;
      } else if (curAqi < _airQualitySetPoint) {
        overallStatus = 'AIR_LOW';
        headline = 'Air Quality Low — Ventilation Active';
        subline = 'Air quality is ${curAqi.toInt()}% (target >= ${_airQualitySetPoint.toInt()}%). Exhaust fan active.';
        fan = true;
      } else {
        overallStatus = 'IDEAL';
        headline = 'Ideal for Silkworms';
        subline = 'Microclimate is comfortable at target (${_tempSetPoint.toStringAsFixed(1)}°C • ${_humSetPoint.toInt()}% RH).';
        cooler = false;
        heater = false;
        fan = false;
      }
      light = curLux >= 5.0;
    }

    _shedData = _shedData.copyWith(
      currentStage: _currentGrowthStage,
      stageName: currentStageInfo.name,
      overallStatus: overallStatus,
      statusHeadline: headline,
      statusSubline: subline,
      actuators: ActuatorStates(
        cooler: cooler,
        heater: heater,
        fan: fan,
        light: light,
        lightBrightness: brightness,
      ),
      isAutoMode: auto,
      tempTarget: _tempSetPoint,
      humidityTarget: _humSetPoint,
      airflowTarget: _airflowSetPoint.toDouble(),
      lightTarget: _lightSetPoint.toDouble(),
      airQualityTarget: _airQualitySetPoint,
      lightLuxTarget: _lightLuxSetPoint,
      lastUpdated: DateTime.now(),
    );

    // Update AI advice to match active precautions
    if (cooler) {
      _aiAdvice = _aiAdvice.copyWith(
        currentAction: 'Cooling is ON (Target: ${_tempSetPoint.toStringAsFixed(1)}°C)',
        whyText: 'Shed temperature is ${curTemp.toStringAsFixed(1)}°C, which is above your setpoint of ${_tempSetPoint.toStringAsFixed(1)}°C. Coolers are actively running to lower temperature.',
        targetDescription: 'Targeting ${_tempSetPoint.toStringAsFixed(1)}°C and ${_humSetPoint.toInt()}% humidity for healthy growth.',
      );
    } else if (heater) {
      _aiAdvice = _aiAdvice.copyWith(
        currentAction: 'Heating is ON (Target: ${_tempSetPoint.toStringAsFixed(1)}°C)',
        whyText: 'Shed temperature is ${curTemp.toStringAsFixed(1)}°C, below your setpoint of ${_tempSetPoint.toStringAsFixed(1)}°C. Heater is running to maintain warmth.',
        targetDescription: 'Targeting ${_tempSetPoint.toStringAsFixed(1)}°C and ${_humSetPoint.toInt()}% humidity for healthy growth.',
      );
    } else if (fan) {
      _aiAdvice = _aiAdvice.copyWith(
        currentAction: 'Ventilation Fan is ON',
        whyText: curHum > _humSetPoint + 5.0
            ? 'Humidity is ${curHum.toInt()}% (target ${_humSetPoint.toInt()}%). Exhaust fan is running to remove excess moisture.'
            : 'Exhaust fan is active to improve air quality to >=${_airQualitySetPoint.toInt()}%.',
        targetDescription: 'Maintaining healthy airflow and safe CO₂ levels in the shed.',
      );
    } else {
      _aiAdvice = _aiAdvice.copyWith(
        currentAction: 'Microclimate Optimal',
        whyText: 'Shed is currently at ${curTemp.toStringAsFixed(1)}°C and ${curHum.toInt()}% humidity, within your target ranges.',
        targetDescription: 'Targeting ${_tempSetPoint.toStringAsFixed(1)}°C and ${_humSetPoint.toInt()}% humidity.',
      );
    }
  }

  void _applySimpleStagePreset() {
    final preset = currentStageInfo;
    _tempSetPoint = preset.tempTarget;
    _humSetPoint = preset.humidityTarget;
    _airflowSetPoint = preset.airflowPercent;
    _lightSetPoint = preset.lightPercent;
    _airQualitySetPoint = 80.0;
    _lightLuxSetPoint = _currentGrowthStage == 5 ? 10.0 : 25.0;
    _lightBrightness = _currentGrowthStage == 5 ? 15 : 35;

    _syncTargetsIntoShedData(
      isAutoMode: true,
      actuators: ActuatorStates(
        cooler: _shedData.actuators.cooler,
        fan: preset.airflowPercent >= 50,
        heater: _shedData.actuators.heater,
        light: true,
        lightBrightness: _lightBrightness,
      ),
    );
  }

  void setAutoMode(bool auto) {
    _isAutoMode = auto;
    if (auto) {
      _applySimpleStagePreset();
    } else {
      _syncTargetsIntoShedData(isAutoMode: false);
    }
    _apiService.updateSetpoints(
      _shedData.shedId,
      auto,
      _tempSetPoint,
      _humSetPoint,
      airQualityTarget: _airQualitySetPoint,
      lightLuxTarget: _lightLuxSetPoint,
      lightBrightness: _lightBrightness,
    );
    notifyListeners();
  }

  void adjustTempSetPoint(double delta) {
    _tempSetPoint = (_tempSetPoint + delta).clamp(18.0, 35.0);
    _tempSetPoint = double.parse(_tempSetPoint.toStringAsFixed(1));
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    _apiService.updateSetpoints(_shedData.shedId, _isAutoMode, _tempSetPoint, _humSetPoint);
    notifyListeners();
  }

  void adjustHumSetPoint(double delta) {
    _humSetPoint = (_humSetPoint + delta).clamp(40.0, 95.0);
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    _apiService.updateSetpoints(_shedData.shedId, _isAutoMode, _tempSetPoint, _humSetPoint);
    notifyListeners();
  }

  void adjustAirflowSetPoint(int delta) {
    _airflowSetPoint = (_airflowSetPoint + delta).clamp(10, 100);
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    notifyListeners();
  }

  void adjustLightSetPoint(int delta) {
    _lightSetPoint = (_lightSetPoint + delta).clamp(0, 100);
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    notifyListeners();
  }

  void adjustAirQualitySetPoint(double delta) {
    _airQualitySetPoint = (_airQualitySetPoint + delta).clamp(50.0, 95.0);
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    _apiService.updateSetpoints(
      _shedData.shedId,
      _isAutoMode,
      _tempSetPoint,
      _humSetPoint,
      airQualityTarget: _airQualitySetPoint,
    );
    notifyListeners();
  }

  void adjustLightLuxSetPoint(double delta) {
    _lightLuxSetPoint = (_lightLuxSetPoint + delta).clamp(5.0, 80.0);
    _syncTargetsIntoShedData(isAutoMode: _isAutoMode);
    _apiService.updateSetpoints(
      _shedData.shedId,
      _isAutoMode,
      _tempSetPoint,
      _humSetPoint,
      lightLuxTarget: _lightLuxSetPoint,
    );
    notifyListeners();
  }

  void setLightBrightness(int brightness) {
    _lightBrightness = brightness.clamp(0, 100);
    final isLit = _lightBrightness > 0;
    _syncTargetsIntoShedData(
      isAutoMode: false,
      actuators: ActuatorStates(
        cooler: _shedData.actuators.cooler,
        fan: _shedData.actuators.fan,
        heater: _shedData.actuators.heater,
        light: isLit,
        lightBrightness: _lightBrightness,
      ),
    );
    _apiService.manualActuatorOverride(
      _shedData.shedId,
      'light_brightness',
      isLit,
      value: _lightBrightness,
    );
    notifyListeners();
  }

  void setGrowthStage(int stage) {
    if (stage >= 1 && stage <= GrowthStageModel.allStages.length) {
      _currentGrowthStage = stage;
      if (_isAutoMode) {
        _applySimpleStagePreset();
      } else {
        _syncTargetsIntoShedData(isAutoMode: false);
      }
      _apiService.setGrowthStage(_shedData.shedId, stage);
      _apiService.updateProfile({'current_stage': stage});
      _syncTelemetryToBackend();
      notifyListeners();
    }
  }

  Future<void> _syncTelemetryToBackend() async {
    if (!_isLoggedIn) return;
    try {
      await _apiService.recordTelemetry(
        shedId: _shedData.shedId,
        temperature: _shedData.indoorTemp,
        humidity: _shedData.indoorHumidity,
        airQuality: _shedData.indoorAirQuality,
        lightLux: _shedData.indoorLightLux,
        outsideTemp: _shedData.outsideTemp,
        outsideHumidity: _shedData.outsideHumidity,
      );
    } catch (_) {}
  }

  void toggleActuator(String actuator) {
    if (_isAutoMode) return;

    bool nextCooler = _shedData.actuators.cooler;
    bool nextFan = _shedData.actuators.fan;
    bool nextHeater = _shedData.actuators.heater;
    bool nextLight = _shedData.actuators.light;
    int nextBrightness = _shedData.actuators.lightBrightness;

    if (actuator == 'cooler') {
      nextCooler = !nextCooler;
      if (nextCooler) nextHeater = false;
    } else if (actuator == 'heater') {
      nextHeater = !nextHeater;
      if (nextHeater) nextCooler = false;
    } else if (actuator == 'fan') {
      nextFan = !nextFan;
    } else if (actuator == 'light') {
      nextLight = !nextLight;
      nextBrightness = nextLight ? (_lightBrightness > 0 ? _lightBrightness : 35) : 0;
      _lightBrightness = nextBrightness;
    }

    _syncTargetsIntoShedData(
      isAutoMode: false,
      actuators: ActuatorStates(
        cooler: nextCooler,
        fan: nextFan,
        heater: nextHeater,
        light: nextLight,
        lightBrightness: nextBrightness,
      ),
    );

    final nextState = actuator == 'cooler'
        ? nextCooler
        : actuator == 'heater'
            ? nextHeater
            : actuator == 'light'
                ? nextLight
                : nextFan;
    _apiService.manualActuatorOverride(_shedData.shedId, actuator, nextState);
    _syncTelemetryToBackend();
    notifyListeners();
  }

  void applyScenario(String scenario) {
    if (scenario == 'normal') {
      _shedData = ShedData(
        shedId: _shedData.shedId,
        farmName: _shedData.farmName,
        region: _shedData.region,
        overallStatus: 'IDEAL',
        statusHeadline: 'Ideal for Silkworms',
        statusSubline: 'Everything is comfortable inside the shed. No action required.',
        currentStage: _currentGrowthStage,
        stageName: currentStageInfo.name,
        indoorTemp: 26.2,
        indoorHumidity: 74.0,
        indoorAirQuality: 88.0,
        indoorLightLux: 24.0,
        outsideTemp: 34.2,
        outsideHumidity: 58.0,
        actuators: ActuatorStates(cooler: true, fan: false, heater: false, light: true, lightBrightness: 35),
        isAutoMode: true,
        tempTarget: 26.0,
        humidityTarget: 75.0,
        airQualityTarget: 80.0,
        lightLuxTarget: 25.0,
        photoperiodMode: 'DAY',
        lastUpdated: DateTime.now(),
      );
    } else if (scenario == 'hot') {
      _shedData = ShedData(
        shedId: _shedData.shedId,
        farmName: _shedData.farmName,
        region: _shedData.region,
        overallStatus: 'TOO_WARM',
        statusHeadline: 'Too Warm — Cooling Maximum',
        statusSubline: 'Shed temperature is rising (28.6°C). Automated cooling boosted.',
        currentStage: _currentGrowthStage,
        stageName: currentStageInfo.name,
        indoorTemp: 28.6,
        indoorHumidity: 68.0,
        indoorAirQuality: 82.0,
        indoorLightLux: 28.0,
        outsideTemp: 37.8,
        outsideHumidity: 45.0,
        actuators: ActuatorStates(cooler: true, fan: true, heater: false, light: true, lightBrightness: 25),
        isAutoMode: true,
        tempTarget: 26.0,
        humidityTarget: 75.0,
        airQualityTarget: 80.0,
        lightLuxTarget: 25.0,
        photoperiodMode: 'DAY',
        lastUpdated: DateTime.now(),
      );
    } else if (scenario == 'cold') {
      _shedData = ShedData(
        shedId: _shedData.shedId,
        farmName: _shedData.farmName,
        region: _shedData.region,
        overallStatus: 'TOO_COOL',
        statusHeadline: 'Too Cool — Shed Heater ON',
        statusSubline: 'Night chill detected (20.4°C). Heating activated safely.',
        currentStage: _currentGrowthStage,
        stageName: currentStageInfo.name,
        indoorTemp: 20.4,
        indoorHumidity: 82.0,
        indoorAirQuality: 85.0,
        indoorLightLux: 2.0,
        outsideTemp: 16.5,
        outsideHumidity: 88.0,
        actuators: ActuatorStates(cooler: false, fan: false, heater: true, light: false, lightBrightness: 0),
        isAutoMode: true,
        tempTarget: 26.0,
        humidityTarget: 75.0,
        airQualityTarget: 80.0,
        lightLuxTarget: 25.0,
        photoperiodMode: 'NIGHT',
        lastUpdated: DateTime.now(),
      );
    } else if (scenario == 'stale_air') {
      // Research scenario: CO2 accumulation exceeds 1% / low air quality (< 80%)
      _shedData = ShedData(
        shedId: _shedData.shedId,
        farmName: _shedData.farmName,
        region: _shedData.region,
        overallStatus: 'AIR_LOW',
        statusHeadline: 'Air Quality Low — Ventilation Active',
        statusSubline: 'Air quality dropped to 64% (target >= 80%). Exhaust fan activated for fresh aeration.',
        currentStage: _currentGrowthStage,
        stageName: currentStageInfo.name,
        indoorTemp: 26.0,
        indoorHumidity: 76.0,
        indoorAirQuality: 64.0,
        indoorLightLux: 22.0,
        outsideTemp: 32.0,
        outsideHumidity: 60.0,
        actuators: ActuatorStates(cooler: false, fan: true, heater: false, light: true, lightBrightness: 35),
        isAutoMode: true,
        tempTarget: 26.0,
        humidityTarget: 75.0,
        airQualityTarget: 80.0,
        lightLuxTarget: 25.0,
        photoperiodMode: 'DAY',
        lastUpdated: DateTime.now(),
      );
    } else if (scenario == 'night_mode') {
      // Research scenario: 8h photoperiod night rest (< 5 Lux)
      _shedData = ShedData(
        shedId: _shedData.shedId,
        farmName: _shedData.farmName,
        region: _shedData.region,
        overallStatus: 'IDEAL',
        statusHeadline: 'Night Rest Photoperiod (<5 Lux)',
        statusSubline: 'Dark resting cycle active (22:00–06:00). Silkworms resting peacefully.',
        currentStage: _currentGrowthStage,
        stageName: currentStageInfo.name,
        indoorTemp: 24.8,
        indoorHumidity: 75.0,
        indoorAirQuality: 90.0,
        indoorLightLux: 2.0,
        outsideTemp: 22.0,
        outsideHumidity: 70.0,
        actuators: ActuatorStates(cooler: false, fan: false, heater: false, light: false, lightBrightness: 0),
        isAutoMode: true,
        tempTarget: 26.0,
        humidityTarget: 75.0,
        airQualityTarget: 80.0,
        lightLuxTarget: 25.0,
        photoperiodMode: 'NIGHT',
        lastUpdated: DateTime.now(),
      );
    }
    notifyListeners();
  }

}
