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
        ).timeout(const Duration(seconds: 4));

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

  Future<ShedData?> getShedStatus(
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
          _workingBaseUrl = base;
          return ShedData.fromJson(jsonDecode(res.body));
        }
      } catch (_) {}
    }
    return null;
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
    bool isAdvancedMode = false,
    double? airQualityTarget,
    double? lightLuxTarget,
    int? lightBrightness,
  }) async {
    for (final base in candidateUrls) {
      try {
        final payload = <String, dynamic>{
          'is_auto_mode': isAuto,
          'is_advanced_mode': isAdvancedMode,
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
          _workingBaseUrl = base;
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
        if (res.statusCode == 200) {
          _workingBaseUrl = base;
          return true;
        }
      } catch (_) {}
    }
    return false;
  }

  
  static final List<Map<String, dynamic>> defaultCatalogProducts = [
    {
      'id': 'prod_act_mist',
      'sku': 'SKU-ACT-MIST-4N',
      'name': 'High-Pressure Ultrasonic Cold Mist Fogger',
      'slug': 'high-pressure-ultrasonic-cold-mist-fogger',
      'category': 'Smart Rearing Shed Control',
      'short_description': 'Micro-droplet humidification unit maintaining 85–90% RH for 1st/2nd Instar Chawki worms.',
      'description': 'Generates ultra-fine 5–10 micron water aerosols that evaporate in ambient air without settling on mulberry leaves. Critical for young age silkworms to prevent dehydration while avoiding leaf rot and fungal flacherie outbreaks.',
      'price_minor_units': 899900,
      'currency': 'INR',
      'stock_quantity': 19,
      'unit': 'unit',
      'availability_status': 'IN_STOCK',
      'publication_status': 'PUBLISHED',
      'compatibility': 'Setu Gateway Relay Port 1/2, Automated Humidity Rules Engine',
    },
    {
      'id': 'prod_sns_sht31',
      'sku': 'SKU-SNS-SHT31-IP67',
      'name': 'Sensirion SHT31 High-Precision Dual Probe',
      'slug': 'sensirion-sht31-precision-probe',
      'category': 'IoT Temperature and Humidity Sensors',
      'short_description': 'IP67 weather-shielded temperature (±0.2°C) and relative humidity (±1.5% RH) sensor probe for rearing racks.',
      'description': 'Engineered specifically for harsh rearing environments with high moisture and disinfectant chemical vapors (formalin, chlorine dioxide). Delivers true laboratory precision across all five silkworm developmental instars.',
      'price_minor_units': 185000,
      'currency': 'INR',
      'stock_quantity': 118,
      'unit': 'unit',
      'availability_status': 'IN_STOCK',
      'publication_status': 'PUBLISHED',
      'compatibility': 'Setu Gateway v2.4, ESP32, Arduino, standard Modbus RTU masters',
    },
    {
      'id': 'prod_gw_01',
      'sku': 'SKU-GW-SERI-4G',
      'name': 'Setu Agri-Edge IoT Smart Gateway (4G + Wi-Fi)',
      'slug': 'setu-agri-edge-iot-smart-gateway-4g-wifi',
      'category': 'IoT Gateways and Connectivity',
      'short_description': 'Edge computing hub with dual 4G/Wi-Fi fallback, RS-485 Modbus, and 4 high-current relay outputs.',
      'description': 'Central computing and automation unit for silkworm sheds. Continuously logs microclimate metrics, triggers automated fans/foggers even during internet outages, and synchronizes real-time sensor streams with SeriCare Cloud.',
      'price_minor_units': 1249900,
      'currency': 'INR',
      'stock_quantity': 42,
      'unit': 'unit',
      'availability_status': 'IN_STOCK',
      'publication_status': 'PUBLISHED',
      'compatibility': 'Sensirion SHT31, NDIR CO2, Lux probes, 230V AC foggers/exhaust fans',
    },
    {
      'id': 'prod_sns_co2',
      'sku': 'SKU-SNS-CO2-S8',
      'name': 'SenseAir S8 Industrial NDIR CO2 Sensor Probe',
      'slug': 'senseair-s8-industrial-ndir-co2-sensor-probe',
      'category': 'Air Quality and Gas Detection',
      'short_description': 'Dual-beam non-dispersive infrared CO2 sensor (400–10,000 ppm) for Late Age silkworm ventilation monitoring.',
      'description': 'Detects carbon dioxide buildup in 4th and 5th instar rearing beds where silkworm respiration peaks. Prevents suffocating lethargy and uneven cocoon spinning by automatically activating ventilation curtains and exhaust blowers.',
      'price_minor_units': 345000,
      'currency': 'INR',
      'stock_quantity': 65,
      'unit': 'unit',
      'availability_status': 'IN_STOCK',
      'publication_status': 'PUBLISHED',
      'compatibility': 'Setu Gateway v2.4 Analog/UART Port, Modbus RTU',
    },
    {
      'id': 'prod_act_fan',
      'sku': 'SKU-ACT-FAN-400',
      'name': 'Smart Variable-Speed Microclimate Exhaust Blower',
      'slug': 'smart-variable-speed-microclimate-exhaust-blower',
      'category': 'Smart Rearing Shed Control',
      'short_description': 'Quiet, high-airflow 400 CFM negative-pressure extraction fan with thermal overload cut-off.',
      'description': 'Evacuates stale, humid, and CO2-saturated air during critical molting and feeding stages. Whisper-quiet brushless DC motor avoids stressing worms during late-stage feeding cycles.',
      'price_minor_units': 420000,
      'currency': 'INR',
      'stock_quantity': 28,
      'unit': 'unit',
      'availability_status': 'IN_STOCK',
      'publication_status': 'PUBLISHED',
      'compatibility': 'Setu Gateway Relay 1, PWM speed controller board',
    },
  ];

  Future<List<Map<String, dynamic>>> getProducts({String? category}) async {
    for (final base in candidateUrls) {
      final categoryParam = (category != null && category.isNotEmpty && category != 'All')
          ? '?category=${Uri.encodeComponent(category)}'
          : '';

      // 1. Try public products endpoint first
      try {
        final pubUri = Uri.parse('$base/public/products$categoryParam');
        final res = await http.get(pubUri, headers: {'Accept': 'application/json'}).timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final decoded = jsonDecode(res.body);
          if (decoded is List) {
            _workingBaseUrl = base;
            return List<Map<String, dynamic>>.from(decoded);
          }
        }
      } catch (_) {}

      // 2. Try authenticated /products
      try {
        final uri = Uri.parse('$base/products$categoryParam');
        final res = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 5));
        if (res.statusCode == 200) {
          final decoded = jsonDecode(res.body);
          if (decoded is List) {
            _workingBaseUrl = base;
            return List<Map<String, dynamic>>.from(decoded);
          }
        }
      } catch (_) {}
    }
    return [];
  }

  Future<List<Map<String, dynamic>>> getOrders() async {
    for (final base in candidateUrls) {
      try {
        final uri = Uri.parse('$base/orders');
        final res = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 4));
        if (res.statusCode == 200) {
          final decoded = jsonDecode(res.body);
          if (decoded is List) {
            _workingBaseUrl = base;
            return List<Map<String, dynamic>>.from(decoded);
          }
        }
      } catch (_) {}
    }
    return [];
  }

  Future<Map<String, dynamic>> placeOrder({
    required List<Map<String, dynamic>> items,
    required String shippingAddress,
    String paymentMethod = 'UPI',
    String? notes,
  }) async {
    String? serverError;
    for (final base in candidateUrls) {
      try {
        final res = await http.post(
          Uri.parse('$base/orders'),
          headers: _headers,
          body: jsonEncode({
            'items': items,
            'shipping_address': shippingAddress,
            'payment_method': paymentMethod,
            if (notes != null && notes.isNotEmpty) 'notes': notes,
          }),
        ).timeout(const Duration(seconds: 6));
        if (res.statusCode == 200 || res.statusCode == 201) {
          _workingBaseUrl = base;
          return {'success': true, 'data': jsonDecode(res.body)};
        } else {
          try {
            final err = jsonDecode(res.body);
            serverError = err['detail']?.toString() ?? 'Failed with status ${res.statusCode}';
          } catch (_) {
            serverError = 'Server error (${res.statusCode})';
          }
        }
      } catch (_) {}
    }
    return {'success': false, 'error': serverError ?? 'Could not place order'};
  }
}
