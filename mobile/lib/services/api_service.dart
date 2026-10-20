import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/shed_data.dart';
import '../models/ai_advice.dart';

class ApiService {
  // Candidate hosts tried in order for local development.
  // Use the settings modal to enter your computer's LAN IP when testing on a physical phone.
  static const List<String> defaultCandidates = [
    'https://setu-8vh9.onrender.com/api/v1',
    'http://10.0.2.2:8000/api/v1',
    'http://127.0.0.1:8000/api/v1',
    'http://localhost:8000/api/v1',
  ];

  String? _customHost;
  String? _workingBaseUrl;
  String? _authToken;

  void setCustomHost(String? host) {
    if (host != null && host.trim().isNotEmpty) {
      String clean = host.trim();
      if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
        if (clean.contains('.onrender.com') ||
            clean.contains('.vercel.app') ||
            clean.contains('.app') ||
            clean.contains('.com') ||
            clean.contains('.io')) {
          clean = 'https://$clean';
        } else {
          clean = 'http://$clean';
        }
      }
      // Only append :8000 if it is a local IP or localhost without any port specified
      final hostPart = clean.replaceFirst(RegExp(r'^https?://'), '').split('/').first;
      final isLocalOrIp = hostPart.contains('127.0.0.1') ||
          hostPart.contains('localhost') ||
          hostPart.contains('10.0.2.2') ||
          RegExp(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}').hasMatch(hostPart);
      if (isLocalOrIp && !hostPart.contains(':')) {
        clean = clean.replaceFirst(hostPart, '$hostPart:8000');
      }
      // Ensure /api/v1 path
      if (!clean.contains('/api')) {
        clean = '$clean/api/v1';
      } else if (!clean.endsWith('/api/v1')) {
        clean = clean.replaceAll(RegExp(r'/api.*'), '/api/v1');
      }
      _customHost = clean;
    } else {
      _customHost = null;
    }
  }

  List<String> get candidateUrls {
    final list = <String>[];
    if (_workingBaseUrl != null && _workingBaseUrl!.isNotEmpty) {
      list.add(_workingBaseUrl!);
    }
    if (_customHost != null && _customHost!.isNotEmpty && !list.contains(_customHost)) {
      list.add(_customHost!);
    }
    for (final c in defaultCandidates) {
      if (!list.contains(c)) list.add(c);
    }
    return list;
  }

  void setToken(String? token) {
    _authToken = token;
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'X-Device-Key': 'setu-iot-device-key-2026',
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<Map<String, dynamic>?> login(String username, String password) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/auth/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        ).timeout(const Duration(seconds: 8));
        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          _authToken = data['access_token'];
          _workingBaseUrl = base;
          return data;
        }
      } catch (_) {}
    }
    return null;
  }

  Future<Map<String, dynamic>> register({
    required String username,
    required String password,
    required String fullName,
    required String phone,
    required String preferredLanguage,
    String? farmName,
    String? region,
    String? batchId,
    String? dflCapacity,
    String? breed,
  }) async {
    String? serverError;
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/auth/register'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'username': username,
            'password': password,
            'full_name': fullName,
            'phone': phone,
            'preferred_language': preferredLanguage,
            'farm_name': (farmName != null && farmName.isNotEmpty) ? farmName : 'Green Valley Sericulture Farm',
            'region': (region != null && region.isNotEmpty) ? region : 'Local Rearing Shed',
            'batch_id': (batchId != null && batchId.isNotEmpty) ? batchId : 'SERI-2026-M04',
            'dfl_capacity': (dflCapacity != null && dflCapacity.isNotEmpty) ? dflCapacity : '200 DFL',
            'breed': (breed != null && breed.isNotEmpty) ? breed : 'Double Hybrid (FC1 x FC2)',
          }),
        ).timeout(const Duration(seconds: 8));

        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          _authToken = data['access_token'];
          _workingBaseUrl = base;
          return {'success': true, 'data': data};
        } else {
          try {
            final errBody = jsonDecode(res.body);
            serverError = errBody['detail']?.toString() ?? 'Server error (${res.statusCode})';
          } catch (_) {
            serverError = 'Server error (${res.statusCode})';
          }
          if (res.statusCode == 400 || res.statusCode == 422) {
            return {'success': false, 'error': serverError};
          }
        }
      } catch (_) {}
    }
    return {'success': false, 'error': serverError ?? 'Could not connect to backend server'};
  }

  Future<Map<String, dynamic>?> checkFarmer(String identifier) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.get(
          Uri.parse('$base/auth/check-farmer?identifier=${Uri.encodeComponent(identifier)}'),
          headers: {'Content-Type': 'application/json'},
        ).timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          return jsonDecode(res.body);
        }
      } catch (_) {}
    }
    return null;
  }

  Future<Map<String, dynamic>> googleSync({
    required String fullName,
    String? email,
    String? googleId,
    String? phone,
    String? farmName,
    String? region,
    String? batchId,
    String? dflCapacity,
    String? breed,
    String? preferredLanguage,
  }) async {
    String? serverError;
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/auth/google-sync'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'full_name': fullName,
            if (email != null) 'email': email,
            if (googleId != null) 'google_id': googleId,
            if (phone != null) 'phone': phone,
            if (farmName != null) 'farm_name': farmName,
            if (region != null) 'region': region,
            if (batchId != null) 'batch_id': batchId,
            if (dflCapacity != null) 'dfl_capacity': dflCapacity,
            if (breed != null) 'breed': breed,
            if (preferredLanguage != null) 'preferred_language': preferredLanguage,
          }),
        ).timeout(const Duration(seconds: 10));

        if (res.statusCode == 200) {
          final data = jsonDecode(res.body);
          _authToken = data['access_token'];
          _workingBaseUrl = base;
          return {'success': true, 'data': data};
        } else {
          try {
            final errBody = jsonDecode(res.body);
            serverError = errBody['detail']?.toString() ?? 'Server error (${res.statusCode})';
          } catch (_) {
            serverError = 'Server error (${res.statusCode})';
          }
        }
      } catch (_) {}
    }
    return {'success': false, 'error': serverError ?? 'Could not connect to backend server'};
  }

  Future<Map<String, dynamic>?> getMe() async {
    for (final base in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$base/auth/me'), headers: _headers)
            .timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return jsonDecode(res.body);
        }
      } catch (_) {}
    }
    return null;
  }

  Future<Map<String, dynamic>?> updateProfile(Map<String, dynamic> profileData) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.put(
          Uri.parse('$base/auth/profile'),
          headers: _headers,
          body: jsonEncode(profileData),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return jsonDecode(res.body);
        }
      } catch (_) {}
    }
    return null;
  }

  Future<bool> recordTelemetry({
    required String shedId,
    required double temperature,
    required double humidity,
    double? airQuality,
    double? lightLux,
    double? outsideTemp,
    double? outsideHumidity,
  }) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/telemetry/record'),
          headers: _headers,
          body: jsonEncode({
            'shed_id': shedId,
            'temperature': temperature,
            'humidity': humidity,
            'air_quality': airQuality ?? 88.0,
            'light_lux': lightLux ?? 22.0,
            'outside_temperature': outsideTemp,
            'outside_humidity': outsideHumidity,
            'timestamp': DateTime.now().toUtc().toIso8601String(),
          }),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          _workingBaseUrl = base;
          return true;
        }
      } catch (_) {}
    }
    return false;
  }

  Future<Map<String, dynamic>?> setGrowthStage(String shedId, int stage) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/sheds/$shedId/stage/$stage'),
          headers: _headers,
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return jsonDecode(res.body);
        }
      } catch (_) {}
    }
    return null;
  }

  Future<ShedData> getShedStatus(
    String shedId, {
    double? lat,
    double? lon,
    String? region,
  }) async {
    for (final base in candidateUrls) {
      try {
        final queryParams = <String, String>{};
        if (lat != null) queryParams['lat'] = lat.toString();
        if (lon != null) queryParams['lon'] = lon.toString();
        if (region != null && region.isNotEmpty) queryParams['region'] = region;

        final uri = Uri.parse('$base/sheds/$shedId').replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);
        final res = await http.get(uri, headers: _headers)
            .timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return ShedData.fromJson(jsonDecode(res.body));
        }
      } catch (_) {}
    }
    
    // Offline / Mock fallback
    return ShedData(
      shedId: shedId,
      farmName: 'Green Valley Farm',
      region: region ?? 'My Sericulture Shed',
      overallStatus: 'IDEAL',
      statusHeadline: 'Ideal for Silkworms',
      statusSubline: 'Everything is comfortable inside the shed. No action required.',
      currentStage: 4,
      stageName: 'III Instar',
      indoorTemp: 26.2,
      indoorHumidity: 80.0,
      outsideTemp: 28.5,
      outsideHumidity: 55.0,
      actuators: ActuatorStates(cooler: true, fan: true, heater: false, light: true),
      isAutoMode: true,
      tempTarget: 26.0,
      humidityTarget: 80.0,
      airflowTarget: 50.0,
      lightTarget: 35.0,
      lastUpdated: DateTime.now(),
    );
  }

  Future<AIAdvice> getAIExplanation(String shedId, String lang) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$base/ai/explain/$shedId?lang=$lang'), headers: _headers)
            .timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          _workingBaseUrl = base;
          return AIAdvice.fromJson(jsonDecode(res.body));
        }
      } catch (_) {}
    }

    return AIAdvice(
      whyText: 'Outside temperature is high (34.2°C) today, so cooling is activated to keep the shed comfortable for silkworms.',
      currentAction: 'Cooling is ON',
      targetDescription: 'To maintain suitable temperature, humidity, airflow, and light for the current lifecycle phase.',
      bulletPoints: [
        'Outside temperature is high and heat permeates through the shed roof.',
        'Silkworms can get stressed and lose appetite in high heat (>28°C).',
        'Cooling helps maintain a safe environment and prevents cocoon quality loss.'
      ],
      language: lang,
    );
  }

  Future<ShedData?> updateSetpoints(
    String shedId,
    bool isAuto,
    double tempTarget,
    double humTarget, {
    double? airQualityTarget,
    double? lightLuxTarget,
    int? lightBrightness,
  }) async {
    for (final base in candidateUrls) {
      try {
        final payload = <String, dynamic>{
          'is_auto_mode': isAuto,
          'temp_target': tempTarget,
          'humidity_target': humTarget,
        };
        if (airQualityTarget != null) payload['air_quality_target'] = airQualityTarget;
        if (lightLuxTarget != null) payload['light_lux_target'] = lightLuxTarget;
        if (lightBrightness != null) payload['light_brightness'] = lightBrightness;

        final res = await http.post(
          Uri.parse('$base/control/$shedId/setpoints'),
          headers: _headers,
          body: jsonEncode(payload),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return ShedData.fromJson(jsonDecode(res.body));
        }
      } catch (_) {}
    }
    return null;
  }

  Future<bool> manualActuatorOverride(
    String shedId,
    String actuator,
    bool state, {
    int? value,
  }) async {
    for (final base in candidateUrls) {
      try {
        final payload = <String, dynamic>{
          'actuator': actuator,
          'state': state,
        };
        if (value != null) payload['value'] = value;

        final res = await http.post(
          Uri.parse('$base/control/$shedId/override'),
          headers: _headers,
          body: jsonEncode(payload),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) return true;
      } catch (_) {}
    }
    return false;
  }
}

