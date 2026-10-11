class GrowthStageModel {
  final int stageNumber;
  final String shortLabel;
  final String name;
  final String daysRange;
  final double tempMin;
  final double tempMax;
  final double humMin;
  final double humMax;
  final int airflowPercent;
  final int lightPercent;
  final List<String> guidancePoints;
  final String aiRecommendation;

  const GrowthStageModel({
    required this.stageNumber,
    required this.shortLabel,
    required this.name,
    required this.daysRange,
    required this.tempMin,
    required this.tempMax,
    required this.humMin,
    required this.humMax,
    required this.airflowPercent,
    required this.lightPercent,
    required this.guidancePoints,
    required this.aiRecommendation,
  });

  double get tempTarget => double.parse(((tempMin + tempMax) / 2).toStringAsFixed(1));
  double get humidityTarget => double.parse(((humMin + humMax) / 2).toStringAsFixed(1));

  static const List<GrowthStageModel> allStages = [
    GrowthStageModel(
      stageNumber: 1,
      shortLabel: "INC",
      name: "Incubation",
      daysRange: "Egg Stage",
      tempMin: 25.0,
      tempMax: 25.0,
      humMin: 75.0,
      humMax: 80.0,
      airflowPercent: 20,
      lightPercent: 15,
      guidancePoints: [
        "Keep eggs in a stable 25C incubation room without direct heat bursts.",
        "Humidity around 75-80% helps prevent desiccation before hatching.",
        "Use very soft light and minimal air disturbance during incubation.",
      ],
      aiRecommendation: "Incubation mode keeps air gentle, lighting low, and humidity stable.",
    ),
    GrowthStageModel(
      stageNumber: 2,
      shortLabel: "I",
      name: "I Instar (Chawki)",
      daysRange: "Days 1-3",
      tempMin: 28.0,
      tempMax: 28.0,
      humMin: 85.0,
      humMax: 85.0,
      airflowPercent: 25,
      lightPercent: 20,
      guidancePoints: [
        "Young worms need high humidity to prevent mulberry wilting.",
        "Maintain warm temperature for even hatching and early feeding.",
        "Cover rearing trays with paraffin paper to retain moisture.",
        "Gentle handling only; avoid sudden air or light changes."
      ],
      aiRecommendation: "Chawki stage requires warm and humid air. Micro-fogger is primed.",
    ),
    GrowthStageModel(
      stageNumber: 3,
      shortLabel: "II",
      name: "II Instar",
      daysRange: "Days 4-5",
      tempMin: 27.0,
      tempMax: 27.0,
      humMin: 85.0,
      humMax: 85.0,
      airflowPercent: 35,
      lightPercent: 25,
      guidancePoints: [
        "Temperature remains warm while air exchange can increase slightly.",
        "Observe 1st molt exit closely before resuming feeding.",
        "Feed freshly harvested, tender mulberry leaves.",
        "Keep trays clean and dusted with bed disinfectant."
      ],
      aiRecommendation: "2nd instar environment is optimal. Bed conditions remain well balanced.",
    ),
    GrowthStageModel(
      stageNumber: 4,
      shortLabel: "III",
      name: "III Instar",
      daysRange: "Days 6-9",
      tempMin: 26.0,
      tempMax: 26.0,
      humMin: 80.0,
      humMax: 80.0,
      airflowPercent: 50,
      lightPercent: 35,
      guidancePoints: [
        "Temperature should remain moderate and consistent through active feeding.",
        "Keep humidity stable while avoiding damp bed conditions.",
        "Ensure proper shed cross-ventilation during feeding hours.",
        "Avoid sudden fluctuations or direct hot drafts on trays."
      ],
      aiRecommendation: "Current shed environment is suitable for 3rd instar silkworms. No manual intervention required.",
    ),
    GrowthStageModel(
      stageNumber: 5,
      shortLabel: "IV",
      name: "IV Instar",
      daysRange: "Days 10-14",
      tempMin: 25.0,
      tempMax: 25.0,
      humMin: 70.0,
      humMax: 70.0,
      airflowPercent: 65,
      lightPercent: 40,
      guidancePoints: [
        "Voracious feeding stage: Ensure abundant mulberry supply.",
        "Lower humidity is vital to prevent flacherie bacterial rot.",
        "Run exhaust fans to clear metabolic moisture and carbon dioxide.",
        "Increase bed spacing as silkworms grow rapidly."
      ],
      aiRecommendation: "4th instar requires enhanced airflow. Ventilation fans ready for duty cycle.",
    ),
    GrowthStageModel(
      stageNumber: 6,
      shortLabel: "V",
      name: "V Instar",
      daysRange: "Days 15-20",
      tempMin: 24.0,
      tempMax: 24.0,
      humMin: 66.0,
      humMax: 70.0,
      airflowPercent: 75,
      lightPercent: 45,
      guidancePoints: [
        "Cooler, drier air is required before spinning begins.",
        "Crucial period for silk gland synthesis before spinning.",
        "Continuous gentle ventilation without disturbing worm alignment.",
        "Prepare mounting frames (chandrike) as worms turn translucent."
      ],
      aiRecommendation: "Final rearing stage. Cooling and aeration given priority over fogging.",
    ),
    GrowthStageModel(
      stageNumber: 7,
      shortLabel: "SPN",
      name: "Spinning",
      daysRange: "Days 21-24",
      tempMin: 25.0,
      tempMax: 25.0,
      humMin: 70.0,
      humMax: 70.0,
      airflowPercent: 55,
      lightPercent: 25,
      guidancePoints: [
        "Maintain a calm, clean room while worms mount evenly.",
        "Humidity should stay steady to avoid weak or stained cocoons.",
        "Keep airflow moderate and light soft during spinning."
      ],
      aiRecommendation: "Spinning mode softens lighting and keeps airflow steady for cocoon formation.",
    ),
    GrowthStageModel(
      stageNumber: 8,
      shortLabel: "COC",
      name: "Cocoon Preservation",
      daysRange: "Post-harvest",
      tempMin: 25.0,
      tempMax: 25.0,
      humMin: 80.0,
      humMax: 80.0,
      airflowPercent: 40,
      lightPercent: 15,
      guidancePoints: [
        "Keep harvested cocoons in a clean, protected holding area.",
        "Humidity control helps preserve shell quality before dispatch.",
        "Avoid harsh light and extreme air movement during storage."
      ],
      aiRecommendation: "Preservation mode prioritizes gentle storage conditions for harvested cocoons.",
    ),
  ];
}
