import 'package:flutter_test/flutter_test.dart';
import 'package:placar_da_verdade/src/domain/mentiromentro.dart';
import 'package:placar_da_verdade/src/domain/verdict.dart';

void main() {
  test('falso vale 1, impreciso vale meio e verdadeiro vale 0', () {
    final index = ErrorIndex.fromCounts(verdadeiro: 2, impreciso: 2, falso: 2);
    expect(index.total, 6);
    expect(index.erro, 0.5);
    expect(index.erroPct, 50);
  });

  test('arredonda as fatias da barra como o placar web', () {
    final thirds = ErrorIndex.fromCounts(verdadeiro: 1, impreciso: 1, falso: 1);
    expect(thirds.verdadeiroPct, 33);
    expect(thirds.imprecisoPct, 33);
    expect(thirds.falsoPct, 33);

    final twoThirds =
        ErrorIndex.fromCounts(verdadeiro: 2, impreciso: 0, falso: 1);
    expect(twoThirds.verdadeiroPct, 67);
    expect(twoThirds.falsoPct, 33);
  });

  test('sem total o índice fica em zero e o visor não inventa porcentagem', () {
    final index = ErrorIndex.fromCounts(verdadeiro: 0, impreciso: 0, falso: 0);
    expect(index.erro, 0);
    expect(index.erroPct, 0);
    expect(index.verdadeiroPct, 0);
  });

  test('sem dados e em revisão não mudam o índice', () {
    const base = [
      Verdict.falso,
      Verdict.impreciso,
      Verdict.impreciso,
      Verdict.verdadeiro,
    ];
    final clean = VerdictTally.from(base);
    final noisy = VerdictTally.from([
      ...base,
      Verdict.semDados,
      Verdict.semDados,
      Verdict.emRevisao,
    ]);

    expect(noisy.index.erro, clean.index.erro);
    expect(noisy.index.total, 4);
    expect(noisy.index.erro, 0.5);
    expect(noisy.semDados, 2);
    expect(noisy.emRevisao, 1);
    expect(clean.semDados, 0);
  });

  test('o ponteiro só sai do centro com 3 fatos checáveis de cada lado', () {
    final waiting = MentiromentroReading.compute(
      leftName: 'Lula',
      rightName: 'Flávio Bolsonaro',
      leftVerdadeiro: 2,
      leftImpreciso: 0,
      leftFalso: 0,
      rightVerdadeiro: 0,
      rightImpreciso: 0,
      rightFalso: 10,
    );
    expect(waiting.ready, isFalse);
    expect(waiting.angleDegrees, 0);
    expect(waiting.call, NeedleCall.waiting);
    expect(waiting.headline, 'Esperando mais fatos');
    expect(
      waiting.detail,
      'o ponteiro só se mexe com pelo menos 3 fatos checáveis de cada lado',
    );
    expect(waiting.basis, contains('sem dados fica de fora'));
  });

  test('50 pontos de diferença no índice inclinam o ponteiro 45 graus', () {
    final reading = MentiromentroReading.compute(
      leftName: 'A',
      rightName: 'B',
      leftVerdadeiro: 3,
      leftImpreciso: 0,
      leftFalso: 0,
      rightVerdadeiro: 2,
      rightImpreciso: 0,
      rightFalso: 2,
    );
    expect(reading.ready, isTrue);
    expect(reading.angleDegrees, 45);
    expect(reading.call, NeedleCall.rightErrsMore);
    expect(reading.headline, 'B está errando mais');
    expect(reading.detail, '50% contra 0% de índice de erro');
  });

  test('quem erra mais à esquerda puxa o ponteiro para a esquerda', () {
    final reading = MentiromentroReading.compute(
      leftName: 'A',
      rightName: 'B',
      leftVerdadeiro: 0,
      leftImpreciso: 0,
      leftFalso: 4,
      rightVerdadeiro: 4,
      rightImpreciso: 0,
      rightFalso: 0,
    );
    expect(reading.angleDegrees, -90);
    expect(reading.call, NeedleCall.leftErrsMore);
    expect(reading.headline, 'A está errando mais');
    expect(reading.detail, '100% contra 0% de índice de erro');
    expect(reading.basis,
        'com base em 4 fatos checáveis de A e 4 de B (sem dados fica de fora)');
  });

  test('diferença menor que 10 pontos é empate técnico', () {
    final tie = MentiromentroReading.compute(
      leftName: 'A',
      rightName: 'B',
      leftVerdadeiro: 10,
      leftImpreciso: 0,
      leftFalso: 0,
      rightVerdadeiro: 9,
      rightImpreciso: 1,
      rightFalso: 0,
    );
    expect(tie.right.erro, closeTo(0.05, 0.0001));
    expect(tie.call, NeedleCall.tie);
    expect(tie.headline, 'Empate técnico');
    expect(tie.detail, 'os dois erram parecido até agora');

    final notTie = MentiromentroReading.compute(
      leftName: 'A',
      rightName: 'B',
      leftVerdadeiro: 9,
      leftImpreciso: 0,
      leftFalso: 1,
      rightVerdadeiro: 10,
      rightImpreciso: 0,
      rightFalso: 0,
    );
    expect(notTie.left.erro, closeTo(0.1, 0.0001));
    expect(notTie.call, NeedleCall.leftErrsMore);
  });

  test('um único fato checável usa o singular na base', () {
    final reading = MentiromentroReading.compute(
      leftName: 'A',
      rightName: 'B',
      leftVerdadeiro: 1,
      leftImpreciso: 0,
      leftFalso: 0,
      rightVerdadeiro: 0,
      rightImpreciso: 0,
      rightFalso: 1,
    );
    expect(reading.basis, contains('1 fato checável de A'));
    expect(reading.basis, contains('1 de B'));
  });
}
