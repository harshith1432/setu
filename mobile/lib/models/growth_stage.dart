class GrowthStageModel {
  final int stageNumber;
  final String name;
  final String daysRange;
  final double tempMin;
  final double tempMax;
  final double humMin;
  final double humMax;
  final List<String> guidancePoints;
  final String aiRecommendation;

  const GrowthStageModel({
    required this.stageNumber,
    required this.name,
    required this.daysRange,
    required this.tempMin,
    required this.tempMax,
    required this.humMin,
    required this.humMax,
    required this.guidancePoints,
    required this.aiRecommendation,
  });

  static const List<GrowthStageModel> allStages = [
    GrowthStageModel(
      stageNumber: 1,
      name: "1st Instar (Chawki)",
      daysRange: "Days 1–3",
      tempMin: 27.0,
      tempMax: 28.0,
      humMin: 80.0,
      humMax: 85.0,
      guidancePoints: [
        "Young worms need high humidity (80-85%) to prevent mulberry wilting.",
        "Maintain warm temperature (27-28°C) for even hatching and growth.",
        "Cover rearing trays with paraffin paper to retain moisture.",
        "Gentle handling only; strictly avoid sudden room temperature drops."
      ],
      aiRecommendation: "Chawki stage requires warm and humid air. Micro-fogger is primed.",
    ),
    GrowthStageModel(
      stageNumber: 2,
      name: "2nd Instar",
      daysRange: "Days 4–5",
      tempMin: 26.5,
      tempMax: 27.5,
      humMin: 75.0,
      humMax: 80.0,
      guidancePoints: [
        "Slightly reduce humidity compared to 1st instar.",
        "Observe 1st molt exit closely before resuming feeding.",
        "Feed freshly harvested, tender mulberry leaves.",
        "Keep trays clean and dusted with bed disinfectant."
      ],
      aiRecommendation: "2nd instar environment is optimal. Bed conditions remain well balanced.",
    ),
    GrowthStageModel(
      stageNumber: 3,
      name: "3rd Instar",
      daysRange: "Days 6–9",
      tempMin: 25.0,
      tempMax: 26.5,
      humMin: 70.0,
      humMax: 75.0,
      guidancePoints: [
        "Ideal temperature: Moderate and consistent (25-26.5°C).",
        "Keep humidity stable (70-75%); prevent damp bed conditions.",
        "Ensure proper shed cross-ventilation during feeding hours.",
        "Avoid sudden fluctuations or direct hot drafts on trays."
      ],
      aiRecommendation: "Current shed environment is suitable for 3rd instar silkworms. No manual intervention required.",
    ),
    GrowthStageModel(
      stageNumber: 4,
      name: "4th Instar",
      daysRange: "Days 10–14",
      tempMin: 24.0,
      tempMax: 25.5,
      humMin: 65.0,
      humMax: 70.0,
      guidancePoints: [
        "Voracious feeding stage: Ensure abundant mulberry supply.",
        "Lower humidity (65-70%) is vital to prevent flacherie bacterial rot.",
        "Run exhaust fans to clear metabolic moisture and carbon dioxide.",
        "Increase bed spacing as silkworms grow rapidly."
      ],
      aiRecommendation: "4th instar requires enhanced airflow. Ventilation fans ready for duty cycle.",
    ),
    GrowthStageModel(
      stageNumber: 5,
      name: "5th Instar",
      daysRange: "Days 15–20",
      tempMin: 23.0,
      tempMax: 24.5,
      humMin: 60.0,
      humMax: 65.0,
      guidancePoints: [
        "Cooler, dry air required (23-24°C, 60-65% RH).",
        "Crucial period for silk gland synthesis before spinning.",
        "Continuous gentle ventilation without disturbing worm alignment.",
        "Prepare mounting frames (chandrike) as worms turn translucent."
      ],
      aiRecommendation: "Final rearing stage. Cooling and aeration given priority over fogging.",
    ),
  ];
}
