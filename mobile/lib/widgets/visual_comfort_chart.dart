import 'package:flutter/material.dart';

class VisualComfortChart extends StatelessWidget {
  final String title;
  final String currentVal;
  final String idealZoneText;
  final String topLabel;
  final String midLabel;
  final String bottomLabel;
  final Color lineColor;
  final List<double> normalizedPoints; // 0.0 to 1.0 (0.0 is top/hot, 1.0 is bottom/cool)

  const VisualComfortChart({
    super.key,
    required this.title,
    required this.currentVal,
    required this.idealZoneText,
    required this.topLabel,
    required this.midLabel,
    required this.bottomLabel,
    required this.lineColor,
    required this.normalizedPoints,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
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
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF5A695C)),
                  ),
                  Row(
                    children: [
                      Text(
                        currentVal,
                        style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: const Text(
                          'Ideal',
                          style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Color(0xFF1B5E20)),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
              Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      color: const Color(0xFF4CAF50).withValues(alpha: 0.25),
                      border: Border.all(color: const Color(0xFF2E7D32)),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                  const SizedBox(width: 5),
                  Text(
                    idealZoneText,
                    style: const TextStyle(fontSize: 10, color: Color(0xFF5A695C)),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Custom Painted Chart Area
          Row(
            children: [
              // Y-Axis Labels
              SizedBox(
                width: 52,
                height: 110,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(topLabel, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFFC62828))),
                    Text(midLabel, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFF2E7D32))),
                    Text(bottomLabel, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700, color: Color(0xFF0288D1))),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              // Chart Canvas
              Expanded(
                child: SizedBox(
                  height: 110,
                  child: CustomPaint(
                    painter: _ChartPainter(lineColor: lineColor, points: normalizedPoints),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),

          // X-Axis Labels
          const Padding(
            padding: EdgeInsets.only(left: 60.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('6 AM', style: TextStyle(fontSize: 9, color: Color(0xFF5A695C))),
                Text('12 PM', style: TextStyle(fontSize: 9, color: Color(0xFF5A695C))),
                Text('6 PM', style: TextStyle(fontSize: 9, color: Color(0xFF5A695C))),
                Text('12 AM', style: TextStyle(fontSize: 9, color: Color(0xFF5A695C))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChartPainter extends CustomPainter {
  final Color lineColor;
  final List<double> points;

  _ChartPainter({required this.lineColor, required this.points});

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Draw Shaded Ideal Comfort Band (from 35% to 65% of height)
    final bandPaint = Paint()
      ..color = const Color(0xFF4CAF50).withValues(alpha: 0.18)
      ..style = PaintingStyle.fill;
    
    final bandRect = Rect.fromLTWH(0, size.height * 0.35, size.width, size.height * 0.32);
    canvas.drawRRect(RRect.fromRectAndRadius(bandRect, const Radius.circular(4)), bandPaint);

    // 2. Ideal Boundary lines
    final dashPaint = Paint()
      ..color = const Color(0xFF4CAF50).withValues(alpha: 0.5)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;
    canvas.drawLine(Offset(0, size.height * 0.35), Offset(size.width, size.height * 0.35), dashPaint);
    canvas.drawLine(Offset(0, size.height * 0.67), Offset(size.width, size.height * 0.67), dashPaint);

    if (points.isEmpty) return;

    // 3. Draw Spline / Curve
    final path = Path();
    final stepX = size.width / (points.length - 1);

    for (int i = 0; i < points.length; i++) {
      final x = i * stepX;
      final y = points[i] * size.height;
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        final prevX = (i - 1) * stepX;
        final prevY = points[i - 1] * size.height;
        final midX = (prevX + x) / 2;
        path.cubicTo(midX, prevY, midX, y, x, y);
      }
    }

    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 3.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(path, linePaint);

    // 4. Current indicator dot
    final lastIdx = (points.length / 2).floor();
    final dotX = lastIdx * stepX;
    final dotY = points[lastIdx] * size.height;

    final dotPaint = Paint()..color = lineColor;
    final dotBorder = Paint()
      ..color = Colors.white
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    canvas.drawCircle(Offset(dotX, dotY), 5, dotPaint);
    canvas.drawCircle(Offset(dotX, dotY), 5, dotBorder);
  }

  @override
  bool shouldRepaint(covariant _ChartPainter oldDelegate) => true;
}
