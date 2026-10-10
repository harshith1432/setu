import 'package:flutter/material.dart';

class LiveWeatherData {
  final double temperature;
  final double humidity;
  final double? apparentTemperature;
  final double? windSpeed;
  final int weatherCode;
  final String condition;
  final String locationName;
  final double latitude;
  final double longitude;
  final DateTime lastUpdated;
  final bool isGps;

  LiveWeatherData({
    required this.temperature,
    required this.humidity,
    this.apparentTemperature,
    this.windSpeed,
    required this.weatherCode,
    required this.condition,
    required this.locationName,
    required this.latitude,
    required this.longitude,
    required this.lastUpdated,
    required this.isGps,
  });

  /// Factory from Open-Meteo Current payload and reverse-geocoded location
  factory LiveWeatherData.fromOpenMeteo({
    required Map<String, dynamic> currentJson,
    required double lat,
    required double lon,
    required String locationName,
    required bool isGps,
  }) {
    final temp = (currentJson['temperature_2m'] as num?)?.toDouble() ?? 28.0;
    final hum = (currentJson['relative_humidity_2m'] as num?)?.toDouble() ?? 55.0;
    final appTemp = (currentJson['apparent_temperature'] as num?)?.toDouble();
    final wind = (currentJson['wind_speed_10m'] as num?)?.toDouble();
    final code = (currentJson['weather_code'] as num?)?.toInt() ?? 0;

    return LiveWeatherData(
      temperature: double.parse(temp.toStringAsFixed(1)),
      humidity: double.parse(hum.toStringAsFixed(1)),
      apparentTemperature: appTemp != null ? double.parse(appTemp.toStringAsFixed(1)) : null,
      windSpeed: wind != null ? double.parse(wind.toStringAsFixed(1)) : null,
      weatherCode: code,
      condition: _conditionFromCode(code),
      locationName: locationName,
      latitude: lat,
      longitude: lon,
      lastUpdated: DateTime.now(),
      isGps: isGps,
    );
  }

  factory LiveWeatherData.fallback({
    String locationName = 'Mulbagal, Karnataka',
    double lat = 13.1652,
    double lon = 78.3965,
  }) {
    return LiveWeatherData(
      temperature: 34.2,
      humidity: 58.0,
      apparentTemperature: 36.0,
      windSpeed: 14.5,
      weatherCode: 1,
      condition: 'Partly Sunny',
      locationName: locationName,
      latitude: lat,
      longitude: lon,
      lastUpdated: DateTime.now(),
      isGps: false,
    );
  }

  static String _conditionFromCode(int code) {
    if (code == 0) return 'Clear Sky';
    if (code == 1) return 'Mainly Clear';
    if (code == 2) return 'Partly Cloudy';
    if (code == 3) return 'Overcast';
    if (code == 45 || code == 48) return 'Foggy';
    if (code >= 51 && code <= 55) return 'Drizzle';
    if (code >= 61 && code <= 65) return 'Rainy';
    if (code >= 71 && code <= 77) return 'Snow Flurries';
    if (code >= 80 && code <= 82) return 'Rain Showers';
    if (code >= 95) return 'Thunderstorm';
    return 'Clear Sky';
  }

  IconData get weatherIcon {
    if (weatherCode == 0 || weatherCode == 1) return Icons.wb_sunny_rounded;
    if (weatherCode == 2 || weatherCode == 3) return Icons.cloud_queue_rounded;
    if (weatherCode == 45 || weatherCode == 48) return Icons.foggy;
    if (weatherCode >= 51 && weatherCode <= 67) return Icons.grain_rounded;
    if (weatherCode >= 80 && weatherCode <= 82) return Icons.water_drop_rounded;
    if (weatherCode >= 95) return Icons.flash_on_rounded;
    return Icons.wb_sunny_rounded;
  }

  Color get weatherColor {
    if (weatherCode == 0 || weatherCode == 1) return const Color(0xFFF57C00);
    if (weatherCode == 2 || weatherCode == 3) return const Color(0xFF0288D1);
    if (weatherCode >= 51 && weatherCode <= 82) return const Color(0xFF1976D2);
    if (weatherCode >= 95) return const Color(0xFF7B1FA2);
    return const Color(0xFFE65100);
  }

  /// Farmer advisory based on outside ambient conditions
  String get silkwormAdvisory {
    if (temperature > 32.0) {
      return 'Extreme outdoor heat. Roof radiation risk. Automated cooling active.';
    } else if (temperature > 28.0) {
      return 'Warm outside. Maintain ventilation & misting to protect cocoon quality.';
    } else if (temperature < 22.0) {
      return 'Cold outside. Ensure shed insulation & heating standby.';
    } else if (humidity > 80.0) {
      return 'High outdoor humidity. Keep exhaust fans running to avoid flacherie.';
    } else if (humidity < 50.0) {
      return 'Dry outside air. Humidifiers or damp gunny bags recommended.';
    }
    return 'Comfortable outdoor weather. Shed microclimate stable.';
  }
}
