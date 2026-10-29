import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';
import '../models/live_weather_data.dart';
import '../l10n/app_localizations.dart';

class LiveWeatherCard extends StatelessWidget {
  final bool compact;
  const LiveWeatherCard({super.key, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final l10n = AppLocalizations.of(context);
    final weather = provider.liveWeather;
    final isLoading = provider.isLoadingWeather;
    final shed = provider.shedData;

    final temp = weather?.temperature ?? shed.outsideTemp;
    final hum = weather?.humidity ?? shed.outsideHumidity;
    final locName = weather?.locationName ?? provider.region;
    final condition = weather?.condition ?? 'Fair';
    final isGps = weather?.isGps ?? false;

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            const Color(0xFFFFFDE7),
            const Color(0xFFFFF9C4),
            const Color(0xFFFFF59D).withValues(alpha: 0.8),
          ],
        ),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: const Color(0xFFFFD54F).withValues(alpha: 0.6),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: const Color(0xFFF57F17).withValues(alpha: 0.08),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(18),
          onTap: () => _showWeatherDetailsSheet(context, provider, weather),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header: Location Name + GPS Badge + Refresh Action
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Row(
                        children: [
                          Icon(
                            isGps ? Icons.my_location_rounded : Icons.location_on_rounded,
                            size: 16,
                            color: const Color(0xFFE65100),
                          ),
                          const SizedBox(width: 6),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Flexible(
                                      child: Text(
                                        locName.toUpperCase(),
                                        style: const TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w800,
                                          letterSpacing: 0.5,
                                          color: Color(0xFF5D4037),
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    const SizedBox(width: 6),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                                      decoration: BoxDecoration(
                                        color: isGps
                                            ? const Color(0xFF2E7D32).withValues(alpha: 0.15)
                                            : const Color(0xFF0288D1).withValues(alpha: 0.15),
                                        borderRadius: BorderRadius.circular(6),
                                        border: Border.all(
                                          color: isGps ? const Color(0xFF4CAF50) : const Color(0xFF29B6F6),
                                          width: 0.8,
                                        ),
                                      ),
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          Container(
                                            width: 5,
                                            height: 5,
                                            decoration: BoxDecoration(
                                              shape: BoxShape.circle,
                                              color: isGps ? const Color(0xFF2E7D32) : const Color(0xFF0288D1),
                                            ),
                                          ),
                                          const SizedBox(width: 3),
                                          Text(
                                            isGps ? l10n.translate('gpsLive') : l10n.translate('liveFeed'),
                                            style: TextStyle(
                                              fontSize: 8.5,
                                              fontWeight: FontWeight.w800,
                                              color: isGps ? const Color(0xFF1B5E20) : const Color(0xFF01579B),
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                                Text(
                                  l10n.translate('weatherSub'),
                                  style: const TextStyle(
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.w500,
                                    color: Color(0xFF8D6E63),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    // Refresh Button
                    InkWell(
                      onTap: isLoading ? null : () => provider.refreshLiveWeather(requestGps: true),
                      borderRadius: BorderRadius.circular(20),
                      child: Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.8),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFFFFD54F)),
                        ),
                        child: isLoading
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFE65100)),
                                ),
                              )
                            : const Icon(
                                Icons.refresh_rounded,
                                size: 16,
                                color: Color(0xFFE65100),
                              ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),

                // Main Weather Display: Temperature & Humidity Cards
                Row(
                  children: [
                    // Outside Temperature
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.75),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFFFE082)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: const Color(0xFFFFE0B2),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(
                                Icons.thermostat_rounded,
                                color: Color(0xFFE65100),
                                size: 18,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    l10n.translate('outsideTemp'),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 8.5,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF8D6E63),
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                                  FittedBox(
                                    fit: BoxFit.scaleDown,
                                    alignment: Alignment.centerLeft,
                                    child: Text(
                                      '$temp°C',
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFFBF360C),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),

                    // Outside Humidity
                    Expanded(
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.75),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFFFE082)),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(6),
                              decoration: BoxDecoration(
                                color: const Color(0xFFB3E5FC),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(
                                Icons.water_drop_rounded,
                                color: Color(0xFF0288D1),
                                size: 18,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    l10n.translate('outsideHumidity'),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 8.5,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFF8D6E63),
                                      letterSpacing: 0.3,
                                    ),
                                  ),
                                  FittedBox(
                                    fit: BoxFit.scaleDown,
                                    alignment: Alignment.centerLeft,
                                    child: Text(
                                      '${hum.toInt()}% RH',
                                      style: const TextStyle(
                                        fontSize: 16,
                                        fontWeight: FontWeight.w800,
                                        color: Color(0xFF01579B),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),

                if (!compact) ...[
                  const SizedBox(height: 8),
                  // Advisory & Condition Row
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE65100).withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              weather?.weatherIcon ?? Icons.wb_sunny_rounded,
                              size: 13,
                              color: const Color(0xFFE65100),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              condition,
                              style: const TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                                color: Color(0xFFBF360C),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          weather?.silkwormAdvisory ?? 'Live outside weather feed active.',
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF5D4037),
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      const Icon(
                        Icons.chevron_right_rounded,
                        size: 16,
                        color: Color(0xFF8D6E63),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showWeatherDetailsSheet(
    BuildContext context,
    SetuProvider provider,
    LiveWeatherData? weather,
  ) {
    final shed = provider.shedData;
    final temp = weather?.temperature ?? shed.outsideTemp;
    final hum = weather?.humidity ?? shed.outsideHumidity;

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => SafeArea(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: const Color(0xFFCFD8DC),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFF3E0),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.wb_sunny_rounded, color: Color(0xFFE65100), size: 22),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Live Microclimate Report',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800, color: Color(0xFF1B2E1E)),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      Text(
                        weather?.locationName ?? provider.region,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF757575)),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close_rounded, size: 22),
                  onPressed: () => Navigator.pop(ctx),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Detail Grid
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFF9FBE7),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFE6EE9C)),
              ),
              child: Column(
                children: [
                  _buildDetailRow('Live Outdoor Temperature', '$temp °C', Icons.thermostat_rounded, const Color(0xFFE65100)),
                  const Divider(height: 16, color: Color(0xFFE0E0E0)),
                  _buildDetailRow('Live Outdoor Humidity', '${hum.toInt()} % RH', Icons.water_drop_rounded, const Color(0xFF0288D1)),
                  if (weather?.apparentTemperature != null) ...[
                    const Divider(height: 16, color: Color(0xFFE0E0E0)),
                    _buildDetailRow('Feels Like (Heat Index)', '${weather!.apparentTemperature} °C', Icons.wb_twilight_rounded, const Color(0xFFF57C00)),
                  ],
                  if (weather?.windSpeed != null) ...[
                    const Divider(height: 16, color: Color(0xFFE0E0E0)),
                    _buildDetailRow('Wind Speed', '${weather!.windSpeed} km/h', Icons.air_rounded, const Color(0xFF00897B)),
                  ],
                  const Divider(height: 16, color: Color(0xFFE0E0E0)),
                  _buildDetailRow('Weather Condition', weather?.condition ?? 'Fair', weather?.weatherIcon ?? Icons.wb_sunny_rounded, const Color(0xFF5D4037)),
                  const Divider(height: 16, color: Color(0xFFE0E0E0)),
                  _buildDetailRow('Location Source', (weather?.isGps ?? false) ? 'Device GPS Coordinates' : 'Registered Farm Region', Icons.satellite_alt_rounded, const Color(0xFF388E3C)),
                ],
              ),
            ),
            const SizedBox(height: 14),

            // Silkworm Shed Impact Card
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: const Color(0xFFFFF8E1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: const Color(0xFFFFECB3)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.info_outline_rounded, color: Color(0xFFF57F17), size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Sericulture Impact & Action',
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: Color(0xFFBF360C)),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          weather?.silkwormAdvisory ??
                              'Outside weather directly alters shed roof temperature and tray humidity. Setu automatically runs foggers or heaters to keep worms inside at comfortable target levels.',
                          style: const TextStyle(fontSize: 11.5, color: Color(0xFF5D4037), height: 1.35),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Refresh Live Weather Button
            ElevatedButton(
              onPressed: () {
                Navigator.pop(ctx);
                provider.refreshLiveWeather(requestGps: true);
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF2E7D32),
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                elevation: 0,
              ),
              child: const Row(
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.my_location_rounded, size: 18),
                  SizedBox(width: 10),
                  Flexible(
                    child: Text(
                      'Re-detect Location & Fetch Live Weather',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 10),
          ],
        ),
      ),
    ),
  ),
);
  }

  Widget _buildDetailRow(String title, String val, IconData icon, Color iconColor) {
    return Row(
      children: [
        Icon(icon, size: 18, color: iconColor),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            title,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF455A64)),
          ),
        ),
        Text(
          val,
          style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800, color: Color(0xFF212121)),
        ),
      ],
    );
  }
}
