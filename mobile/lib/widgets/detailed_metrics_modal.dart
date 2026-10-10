import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/setu_provider.dart';

class DetailedMetricsModal extends StatelessWidget {
  const DetailedMetricsModal({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SetuProvider>(context);
    final shed = provider.shedData;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Center(
            child: Container(
              width: 36,
              height: 4,
              decoration: BoxDecoration(
                color: const Color(0xFFCFD8DC),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Detailed Metrics',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 20),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const SizedBox(height: 14),

          _buildMetricRow('Current Shed Temperature', '${shed.indoorTemp} °C'),
          _buildMetricRow('Current Shed Humidity', '${shed.indoorHumidity.toInt()} %'),
          _buildMetricRow('Live Outside Temperature', '${shed.outsideTemp} °C'),
          _buildMetricRow('Live Outside Humidity', '${shed.outsideHumidity.toInt()} %'),
          _buildMetricRow('Current User Location', provider.liveWeather?.locationName ?? provider.region),
          _buildMetricRow('Weather Data Source', (provider.liveWeather?.isGps ?? false) ? '● Device GPS Live' : '● Internet Live Feed', isGreen: true),
          _buildMetricRow('System Status', shed.actuators.cooler ? '● Cooling ON' : '● Normal Standby', isGreen: true),
          _buildMetricRow('ESP32 Node IP & Ping', '192.168.1.104 (22 ms)'),
          const SizedBox(height: 14),
        ],
      ),
    );
  }

  Widget _buildMetricRow(String label, String value, {bool isGreen = false}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F7F2),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, color: Color(0xFF37474F)),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: isGreen ? const Color(0xFF2E7D32) : const Color(0xFF1C251D),
            ),
          ),
        ],
      ),
    );
  }
}
