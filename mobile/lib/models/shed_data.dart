class ActuatorStates {
  final bool cooler;
  final bool fan;
  final bool heater;
  final bool light;
  final int lightBrightness;

  ActuatorStates({
    this.cooler = false,
    this.fan = false,
    this.heater = false,
    this.light = false,
    this.lightBrightness = 0,
  });

  factory ActuatorStates.fromJson(Map<String, dynamic> json) {
    return ActuatorStates(
      cooler: json['cooler'] ?? false,
      fan: json['fan'] ?? false,
      heater: json['heater'] ?? false,
      light: json['light'] ?? false,
      lightBrightness: json['light_brightness'] ?? (json['light'] == true ? 35 : 0),
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
  final double indoorAirQuality;
  final double indoorLightLux;
  final double outsideTemp;
  final double outsideHumidity;
  final ActuatorStates actuators;
  final bool isAutoMode;
  final bool isAdvancedMode;
  final double tempTarget;
  final double humidityTarget;
  final double airflowTarget;
  final double lightTarget;
  final double airQualityTarget;
  final double lightLuxTarget;
  final String photoperiodMode;
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
    this.indoorAirQuality = 88.0,
    this.indoorLightLux = 22.0,
    required this.outsideTemp,
    required this.outsideHumidity,
    required this.actuators,
    required this.isAutoMode,
    this.isAdvancedMode = false,
    required this.tempTarget,
    required this.humidityTarget,
    this.airflowTarget = 50.0,
    this.lightTarget = 30.0,
    this.airQualityTarget = 80.0,
    this.lightLuxTarget = 25.0,
    this.photoperiodMode = 'DAY',
    required this.lastUpdated,
  });

  factory ShedData.fromJson(Map<String, dynamic> json) {
    return ShedData(
      shedId: json['shed_id'] ?? 'shed_01',
      farmName: json['farm_name'] ?? 'Green Valley Farm',
      region: json['region'] ?? 'My Rearing Shed',
      overallStatus: json['overall_status'] ?? 'IDEAL',
      statusHeadline: json['status_headline'] ?? 'Ideal for Silkworms',
      statusSubline: json['status_subline'] ?? 'Everything is normal',
      currentStage: json['current_stage'] ?? 4,
      stageName: json['stage_name'] ?? 'III Instar',
      indoorTemp: (json['indoor_temp'] as num?)?.toDouble() ?? 26.2,
      indoorHumidity: (json['indoor_humidity'] as num?)?.toDouble() ?? 74.0,
      indoorAirQuality: (json['indoor_air_quality'] as num?)?.toDouble() ?? 88.0,
      indoorLightLux: (json['indoor_light_lux'] as num?)?.toDouble() ?? 22.0,
      outsideTemp: (json['outside_temp'] as num?)?.toDouble() ?? 34.2,
      outsideHumidity: (json['outside_humidity'] as num?)?.toDouble() ?? 58.0,
      actuators: ActuatorStates.fromJson(json['actuators'] ?? {}),
      isAutoMode: json['is_auto_mode'] ?? true,
      isAdvancedMode: json['is_advanced_mode'] ?? false,
      tempTarget: (json['temp_target'] as num?)?.toDouble() ?? 26.0,
      humidityTarget: (json['humidity_target'] as num?)?.toDouble() ?? 80.0,
      airflowTarget: (json['airflow_target'] as num?)?.toDouble() ?? 50.0,
      lightTarget: (json['light_target'] as num?)?.toDouble() ?? 35.0,
      airQualityTarget: (json['air_quality_target'] as num?)?.toDouble() ?? 80.0,
      lightLuxTarget: (json['light_lux_target'] as num?)?.toDouble() ?? 25.0,
      photoperiodMode: json['photoperiod_mode'] ?? 'DAY',
      lastUpdated: DateTime.tryParse(json['last_updated'] ?? '') ?? DateTime.now(),
    );
  }

  ShedData copyWith({
    String? shedId,
    String? farmName,
    String? region,
    String? overallStatus,
    String? statusHeadline,
    String? statusSubline,
    int? currentStage,
    String? stageName,
    double? indoorTemp,
    double? indoorHumidity,
    double? indoorAirQuality,
    double? indoorLightLux,
    double? outsideTemp,
    double? outsideHumidity,
    ActuatorStates? actuators,
    bool? isAutoMode,
    bool? isAdvancedMode,
    double? tempTarget,
    double? humidityTarget,
    double? airflowTarget,
    double? lightTarget,
    double? airQualityTarget,
    double? lightLuxTarget,
    String? photoperiodMode,
    DateTime? lastUpdated,
  }) {
    return ShedData(
      shedId: shedId ?? this.shedId,
      farmName: farmName ?? this.farmName,
      region: region ?? this.region,
      overallStatus: overallStatus ?? this.overallStatus,
      statusHeadline: statusHeadline ?? this.statusHeadline,
      statusSubline: statusSubline ?? this.statusSubline,
      currentStage: currentStage ?? this.currentStage,
      stageName: stageName ?? this.stageName,
      indoorTemp: indoorTemp ?? this.indoorTemp,
      indoorHumidity: indoorHumidity ?? this.indoorHumidity,
      indoorAirQuality: indoorAirQuality ?? this.indoorAirQuality,
      indoorLightLux: indoorLightLux ?? this.indoorLightLux,
      outsideTemp: outsideTemp ?? this.outsideTemp,
      outsideHumidity: outsideHumidity ?? this.outsideHumidity,
      actuators: actuators ?? this.actuators,
      isAutoMode: isAutoMode ?? this.isAutoMode,
      isAdvancedMode: isAdvancedMode ?? this.isAdvancedMode,
      tempTarget: tempTarget ?? this.tempTarget,
      humidityTarget: humidityTarget ?? this.humidityTarget,
      airflowTarget: airflowTarget ?? this.airflowTarget,
      lightTarget: lightTarget ?? this.lightTarget,
      airQualityTarget: airQualityTarget ?? this.airQualityTarget,
      lightLuxTarget: lightLuxTarget ?? this.lightLuxTarget,
      photoperiodMode: photoperiodMode ?? this.photoperiodMode,
      lastUpdated: lastUpdated ?? this.lastUpdated,
    );
  }
}
