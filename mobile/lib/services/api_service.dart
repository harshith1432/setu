import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/shed_data.dart';
import '../models/ai_advice.dart';

class ApiService {
  // Candidate hosts tried in order:
  // 1. Current PC Wi-Fi IP (10.38.239.10:8000) for real mobile phone connection
  // 2. Android emulator host (10.0.2.2:8000)
  // 3. Localhost (127.0.0.1:8000) for desktop/browser
  // 4. Previous Wi-Fi IP fallback (192.168.0.116:8000)
  static const List<String> defaultCandidates = [
    'http://10.38.239.10:8000/api/v1',
    'http://10.0.2.2:8000/api/v1',
    'http://127.0.0.1:8000/api/v1',
    'http://192.168.0.116:8000/api/v1',
  ];

  String? _customHost;
  String? _workingBaseUrl;
  String? _authToken;

  void setCustomHost(String? host) {
    if (host != null && host.trim().isNotEmpty) {
      String clean = host.trim();
      if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
        clean = 'http://$clean';
      }
      if (!clean.contains(':8000') && !clean.contains('/api')) {
        clean = '$clean:8000/api/v1';
      } else if (!clean.endsWith('/api/v1')) {
        clean = '$clean/api/v1';
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
        if (_authToken != null) 'Authorization': 'Bearer $_authToken',
      };

  Future<Map<String, dynamic>?> login(String username, String password) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/auth/login'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'username': username, 'password': password}),
        ).timeout(const Duration(seconds: 2));
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
            'region': (region != null && region.isNotEmpty) ? region : 'Mulbagal, Kolar, KA',
            'batch_id': (batchId != null && batchId.isNotEmpty) ? batchId : 'SERI-2026-M04',
            'dfl_capacity': (dflCapacity != null && dflCapacity.isNotEmpty) ? dflCapacity : '200 DFL',
            'breed': (breed != null && breed.isNotEmpty) ? breed : 'Double Hybrid (FC1 x FC2)',
          }),
        ).timeout(const Duration(seconds: 2));

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
      currentStage: 3,
      stageName: '3rd Instar',
      indoorTemp: 26.2,
      indoorHumidity: 74.0,
      outsideTemp: 28.5,
      outsideHumidity: 55.0,
      actuators: ActuatorStates(cooler: true, fan: false, heater: false),
      isAutoMode: true,
      tempTarget: 26.0,
      humidityTarget: 75.0,
      lastUpdated: DateTime.now(),
    );
  }

  Future<AIAdvice> getAIExplanation(String shedId, String lang) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.get(Uri.parse('$base/ai/explain/$shedId?lang=$lang'), headers: _headers)
            .timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          return AIAdvice.fromJson(jsonDecode(res.body));
        }
      } catch (_) {}
    }

    return AIAdvice(
      whyText: 'Outside temperature is high (34.2°C) today, so cooling is activated to keep the shed comfortable for silkworms.',
      currentAction: 'Cooling is ON',
      targetDescription: 'To maintain a suitable temperature of 25.0°C–26.5°C for 3rd instar silkworms.',
      bulletPoints: [
        'Outside temperature is high and heat permeates through the shed roof.',
        'Silkworms can get stressed and lose appetite in high heat (>28°C).',
        'Cooling helps maintain a safe environment and prevents cocoon quality loss.'
      ],
      language: lang,
    );
  }

  Future<bool> updateSetpoints(String shedId, bool isAuto, double tempTarget, double humTarget) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/control/$shedId/setpoints'),
          headers: _headers,
          body: jsonEncode({
            'is_auto_mode': isAuto,
            'temp_target': tempTarget,
            'humidity_target': humTarget,
          }),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) return true;
      } catch (_) {}
    }
    return false;
  }

  Future<bool> manualActuatorOverride(String shedId, String actuator, bool state) async {
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/control/$shedId/override'),
          headers: _headers,
          body: jsonEncode({
            'actuator': actuator,
            'state': state,
          }),
        ).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) return true;
      } catch (_) {}
    }
    return false;
  }
}
