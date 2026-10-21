import 'models.dart';

/// Origem do placar. A UI só conhece este contrato.
///
/// Há duas implementações no app: a simulação local, que anda sozinha, e o
/// placar publicado, que faz polling do JSON público. Uma fonte nova
/// (WebSocket, arquivo, outro host) entra implementando esta classe e
/// registrando em `scoreboardRepositoryProvider`.
abstract class ScoreboardRepository {
  Stream<ScoreboardSnapshot> watch();

  /// Busca de novo agora. Na simulação, revela o próximo evento.
  Future<void> refresh();

  void dispose();
}
