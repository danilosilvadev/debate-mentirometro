import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import 'data/mock_scoreboard_repository.dart';
import 'data/placar_endpoints.dart';
import 'data/remote_scoreboard_repository.dart';
import 'domain/fact_query.dart';
import 'domain/models.dart';
import 'domain/scoreboard_repository.dart';

/// `mock` (padrão) ou `live` via `--dart-define=PLACAR_SOURCE=live`.
const placarSource =
    String.fromEnvironment('PLACAR_SOURCE', defaultValue: 'mock');

enum FeedMode { simulation, live }

final feedModeProvider = StateProvider<FeedMode>((ref) {
  return placarSource == 'live' ? FeedMode.live : FeedMode.simulation;
});

/// Arquivo `placar-<id>.json`. Nulo usa o placar corrente.
final archiveProvider = StateProvider<String?>((ref) {
  final env = PlacarEndpoints.archiveFromEnv;
  return env.isEmpty ? null : env;
});

final scoreboardRepositoryProvider = Provider<ScoreboardRepository>((ref) {
  final mode = ref.watch(feedModeProvider);
  if (mode == FeedMode.simulation) {
    final repo = MockScoreboardRepository();
    ref.onDispose(repo.dispose);
    return repo;
  }
  final archive = ref.watch(archiveProvider);
  final httpClient = http.Client();
  final repo = RemoteScoreboardRepository(
    archive: archive,
    client: _PackageClient(httpClient),
    onDispose: httpClient.close,
  );
  ref.onDispose(repo.dispose);
  return repo;
});

class _PackageClient implements ScoreboardClient {
  _PackageClient(this._client);

  final http.Client _client;

  @override
  Future<String> get(Uri uri) async {
    final response = await _client.get(uri, headers: const {
      'accept': 'application/json'
    }).timeout(const Duration(seconds: 15));
    if (response.statusCode != 200) {
      throw ScoreboardFetchException(
        'Não foi possível baixar o placar (HTTP ${response.statusCode}).',
      );
    }
    return response.body;
  }
}

final scoreboardProvider = StreamProvider<ScoreboardSnapshot>((ref) {
  return ref.watch(scoreboardRepositoryProvider).watch();
});

final factFilterProvider =
    StateProvider<FactFilter>((ref) => const FactFilter());

final selectedFactIdProvider = StateProvider<String?>((ref) => null);

void selectFeedMode(WidgetRef ref, FeedMode mode) {
  ref.read(feedModeProvider.notifier).state = mode;
  ref.read(factFilterProvider.notifier).state = const FactFilter();
  ref.read(selectedFactIdProvider.notifier).state = null;
}
