import 'package:flutter_test/flutter_test.dart';
import 'package:setu/models/live_weather_data.dart';
import 'package:setu/services/location_weather_service.dart';

void main() {
  group('LiveWeatherData Model Tests', () {
    test('creates model correctly from Open-Meteo payload', () {
      final mockCurrent = {
        'temperature_2m': 28.6,
        'relative_humidity_2m': 48.0,
        'apparent_temperature': 30.5,
        'wind_speed_10m': 14.2,
        'weather_code': 2,
      };

      final weather = LiveWeatherData.fromOpenMeteo(
        currentJson: mockCurrent,
        lat: 13.1652,
        lon: 78.3965,
        locationName: 'Mulbagal, Karnataka',
        isGps: true,
      );

      expect(weather.temperature, 28.6);
      expect(weather.humidity, 48.0);
      expect(weather.apparentTemperature, 30.5);
      expect(weather.windSpeed, 14.2);
      expect(weather.weatherCode, 2);
      expect(weather.condition, 'Partly Cloudy');
      expect(weather.locationName, 'Mulbagal, Karnataka');
      expect(weather.isGps, true);
      expect(weather.silkwormAdvisory, isNotEmpty);
    });

    test('creates fallback model when offline or GPS unavailable', () {
      final fallback = LiveWeatherData.fallback(
        locationName: 'Kolar, Karnataka',
      );

      expect(fallback.temperature, 34.2);
      expect(fallback.humidity, 58.0);
      expect(fallback.locationName, 'Kolar, Karnataka');
      expect(fallback.isGps, false);
    });
  });

  group('LocationWeatherService Default Resolution', () {
    test('provides valid default coordinates', () {
      expect(LocationWeatherService.defaultLat, 13.1652);
      expect(LocationWeatherService.defaultLon, 78.3965);
    });
  });
}
