import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:setu/main.dart';
import 'package:setu/providers/setu_provider.dart';

void main() {
  testWidgets('SetuApp smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(
      ChangeNotifierProvider(
        create: (_) => SetuProvider(),
        child: const SetuApp(),
      ),
    );
    expect(find.byType(SetuApp), findsOneWidget);
  });
}
