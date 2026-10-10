class ActuatorStates {
  final bool cooler;
  final bool fan;
  final bool heater;

  ActuatorStates({
    this.cooler = false,
    this.fan = false,
    this.heater = false,
  });

  factory ActuatorStates.fromJson(Map<String, dynamic> json) {
    return ActuatorStates(
      cooler: json['cooler'] ?? false,
      fan: json['fan'] ?? false,
      heater: json['heater'] ?? false,
    );
  }
}

class ShedData {
  final String shedId;
  final String farmName;
  final String region;
  final String overallStatus;
  final String statusHeadline;
  final String statusSubline;
  final int currentStage;
  final String stageName;
  final double indoorTemp;
  final double indoorHumidity;
  final double outsideTemp;
  final double outsideHumidity;
  final ActuatorStates actuators;
  final bool isAutoMode;
  final double tempTarget;
  final double humidityTarget;
  final DateTime lastUpdated;

  ShedData({
    required this.shedId,
    required this.farmName,
    required this.region,
    required this.overallStatus,
    required this.statusHeadline,
    required this.statusSubline,
    required this.currentStage,
    required this.stageName,
    required this.indoorTemp,
    required this.indoorHumidity,
    required this.outsideTemp,
    required this.outsideHumidity,
    required this.actuators,
    required this.isAutoMode,
    required this.tempTarget,
    required this.humidityTarget,
    required this.lastUpdated,
  });

  factory ShedData.fromJson(Map<String, dynamic> json) {
    return ShedData(
      shedId: json['shed_id'] ?? 'shed_01',
      farmName: json['farm_name'] ?? 'Green Valley Farm',
      region: json['region'] ?? 'Mulbagal, Karnataka',
      overallStatus: json['overall_status'] ?? 'IDEAL',
      statusHeadline: json['status_headline'] ?? 'Ideal for Silkworms',
      statusSubline: json['status_subline'] ?? 'Everything is normal',
      currentStage: json['current_stage'] ?? 3,
      stageName: json['stage_name'] ?? '3rd Instar',
      indoorTemp: (json['indoor_temp'] as num?)?.toDouble() ?? 26.2,
      indoorHumidity: (json['indoor_humidity'] as num?)?.toDouble() ?? 74.0,
      outsideTemp: (json['outside_temp'] as num?)?.toDouble() ?? 34.2,
      outsideHumidity: (json['outside_humidity'] as num?)?.toDouble() ?? 58.0,
      actuators: ActuatorStates.fromJson(json['actuators'] ?? {}),
      isAutoMode: json['is_auto_mode'] ?? true,
      tempTarget: (json['temp_target'] as num?)?.toDouble() ?? 26.0,
      humidityTarget: (json['humidity_target'] as num?)?.toDouble() ?? 75.0,
      lastUpdated: DateTime.tryParse(json['last_updated'] ?? '') ?? DateTime.now(),
    );
  }
}
