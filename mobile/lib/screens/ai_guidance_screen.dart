import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/sericare_provider.dart';
import '../l10n/app_localizations.dart';

class AiGuidanceScreen extends StatefulWidget {
  const AiGuidanceScreen({Key? key}) : super(key: key);

  @override
  State<AiGuidanceScreen> createState() => _AiGuidanceScreenState();
}

class _AiGuidanceScreenState extends State<AiGuidanceScreen> {
  String? _selectedQueryAnswer;

  final Map<String, String> _qaAnswers = {
    'feeding': '🍃 3rd Instar feeding tips: Offer chopped V-1 or M-5 mulberry leaves 3 times daily. High moisture leaves (>70%) maintain worm vigor.',
    'molting': '😴 3rd molt occurs around Day 8–9. Stop feeding as worms turn shiny and raise their heads. Keep shed completely dry and well ventilated during molting.',
    'weather': '🌧️ Monsoon / high rainfall lowers temperature but raises humidity (>85%). Keep exhaust fans on standby to prevent fungal flacherie.'
  };

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<SeriCareProvider>(context);
    final advice = provider.aiAdvice;
    final l10n = AppLocalizations.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: const BoxDecoration(
                  color: Color(0xFF7B1FA2),
                  shape: BoxShape.circle,
                ),
                child: const Center(child: Text('🤖', style: TextStyle(fontSize: 24))),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.translate('aiTitle'),
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      color: Color(0xFF4A148C),
                    ),
                  ),
                  const Text(
                    'Real-time explainable actions for Mulbagal farmers',
                    style: TextStyle(fontSize: 11, color: Color(0xFF5A695C)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Speech Bubble: Why is this action happening?
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFEDE7F6), Color(0xFFD1C4E9)],
              ),
              borderRadius: BorderRadius.circular(20),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.translate('whyHeader'),
                  style: const TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF512DA8),
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '"${advice.whyText}"',
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFF311B92),
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Current Action Card (Visual & Clear)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFF80DEEA), width: 1.5),
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: const BoxDecoration(
                    color: Color(0xFFE0F7FA),
                    shape: BoxShape.circle,
                  ),
                  child: const Center(child: Text('❄️', style: TextStyle(fontSize: 24))),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        advice.currentAction,
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        advice.targetDescription,
                        style: const TextStyle(fontSize: 12, color: Color(0xFF00796B), fontWeight: FontWeight.w600),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Key Points (Short 1-liners)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFFE0E7DC)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text('💡 ', style: TextStyle(fontSize: 16)),
                    Text(
                      l10n.translate('whatThisMeans'),
                      style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                ...advice.bulletPoints.take(2).map((pt) => Padding(
                      padding: const EdgeInsets.only(bottom: 6.0),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Container(
                            margin: const EdgeInsets.only(top: 5, right: 8),
                            width: 6,
                            height: 6,
                            decoration: const BoxDecoration(
                              color: Color(0xFF2E7D32),
                              shape: BoxShape.circle,
                            ),
                          ),
                          Expanded(
                            child: Text(
                              pt,
                              style: const TextStyle(fontSize: 12, color: Color(0xFF334135)),
                            ),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Interactive Q&A
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFFF3E5F5),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Ask SeriCare Assistant',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                    color: Color(0xFF6A1B9A),
                  ),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    _buildQuestionChip('🍃 Feeding tips?', 'feeding'),
                    _buildQuestionChip('😴 When does 3rd molt start?', 'molting'),
                    _buildQuestionChip('🌧️ Rain impact?', 'weather'),
                  ],
                ),
                if (_selectedQueryAnswer != null) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: const Border(left: BorderSide(color: Color(0xFF7B1FA2), width: 3)),
                    ),
                    child: Text(
                      _selectedQueryAnswer!,
                      style: const TextStyle(fontSize: 11, color: Color(0xFF4A148C)),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildQuestionChip(String label, String key) {
    return InkWell(
      onTap: () {
        setState(() {
          _selectedQueryAnswer = _qaAnswers[key];
        });
      },
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFCE93D8)),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF6A1B9A)),
        ),
      ),
    );
  }
}
