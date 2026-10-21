/// JSON público do Placar da Verdade.
///
/// O site baixa `placar.json` a cada poucos segundos (cache de 3s) e, com
/// `?d=`, um arquivo de debate passado: `placar-<arquivo>.json`.
class PlacarEndpoints {
  const PlacarEndpoints._();

  static const defaultBase = 'https://placar-dados.zenithonacademy.com.br/';

  /// `--dart-define=PLACAR_BASE=https://exemplo.com/`
  static const base = String.fromEnvironment(
    'PLACAR_BASE',
    defaultValue: defaultBase,
  );

  /// `--dart-define=PLACAR_ARCHIVE=2026-10-18` abre `placar-2026-10-18.json`.
  static const archiveFromEnv = String.fromEnvironment('PLACAR_ARCHIVE');

  static final _archiveOk = RegExp(r'^[\w-]{1,40}$');

  static String normalizedBase() {
    final trimmed = base.trim();
    if (trimmed.isEmpty) return defaultBase;
    return trimmed.endsWith('/') ? trimmed : '$trimmed/';
  }

  static Uri placar({String? archive, required int cacheBust}) {
    final chosen =
        (archive != null && archive.isNotEmpty) ? archive : archiveFromEnv;
    final name =
        _archiveOk.hasMatch(chosen) ? 'placar-$chosen.json' : 'placar.json';
    return Uri.parse('${normalizedBase()}$name').replace(
      queryParameters: {'t': '$cacheBust'},
    );
  }

  static String describe({String? archive}) {
    final uri = placar(archive: archive, cacheBust: 0);
    return uri.replace(queryParameters: {}).toString();
  }
}
