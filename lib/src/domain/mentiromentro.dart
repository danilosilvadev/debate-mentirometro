import 'verdict.dart';

/// Índice de erro de um candidato.
///
/// Falso vale 1, impreciso vale 0,5, verdadeiro vale 0. O total do índice
/// só soma esses três. "Sem dados" e "Em revisão" não entram.
class ErrorIndex {
  const ErrorIndex({
    required this.total,
    required this.verdadeiroPct,
    required this.imprecisoPct,
    required this.falsoPct,
    required this.erro,
  });

  /// Fatos checáveis: verdadeiro + impreciso + falso.
  final int total;
  final int verdadeiroPct;
  final int imprecisoPct;
  final int falsoPct;

  /// De 0 a 1. `(falso + impreciso / 2) / total`, ou 0 se não houver fato.
  final double erro;

  factory ErrorIndex.fromCounts({
    required int verdadeiro,
    required int impreciso,
    required int falso,
  }) {
    final total = verdadeiro + impreciso + falso;
    int pct(int k) => total == 0 ? 0 : (k / total * 100).round();
    return ErrorIndex(
      total: total,
      verdadeiroPct: pct(verdadeiro),
      imprecisoPct: pct(impreciso),
      falsoPct: pct(falso),
      erro: total == 0 ? 0 : (falso + impreciso / 2) / total,
    );
  }

  /// Porcentagem inteira mostrada no visor (`Math.round(erro * 100)`).
  int get erroPct => (erro * 100).round();
}

/// Contagem bruta de vereditos, inclusive os que ficam fora do índice.
class VerdictTally {
  const VerdictTally({
    required this.verdadeiro,
    required this.impreciso,
    required this.falso,
    required this.semDados,
    required this.emRevisao,
  });

  final int verdadeiro;
  final int impreciso;
  final int falso;
  final int semDados;
  final int emRevisao;

  static const empty = VerdictTally(
    verdadeiro: 0,
    impreciso: 0,
    falso: 0,
    semDados: 0,
    emRevisao: 0,
  );

  factory VerdictTally.from(Iterable<Verdict> verdicts) {
    var verdadeiro = 0;
    var impreciso = 0;
    var falso = 0;
    var semDados = 0;
    var emRevisao = 0;
    for (final verdict in verdicts) {
      switch (verdict) {
        case Verdict.verdadeiro:
          verdadeiro++;
        case Verdict.impreciso:
          impreciso++;
        case Verdict.falso:
          falso++;
        case Verdict.semDados:
          semDados++;
        case Verdict.emRevisao:
          emRevisao++;
      }
    }
    return VerdictTally(
      verdadeiro: verdadeiro,
      impreciso: impreciso,
      falso: falso,
      semDados: semDados,
      emRevisao: emRevisao,
    );
  }

  ErrorIndex get index => ErrorIndex.fromCounts(
        verdadeiro: verdadeiro,
        impreciso: impreciso,
        falso: falso,
      );
}

enum NeedleCall { waiting, tie, leftErrsMore, rightErrsMore }

/// Leitura do Medidor: para quem o ponteiro pende e o texto do visor.
///
/// O ponteiro só sai do centro com pelo menos [minimo] fatos checáveis de
/// cada lado. A escala é a do site: 100 pontos de diferença no índice de
/// erro (1,0) deitam o ponteiro em 90°; 50 pontos são 45°. Negativo pende
/// para o candidato da esquerda.
class MentiromentroReading {
  const MentiromentroReading({
    required this.left,
    required this.right,
    required this.ready,
    required this.angleDegrees,
    required this.call,
    required this.headline,
    required this.detail,
    required this.basis,
  });

  static const int minimo = 3;

  final ErrorIndex left;
  final ErrorIndex right;
  final bool ready;
  final double angleDegrees;
  final NeedleCall call;
  final String headline;
  final String detail;
  final String basis;

  factory MentiromentroReading.compute({
    required String leftName,
    required String rightName,
    required int leftVerdadeiro,
    required int leftImpreciso,
    required int leftFalso,
    required int rightVerdadeiro,
    required int rightImpreciso,
    required int rightFalso,
  }) {
    final left = ErrorIndex.fromCounts(
      verdadeiro: leftVerdadeiro,
      impreciso: leftImpreciso,
      falso: leftFalso,
    );
    final right = ErrorIndex.fromCounts(
      verdadeiro: rightVerdadeiro,
      impreciso: rightImpreciso,
      falso: rightFalso,
    );
    final ready = left.total >= minimo && right.total >= minimo;
    final angle = ready ? (right.erro - left.erro) * 90 : 0.0;
    final diff = (left.erro - right.erro).abs();

    final NeedleCall call;
    final String headline;
    final String detail;
    if (!ready) {
      call = NeedleCall.waiting;
      headline = 'Esperando mais fatos';
      detail =
          'o ponteiro só se mexe com pelo menos $minimo fatos checáveis de cada lado';
    } else if (diff < 0.1) {
      call = NeedleCall.tie;
      headline = 'Empate técnico';
      detail = 'os dois erram parecido até agora';
    } else if (left.erro > right.erro) {
      call = NeedleCall.leftErrsMore;
      headline = '$leftName está errando mais';
      detail = '${left.erroPct}% contra ${right.erroPct}% de índice de erro';
    } else {
      call = NeedleCall.rightErrsMore;
      headline = '$rightName está errando mais';
      detail = '${right.erroPct}% contra ${left.erroPct}% de índice de erro';
    }

    final leftFatos = left.total == 1 ? 'fato checável' : 'fatos checáveis';
    final basis =
        'com base em ${left.total} $leftFatos de $leftName e ${right.total} de $rightName (sem dados fica de fora)';

    return MentiromentroReading(
      left: left,
      right: right,
      ready: ready,
      angleDegrees: angle,
      call: call,
      headline: headline,
      detail: detail,
      basis: basis,
    );
  }
}
