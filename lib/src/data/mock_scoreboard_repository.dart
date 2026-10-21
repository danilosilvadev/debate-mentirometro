import 'dart:async';

import '../domain/models.dart';
import '../domain/scoreboard_repository.dart';
import 'mock_debate.dart';

/// Placar fictício que anda sozinho, sem rede.
///
/// Abre no meio do debate e, a cada [step], publica um fato, ataque ou
/// proposta novo. Quando o roteiro acaba, o relógio do debate continua.
class MockScoreboardRepository implements ScoreboardRepository {
  MockScoreboardRepository({
    this.step = const Duration(seconds: 3),
    DateTime Function()? clock,
    bool autostart = true,
    int? initialRevealed,
  })  : _clock = clock ?? DateTime.now,
        _revealed = initialRevealed ?? simulationInitialReveal {
    _emit();
    if (autostart) {
      _timer = Timer.periodic(step, (_) => _advance());
    }
  }

  final Duration step;
  final DateTime Function() _clock;
  int _revealed;
  DateTime? _finishedAt;
  Timer? _timer;
  var _disposed = false;

  final StreamController<ScoreboardSnapshot> _updates =
      StreamController<ScoreboardSnapshot>.broadcast();
  late ScoreboardSnapshot _latest;

  @override
  Stream<ScoreboardSnapshot> watch() {
    return Stream<ScoreboardSnapshot>.multi((listener) {
      listener.add(_latest);
      final sub = _updates.stream.listen(
        listener.add,
        onError: listener.addError,
      );
      listener.onCancel = sub.cancel;
    });
  }

  @override
  Future<void> refresh() async {
    _advance();
  }

  void _advance() {
    if (_disposed) return;
    if (_revealed < simulatedEvents.length) {
      _revealed += 1;
      if (_revealed >= simulatedEvents.length) {
        _finishedAt ??= _clock();
      }
    } else {
      _finishedAt ??= _clock();
    }
    _emit();
  }

  void _emit() {
    final board = buildSimulatedBoard(
      revealed: _revealed,
      now: _clock(),
      finishedAt: _finishedAt,
    );
    _latest = ScoreboardSnapshot(origin: DataOrigin.simulation, board: board);
    if (!_updates.isClosed) _updates.add(_latest);
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    unawaited(_updates.close());
  }
}
