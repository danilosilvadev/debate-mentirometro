import 'dart:async';
import 'dart:convert';

import '../domain/models.dart';
import '../domain/scoreboard_repository.dart';
import 'placar_endpoints.dart';
import 'scoreboard_parser.dart';

/// Cliente HTTP mínimo, para o repositório e para os testes.
abstract class ScoreboardClient {
  Future<String> get(Uri uri);
}

class CallbackScoreboardClient implements ScoreboardClient {
  CallbackScoreboardClient(this._get);

  final Future<String> Function(Uri uri) _get;

  @override
  Future<String> get(Uri uri) => _get(uri);
}

class ScoreboardFetchException implements Exception {
  ScoreboardFetchException(this.message);
  final String message;

  @override
  String toString() => message;
}

/// Faz polling do `placar.json` público, no mesmo ritmo do site (6s, com
/// cache-buster a cada 3s).
class RemoteScoreboardRepository implements ScoreboardRepository {
  RemoteScoreboardRepository({
    required ScoreboardClient client,
    this.archive,
    this.pollEvery = const Duration(seconds: 6),
    DateTime Function()? clock,
    bool autostart = true,
    this.onDispose,
  })  : _client = client,
        _clock = clock ?? DateTime.now {
    _latest =
        const ScoreboardSnapshot(origin: DataOrigin.remote, loading: true);
    if (autostart) {
      _timer = Timer.periodic(pollEvery, (_) {
        unawaited(refresh());
      });
      unawaited(refresh());
    }
  }

  final ScoreboardClient _client;
  final String? archive;
  final Duration pollEvery;
  final DateTime Function() _clock;
  final void Function()? onDispose;

  final StreamController<ScoreboardSnapshot> _updates =
      StreamController<ScoreboardSnapshot>.broadcast();
  late ScoreboardSnapshot _latest;
  Timer? _timer;
  int? _lastStamp;
  var _disposed = false;

  /// Uma ida ao servidor. Os testes chamam isto com [autostart] falso.
  Future<Scoreboard> fetch() async {
    final uri = PlacarEndpoints.placar(
      archive: archive,
      cacheBust: _clock().millisecondsSinceEpoch ~/ 3000,
    );
    final body = await _client.get(uri);
    Object? decoded;
    try {
      decoded = jsonDecode(body);
    } on FormatException {
      throw ScoreboardFetchException('O placar não veio em JSON.');
    }
    return ScoreboardParser.parse(decoded);
  }

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
    if (_disposed) return;
    try {
      final board = await fetch();
      if (_disposed) return;
      if (_lastStamp == board.atualizado &&
          _latest.error == null &&
          _latest.hasBoard) {
        return;
      }
      _lastStamp = board.atualizado;
      _publish(ScoreboardSnapshot(origin: DataOrigin.remote, board: board));
    } catch (error) {
      if (_disposed) return;
      final message = error is ScoreboardFetchException
          ? error.message
          : 'Sem conexão com o placar. Tentando de novo…';
      _publish(
        ScoreboardSnapshot(
          origin: DataOrigin.remote,
          board: _latest.board,
          error: message,
          loading: false,
        ),
      );
    }
  }

  void _publish(ScoreboardSnapshot snapshot) {
    _latest = snapshot;
    if (!_updates.isClosed) _updates.add(snapshot);
  }

  @override
  void dispose() {
    _disposed = true;
    _timer?.cancel();
    onDispose?.call();
    unawaited(_updates.close());
  }
}
