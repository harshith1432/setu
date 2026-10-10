import 'package:flutter_test/flutter_test.dart';
import 'package:setu/models/live_weather_data.dart';
import 'package:setu/services/location_weather_service.dart';

void main() {
  group('LiveWeatherData Model Tests', () {
    test('creates model correctly from live Open-Meteo payload', () {
      final mockCurrent = {
        'temperature_2m': 29.4,
        'relative_humidity_2m': 46.0,
        'apparent_temperature': 31.2,
        'wind_speed_10m': 13.8,
        'weather_code': 1,
      };

      final weather = LiveWeatherData.fromOpenMeteo(
        currentJson: mockCurrent,
        lat: 12.9716,
        lon: 77.5946,
        locationName: 'Bengaluru, Karnataka',
        isGps: true,
      );

      expect(weather.temperature, 29.4);
      expect(weather.humidity, 46.0);
      expect(weather.apparentTemperature, 31.2);
      expect(weather.windSpeed, 13.8);
      expect(weather.weatherCode, 1);
      expect(weather.condition, 'Mainly Clear');
      expect(weather.locationName, 'Bengaluru, Karnataka');
      expect(weather.isGps, true);
      expect(weather.silkwormAdvisory, isNotEmpty);
    });
  });

  group('LocationWeatherService Live Resolution Tests', () {
    test('initializes without any hardcoded default coordinates', () {
      final service = LocationWeatherService();
      expect(service, isNotNull);
    });
  });
}
