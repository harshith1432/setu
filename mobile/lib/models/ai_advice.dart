class AIAdvice {
  final String whyText;
  final String currentAction;
  final String targetDescription;
  final List<String> bulletPoints;
  final String language;

  AIAdvice({
    required this.whyText,
    required this.currentAction,
    required this.targetDescription,
    required this.bulletPoints,
    required this.language,
  });

  factory AIAdvice.fromJson(Map<String, dynamic> json) {
    return AIAdvice(
      whyText: json['why_text'] ?? '',
      currentAction: json['current_action'] ?? '',
      targetDescription: json['target_description'] ?? '',
      bulletPoints: List<String>.from(json['bullet_points'] ?? []),
      language: json['language'] ?? 'en',
    );
  }

  AIAdvice copyWith({
    String? whyText,
    String? currentAction,
    String? targetDescription,
    List<String>? bulletPoints,
    String? language,
  }) {
    return AIAdvice(
      whyText: whyText ?? this.whyText,
      currentAction: currentAction ?? this.currentAction,
      targetDescription: targetDescription ?? this.targetDescription,
      bulletPoints: bulletPoints ?? this.bulletPoints,
      language: language ?? this.language,
    );
  }
}
