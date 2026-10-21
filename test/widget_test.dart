import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:placar_da_verdade/src/app.dart';
import 'package:placar_da_verdade/src/data/mock_debate.dart';
import 'package:placar_da_verdade/src/domain/models.dart';
import 'package:placar_da_verdade/src/domain/scoreboard_repository.dart';
import 'package:placar_da_verdade/src/providers.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('o placar mostra o medidor, a linha do tempo e as propostas',
      (tester) async {
    final board = buildSimulatedBoard(
      revealed: simulationInitialReveal,
      now: DateTime.utc(2026, 10, 21, 23),
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          scoreboardRepositoryProvider.overrideWith((ref) {
            final repo = _StaticRepo(board);
            ref.onDispose(repo.dispose);
            return repo;
          }),
        ],
        child: const PlacarApp(),
      ),
    );
    await tester.pump();

    expect(find.text('Mentirômetro'), findsOneWidget);
    expect(find.text('Propostas ou ataques?'), findsOneWidget);
    expect(find.text('Linha do tempo'), findsOneWidget);
    expect(find.text('Como funciona'), findsOneWidget);
    expect(find.textContaining('fatos fictícios'), findsWidgets);
    expect(find.text('Lula'), findsWidgets);
    expect(find.text('Flávio Bolsonaro'), findsWidgets);

    await tester.ensureVisible(find.byKey(const Key('open-proposals')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('open-proposals')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(
      find.text('Reajustar o salário mínimo pela inflação e pelo PIB'),
      findsOneWidget,
    );
    expect(find.text('Citada 2 vezes'), findsOneWidget);

    await tester.tap(find.byTooltip('Voltar ao placar'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    final firstColumn = find.byKey(
      Key('timeline-1-${simulationOrigin.millisecondsSinceEpoch}'),
    );
    await tester.ensureVisible(firstColumn);
    await tester.pump();
    await tester.tap(firstColumn);
    await tester.pump();
    expect(find.textContaining('✕'), findsWidgets);
  });
}

class _StaticRepo implements ScoreboardRepository {
  _StaticRepo(this.board);

  final Scoreboard board;

  @override
  Stream<ScoreboardSnapshot> watch() {
    return Stream<ScoreboardSnapshot>.multi((listener) {
      listener.add(
        ScoreboardSnapshot(origin: DataOrigin.simulation, board: board),
      );
    });
  }

  @override
  Future<void> refresh() async {}

  @override
  void dispose() {}
}
