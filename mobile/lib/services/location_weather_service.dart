import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import '../models/live_weather_data.dart';

class LocationWeatherService {
  // Default fallback coordinates: Mulbagal, Kolar, Karnataka (the primary sericulture cluster)
  static const double defaultLat = 13.1652;
  static const double defaultLon = 78.3965;
  static const String defaultRegion = 'Mulbagal, Kolar, KA';

  /// Resolves device geolocation using GPS / Network Provider.
  /// Falls back gracefully if permissions are denied or GPS is turned off.
  Future<Map<String, dynamic>> resolveCoordinates({String? fallbackRegion}) async {
    bool isGps = false;
    double lat = defaultLat;
    double lon = defaultLon;

    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        debugPrint('[WeatherService] Location services disabled. Using regional fallback.');
        return {'lat': lat, 'lon': lon, 'isGps': false};
      }

      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          debugPrint('[WeatherService] Location permission denied. Using regional fallback.');
          return {'lat': lat, 'lon': lon, 'isGps': false};
        }
      }

      if (permission == LocationPermission.deniedForever) {
        debugPrint('[WeatherService] Location permissions permanently denied. Using fallback.');
        return {'lat': lat, 'lon': lon, 'isGps': false};
      }

      // Permissions granted: Acquire live position
      final Position position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 8),
        ),
      );

      lat = position.latitude;
      lon = position.longitude;
      isGps = true;
      debugPrint('[WeatherService] Acquired GPS location: ($lat, $lon)');
    } catch (e) {
      debugPrint('[WeatherService] Geolocation error: $e. Falling back to default region.');
      // If error or timeout, default coordinates are kept
    }

    return {'lat': lat, 'lon': lon, 'isGps': isGps};
  }

  /// Reverse geocodes coordinates into human-readable city/district name
  Future<String> reverseGeocode(double lat, double lon, {String? defaultName}) async {
    try {
      final uri = Uri.parse(
        'https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=$lat&longitude=$lon&localityLanguage=en',
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final city = data['city'] ?? data['locality'] ?? data['principalSubdivision'];
        final state = data['principalSubdivision'];
        if (city != null && city.toString().trim().isNotEmpty) {
          if (state != null && state != city) {
            return '$city, $state';
          }
          return city.toString();
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Reverse geocode error: $e');
    }

    return defaultName ?? defaultRegion;
  }

  /// Fetches real-time temperature, humidity and microclimate metrics from Open-Meteo
  Future<LiveWeatherData> fetchLiveWeather({
    double? latitude,
    double? longitude,
    bool? isGpsSupplied,
    String? fallbackRegionName,
  }) async {
    double lat = latitude ?? defaultLat;
    double lon = longitude ?? defaultLon;
    bool isGps = isGpsSupplied ?? false;

    // If no coordinates passed, determine from device geolocation
    if (latitude == null || longitude == null) {
      final coords = await resolveCoordinates(fallbackRegion: fallbackRegionName);
      lat = coords['lat'];
      lon = coords['lon'];
      isGps = coords['isGps'];
    }

    // Determine location name
    String locName = fallbackRegionName ?? defaultRegion;
    if (isGps) {
      locName = await reverseGeocode(lat, lon, defaultName: fallbackRegionName);
    }

    try {
      final url = Uri.parse(
        'https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto',
      );

      final response = await http.get(url).timeout(const Duration(seconds: 6));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final current = data['current'];
        if (current != null) {
          return LiveWeatherData.fromOpenMeteo(
            currentJson: current,
            lat: lat,
            lon: lon,
            locationName: locName,
            isGps: isGps,
          );
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Live weather fetch error: $e');
    }

    // Fallback if network fails
    return LiveWeatherData.fallback(
      locationName: locName,
      lat: lat,
      lon: lon,
    );
  }
}
