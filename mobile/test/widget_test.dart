import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:sericare/main.dart';
import 'package:sericare/providers/sericare_provider.dart';

void main() {
  testWidgets('SeriCareApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => SeriCareProvider(),
        child: const SeriCareApp(),
      ),
    );
    expect(find.byType(SeriCareApp), findsOneWidget);
  });
}
