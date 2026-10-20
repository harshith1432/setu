import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geocoding/geocoding.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import '../models/live_weather_data.dart';

class LocationWeatherService {
  /// Specifically acquires live device location, returning a status map
  Future<Map<String, dynamic>> acquireDeviceLocation() async {
    final live = await resolveLiveLocation();
    if (live != null) {
      return {
        'success': true,
        'lat': live['lat'] as double,
        'lon': live['lon'] as double,
        'region': live['locationName'] as String,
        'isGps': live['isGps'] ?? false,
      };
    }
    return {
      'success': false,
      'error': 'Unable to acquire live location. Please enable GPS or verify internet access.',
    };
  }

  /// Resolves the user's live coordinates directly from the device GPS or live IP location.
  /// Does NOT use any hardcoded default coordinates.
  Future<Map<String, dynamic>?> resolveLiveLocation() async {
    // 1. Try Live Device GPS
    try {
      bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (serviceEnabled) {
        LocationPermission permission = await Geolocator.checkPermission();
        if (permission == LocationPermission.denied) {
          permission = await Geolocator.requestPermission();
        }

        if (permission == LocationPermission.whileInUse ||
            permission == LocationPermission.always) {
          final Position position = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(
              accuracy: LocationAccuracy.high,
              timeLimit: Duration(seconds: 8),
            ),
          );

          final lat = position.latitude;
          final lon = position.longitude;
          final locationName = await reverseGeocode(lat, lon);

          debugPrint('[WeatherService] Live GPS Acquired: ($lat, $lon) -> $locationName');
          return {
            'lat': lat,
            'lon': lon,
            'locationName': locationName,
            'isGps': true,
          };
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Device GPS detection error: $e');
    }

    // 2. Try Live IP Geolocation (automatically gets the user's live physical location over the internet)
    try {
      final ipUri = Uri.parse('http://ip-api.com/json');
      final ipRes = await http.get(ipUri).timeout(const Duration(seconds: 5));
      if (ipRes.statusCode == 200) {
        final ipData = jsonDecode(ipRes.body);
        if (ipData['status'] == 'success') {
          final lat = (ipData['lat'] as num).toDouble();
          final lon = (ipData['lon'] as num).toDouble();
          final city = ipData['city'] ?? '';
          final region = ipData['regionName'] ?? '';
          final country = ipData['country'] ?? '';
          final parts = [if (city.isNotEmpty) city, if (region.isNotEmpty) region, if (country.isNotEmpty) country];
          final locationName = parts.isNotEmpty ? parts.join(', ') : 'Live Location';

          debugPrint('[WeatherService] Live IP Location Acquired: ($lat, $lon) -> $locationName');
          return {
            'lat': lat,
            'lon': lon,
            'locationName': locationName,
            'isGps': false,
          };
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Live IP location detection error: $e');
    }

    // Secondary IP service fallback
    try {
      final freeIpUri = Uri.parse('https://freeipapi.com/api/json');
      final freeRes = await http.get(freeIpUri).timeout(const Duration(seconds: 5));
      if (freeRes.statusCode == 200) {
        final data = jsonDecode(freeRes.body);
        final lat = (data['latitude'] as num?)?.toDouble();
        final lon = (data['longitude'] as num?)?.toDouble();
        if (lat != null && lon != null) {
          final city = data['cityName'] ?? '';
          final region = data['regionName'] ?? '';
          final parts = [if (city.isNotEmpty) city, if (region.isNotEmpty) region];
          final locationName = parts.isNotEmpty ? parts.join(', ') : 'Live Location';
          return {
            'lat': lat,
            'lon': lon,
            'locationName': locationName,
            'isGps': false,
          };
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Secondary IP location error: $e');
    }

    return null;
  }

  /// Geocodes a user-specified custom address live worldwide via Open-Meteo
  Future<Map<String, dynamic>?> geocodeAddress(String address) async {
    if (address.trim().isEmpty) return null;
    try {
      final clean = address.split(',')[0].trim();
      final uri = Uri.parse(
        'https://geocoding-api.open-meteo.com/v1/search?name=${Uri.encodeComponent(clean)}&count=1&language=en&format=json',
      );
      final response = await http.get(uri).timeout(const Duration(seconds: 6));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final results = data['results'] as List?;
        if (results != null && results.isNotEmpty) {
          final first = results[0];
          final lat = (first['latitude'] as num).toDouble();
          final lon = (first['longitude'] as num).toDouble();
          final name = first['name'] ?? clean;
          final admin1 = first['admin1'];
          final country = first['country'];
          final parts = [name, if (admin1 != null && admin1 != name) admin1, if (country != null) country];
          return {
            'lat': lat,
            'lon': lon,
            'locationName': parts.join(', '),
            'isGps': false,
          };
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Live geocoding error: $e');
    }
    return null;
  }

  /// Reverse geocodes coordinates to a live exact city/town/village name
  Future<String> reverseGeocode(double lat, double lon) async {
    // 1. Native on-device OS Geocoder (Android Geocoder via Google Play Services)
    try {
      final placemarks = await Geocoding().placemarkFromCoordinates(lat, lon);
      if (placemarks.isNotEmpty) {
        final p = placemarks.first;
        final local = (p.locality != null && p.locality!.trim().isNotEmpty)
            ? p.locality!.trim()
            : ((p.subLocality != null && p.subLocality!.trim().isNotEmpty)
                ? p.subLocality!.trim()
                : (p.name != null && p.name!.trim().isNotEmpty ? p.name!.trim() : null));

        final broader = (p.subAdministrativeArea != null && p.subAdministrativeArea!.trim().isNotEmpty)
            ? p.subAdministrativeArea!.trim()
            : ((p.administrativeArea != null && p.administrativeArea!.trim().isNotEmpty)
                ? p.administrativeArea!.trim()
                : null);

        final country = (p.country != null && p.country!.trim().isNotEmpty) ? p.country!.trim() : null;

        final parts = <String>[];
        if (local != null && local.isNotEmpty) {
          parts.add(local);
        }
        if (broader != null && broader.isNotEmpty && !parts.contains(broader)) {
          parts.add(broader);
        }
        if (country != null && country.isNotEmpty && !parts.contains(country)) {
          parts.add(country);
        }

        if (parts.isNotEmpty) {
          final resolved = parts.join(', ');
          debugPrint('[WeatherService] Native Phone Geocoder Resolved: $resolved');
          return resolved;
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Native phone geocoder error: $e');
    }

    // 2. OpenStreetMap Nominatim fallback
    try {
      final uri = Uri.parse(
        'https://nominatim.openstreetmap.org/reverse?lat=$lat&lon=$lon&format=json',
      );
      final response = await http.get(uri, headers: {
        'User-Agent': 'SetuApp/1.0 (sericare.setu)',
      }).timeout(const Duration(seconds: 4));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final addr = data['address'] as Map<String, dynamic>?;
        if (addr != null) {
          final localPlace = addr['village'] ??
              addr['town'] ??
              addr['city'] ??
              addr['suburb'] ??
              addr['neighbourhood'] ??
              addr['residential'] ??
              addr['municipality'];

          final broaderPlace = addr['county'] ??
              addr['state_district'] ??
              addr['city'] ??
              addr['town'];

          final country = addr['country'];

          final parts = <String>[];
          if (localPlace != null && localPlace.toString().trim().isNotEmpty) {
            parts.add(localPlace.toString().trim());
          }
          if (broaderPlace != null && broaderPlace.toString().trim().isNotEmpty) {
            String cleanBroader = broaderPlace.toString().trim();
            cleanBroader = cleanBroader.replaceAll(RegExp(r'\s+taluk$', caseSensitive: false), '');
            if (!parts.contains(cleanBroader)) {
              parts.add(cleanBroader);
            }
          }
          if (country != null && country.toString().trim().isNotEmpty) {
            parts.add(country.toString().trim());
          }

          if (parts.isNotEmpty) {
            return parts.join(', ');
          }
        }
      }
    } catch (e) {
      debugPrint('[WeatherService] Nominatim reverse geocode error: $e');
    }

    return 'Lat ${lat.toStringAsFixed(2)}, Lon ${lon.toStringAsFixed(2)}';
  }

  /// Fetches live real-time temperature, humidity and microclimate metrics from Open-Meteo.
  /// Throws Exception if live location cannot be detected or network fails.
  Future<LiveWeatherData> fetchLiveWeather({
    double? latitude,
    double? longitude,
    String? customLocationName,
  }) async {
    double? lat = latitude;
    double? lon = longitude;
    String? locName = customLocationName;
    bool isGps = latitude != null;

    // If specific coordinates were not passed, resolve them live
    if (lat == null || lon == null) {
      if (customLocationName != null && customLocationName.trim().isNotEmpty) {
        final geo = await geocodeAddress(customLocationName);
        if (geo != null) {
          lat = geo['lat'];
          lon = geo['lon'];
          locName = geo['locationName'];
          isGps = false;
        }
      }

      if (lat == null || lon == null) {
        final liveLoc = await resolveLiveLocation();
        if (liveLoc != null) {
          lat = liveLoc['lat'];
          lon = liveLoc['lon'];
          locName = liveLoc['locationName'];
          isGps = liveLoc['isGps'] ?? false;
        }
      }
    }

    if (lat == null || lon == null) {
      throw Exception('Unable to detect live location. Please enable GPS or verify internet connectivity.');
    }

    final url = Uri.parse(
      'https://api.open-meteo.com/v1/forecast?latitude=$lat&longitude=$lon&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto',
    );

    final response = await http.get(url).timeout(const Duration(seconds: 8));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final current = data['current'];
      if (current != null) {
        return LiveWeatherData.fromOpenMeteo(
          currentJson: current,
          lat: lat,
          lon: lon,
          locationName: locName ?? 'Live Location',
          isGps: isGps,
        );
      }
    }

    throw Exception('Failed to retrieve live weather data from server (HTTP ${response.statusCode}).');
  }
}
