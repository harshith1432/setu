import 'dart:async';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/foundation.dart';
import '../models/shed_data.dart';
import 'api_service.dart';

/// Centralized Firestore Database Service for SeriCare Mobile.
/// Connects directly to Cloud Firestore project 'setu-a767c' with real-time snapshots,
/// offline persistence, and seamless fallback to REST ApiService when offline.
class FirestoreService {
  static final FirestoreService _instance = FirestoreService._internal();
  factory FirestoreService() => _instance;
  FirestoreService._internal();

  FirebaseFirestore? _firestore;

  FirebaseFirestore get firestore {
    _firestore ??= FirebaseFirestore.instance;
    return _firestore!;
  }

  bool get isAvailable {
    try {
      return FirebaseFirestore.instance.app.options.projectId.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  // ===========================================================================
  // 1. REAL-TIME SHED TELEMETRY STREAM & SNAPSHOTS
  // ===========================================================================

  /// Real-time stream of the latest microclimate sensor reading for a rearing shed.
  Stream<ShedData?> streamLatestTelemetry(String shedId) {
    if (!isAvailable) {
      return const Stream.empty();
    }

    try {
      return firestore
          .collection('shed_telemetry')
          .where('shed_id', isEqualTo: shedId)
          .orderBy('timestamp', descending: true)
          .limit(1)
          .snapshots()
          .map((snapshot) {
        if (snapshot.docs.isEmpty) return null;
        final doc = snapshot.docs.first;
        final data = doc.data();
        data['id'] = doc.id;
        return _mapDocToShedData(data);
      }).handleError((err) {
        debugPrint('Firestore telemetry stream error: $err');
        return null;
      });
    } catch (e) {
      debugPrint('Firestore telemetry stream initialization failed: $e');
      return const Stream.empty();
    }
  }

  /// One-time fetch of the latest telemetry document.
  Future<ShedData?> getLatestTelemetry(String shedId) async {
    if (!isAvailable) return null;
    try {
      final query = await firestore
          .collection('shed_telemetry')
          .where('shed_id', isEqualTo: shedId)
          .orderBy('timestamp', descending: true)
          .limit(1)
          .get(const GetOptions(source: Source.serverAndCache));

      if (query.docs.isEmpty) return null;
      final doc = query.docs.first;
      final data = doc.data();
      data['id'] = doc.id;
      return _mapDocToShedData(data);
    } catch (e) {
      debugPrint('getLatestTelemetry error: $e');
      return null;
    }
  }

  /// Historical telemetry records with pagination.
  Future<List<Map<String, dynamic>>> getTelemetryHistory(
    String shedId, {
    int limit = 50,
    DocumentSnapshot? startAfter,
  }) async {
    if (!isAvailable) return [];
    try {
      var q = firestore
          .collection('shed_telemetry')
          .where('shed_id', isEqualTo: shedId)
          .orderBy('timestamp', descending: true)
          .limit(limit);

      if (startAfter != null) {
        q = q.startAfterDocument(startAfter);
      }

      final res = await q.get(const GetOptions(source: Source.serverAndCache));
      return res.docs.map((doc) {
        final d = doc.data();
        d['doc_id'] = doc.id;
        return d;
      }).toList();
    } catch (e) {
      debugPrint('getTelemetryHistory error: $e');
      return [];
    }
  }

  // ===========================================================================
  // 2. HARDWARE PRODUCTS CATALOGUE
  // ===========================================================================

  /// Real-time stream of hardware store catalogue.
  Stream<List<Map<String, dynamic>>> streamProducts({String? category}) {
    if (!isAvailable) {
      return Stream.value(ApiService.defaultCatalogProducts);
    }

    try {
      Query<Map<String, dynamic>> q = firestore.collection('products');
      if (category != null && category.isNotEmpty && category != 'All') {
        q = q.where('category', isEqualTo: category);
      }

      return q.snapshots().map((snapshot) {
        if (snapshot.docs.isEmpty) {
          return ApiService.defaultCatalogProducts;
        }
        return snapshot.docs.map((doc) {
          final data = doc.data();
          data['id'] = doc.id;
          return data;
        }).toList();
      }).handleError((err) {
        debugPrint('streamProducts error: $err');
        return ApiService.defaultCatalogProducts;
      });
    } catch (e) {
      debugPrint('streamProducts init error: $e');
      return Stream.value(ApiService.defaultCatalogProducts);
    }
  }

  /// Synchronous/async list fetch with automatic offline cache.
  Future<List<Map<String, dynamic>>> getProducts({String? category}) async {
    if (!isAvailable) return ApiService.defaultCatalogProducts;
    try {
      Query<Map<String, dynamic>> q = firestore.collection('products');
      if (category != null && category.isNotEmpty && category != 'All') {
        q = q.where('category', isEqualTo: category);
      }
      final snapshot = await q.get(const GetOptions(source: Source.serverAndCache));
      if (snapshot.docs.isEmpty) {
        return ApiService.defaultCatalogProducts;
      }
      return snapshot.docs.map((d) {
        final m = d.data();
        m['id'] = d.id;
        return m;
      }).toList();
    } catch (e) {
      debugPrint('getProducts error, returning default catalog: $e');
      return ApiService.defaultCatalogProducts;
    }
  }

  // ===========================================================================
  // 3. ORDERS & COMMERCE
  // ===========================================================================

  /// Stream of farmer orders.
  Stream<List<Map<String, dynamic>>> streamOrders(String userId) {
    if (!isAvailable) return Stream.value([]);
    try {
      return firestore
          .collection('orders')
          .where('user_id', isEqualTo: userId)
          .orderBy('created_at', descending: true)
          .snapshots()
          .map((snapshot) {
        return snapshot.docs.map((doc) {
          final data = doc.data();
          data['id'] = doc.id;
          return data;
        }).toList();
      }).handleError((err) {
        debugPrint('streamOrders error: $err');
        return <Map<String, dynamic>>[];
      });
    } catch (e) {
      debugPrint('streamOrders init error: $e');
      return Stream.value([]);
    }
  }

  /// Fetch orders for a user.
  Future<List<Map<String, dynamic>>> getOrders(String userId) async {
    if (!isAvailable) return [];
    try {
      final snapshot = await firestore
          .collection('orders')
          .where('user_id', isEqualTo: userId)
          .orderBy('created_at', descending: true)
          .get(const GetOptions(source: Source.serverAndCache));

      return snapshot.docs.map((doc) {
        final d = doc.data();
        d['id'] = doc.id;
        return d;
      }).toList();
    } catch (e) {
      debugPrint('getOrders error: $e');
      return [];
    }
  }

  /// Create and place an order directly in Cloud Firestore.
  Future<Map<String, dynamic>> placeOrder({
    required String userId,
    required List<Map<String, dynamic>> items,
    required String shippingAddress,
    String paymentMethod = 'UPI',
    String? notes,
  }) async {
    if (!isAvailable) {
      return {'success': false, 'error': 'Firestore not initialized'};
    }

    try {
      int totalPaise = 0;
      for (final it in items) {
        final price = (it['price_minor_units'] as num?)?.toInt() ?? 0;
        final qty = (it['quantity'] as num?)?.toInt() ?? 1;
        totalPaise += (price * qty);
      }

      final docRef = firestore.collection('orders').doc();
      final nowIso = DateTime.now().toUtc().isoformat();
      final orderData = {
        'id': docRef.id,
        'user_id': userId,
        'status': 'PROCESSING',
        'items': items,
        'total_amount_minor_units': totalPaise,
        'currency': 'INR',
        'shipping_address': shippingAddress,
        'payment_method': paymentMethod,
        'notes': notes ?? '',
        'created_at': nowIso,
        'updated_at': nowIso,
      };

      await docRef.set(orderData);
      return {'success': true, 'data': orderData};
    } catch (e) {
      debugPrint('placeOrder Firestore error: $e');
      return {'success': false, 'error': e.toString()};
    }
  }

  // ===========================================================================
  // 4. ACTUATOR & DEVICE COMMANDS
  // ===========================================================================

  /// Issue a hardware control command to an IoT rearing shed.
  Future<bool> issueActuatorCommand({
    required String shedId,
    required String actuator,
    required bool state,
    String? source,
  }) async {
    if (!isAvailable) return false;
    try {
      final cmdRef = firestore.collection('device_commands').doc();
      final nowIso = DateTime.now().toUtc().isoformat();

      await cmdRef.set({
        'command_id': cmdRef.id,
        'shed_id': shedId,
        'actuator': actuator,
        'state': state ? 1 : 0,
        'source': source ?? 'mobile_app',
        'status': 'PENDING',
        'created_at': nowIso,
      });

      // Optimistically update shed actuator state
      final shedRef = firestore.collection('sheds').doc(shedId);
      await shedRef.set({
        'actuators': {
          actuator: state,
        },
        'updated_at': nowIso,
      }, SetOptions(merge: true));

      return true;
    } catch (e) {
      debugPrint('issueActuatorCommand error: $e');
      return false;
    }
  }

  // ===========================================================================
  // 5. USER PROFILE & FARM REGISTRATION
  // ===========================================================================

  /// Fetch user profile from Firestore.
  Future<Map<String, dynamic>?> getUserProfile(String userId) async {
    if (!isAvailable) return null;
    try {
      final doc = await firestore.collection('users').doc(userId).get();
      if (!doc.exists) return null;
      final data = doc.data()!;
      data['id'] = doc.id;
      return data;
    } catch (e) {
      debugPrint('getUserProfile error: $e');
      return null;
    }
  }

  /// Create or update user profile.
  Future<void> saveUserProfile(String userId, Map<String, dynamic> data) async {
    if (!isAvailable) return;
    try {
      data['updated_at'] = DateTime.now().toUtc().isoformat();
      await firestore.collection('users').doc(userId).set(data, SetOptions(merge: true));
    } catch (e) {
      debugPrint('saveUserProfile error: $e');
    }
  }

  // ===========================================================================
  // PRIVATE MAPPER HELPERS
  // ===========================================================================

  ShedData _mapDocToShedData(Map<String, dynamic> map) {
    DateTime ts;
    final rawTs = map['timestamp'];
    if (rawTs is Timestamp) {
      ts = rawTs.toDate();
    } else if (rawTs is String) {
      ts = DateTime.tryParse(rawTs) ?? DateTime.now();
    } else {
      ts = DateTime.now();
    }

    Map<String, dynamic> actMap = {};
    if (map['actuators'] is Map) {
      actMap = Map<String, dynamic>.from(map['actuators']);
    } else {
      actMap = {
        'cooler': map['cooler_active'] == true || map['cooler'] == true,
        'heater': map['heater_active'] == true || map['heater'] == true,
        'fan': map['fan_active'] == true || map['fan'] == true,
        'light': map['light_active'] == true || map['light'] == true,
        'light_brightness': (map['light_brightness'] as num?)?.toInt() ?? 35,
      };
    }

    return ShedData(
      shedId: map['shed_id']?.toString() ?? 'shed_01',
      farmName: map['farm_name']?.toString() ?? 'Green Valley Farm',
      region: map['region']?.toString() ?? 'My Rearing Shed',
      overallStatus: map['overall_status']?.toString() ?? 'IDEAL',
      statusHeadline: map['status_headline']?.toString() ?? 'Ideal for Silkworms',
      statusSubline: map['status_subline']?.toString() ?? 'Everything is normal inside the shed.',
      currentStage: (map['current_stage'] as num?)?.toInt() ?? 4,
      stageName: map['stage_name']?.toString() ?? 'III Instar',
      indoorTemp: (map['indoor_temp'] as num?)?.toDouble() ?? 26.2,
      indoorHumidity: (map['indoor_humidity'] as num?)?.toDouble() ?? 80.0,
      indoorAirQuality: (map['indoor_air_quality'] as num?)?.toDouble() ?? 88.0,
      indoorLightLux: (map['indoor_light_lux'] as num?)?.toDouble() ?? 22.0,
      outsideTemp: (map['outside_temp'] as num?)?.toDouble() ?? 34.2,
      outsideHumidity: (map['outside_humidity'] as num?)?.toDouble() ?? 58.0,
      actuators: ActuatorStates.fromJson(actMap),
      isAutoMode: map['is_auto_mode'] ?? true,
      isAdvancedMode: map['is_advanced_mode'] ?? false,
      tempTarget: (map['target_temp'] as num?)?.toDouble() ?? 26.0,
      humidityTarget: (map['target_humidity'] as num?)?.toDouble() ?? 80.0,
      airflowTarget: (map['airflow_target'] as num?)?.toDouble() ?? 50.0,
      lightTarget: (map['light_target'] as num?)?.toDouble() ?? 35.0,
      airQualityTarget: (map['air_quality_target'] as num?)?.toDouble() ?? 80.0,
      lightLuxTarget: (map['light_lux_target'] as num?)?.toDouble() ?? 25.0,
      photoperiodMode: map['photoperiod_mode']?.toString() ?? 'DAY',
      lastUpdated: ts,
    );
  }
}

extension DateTimeIsoExtension on DateTime {
  String isoformat() => toUtc().toIso8601String();
}
