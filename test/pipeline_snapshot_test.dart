import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:placar_da_verdade/src/data/scoreboard_parser.dart';
import 'package:placar_da_verdade/src/domain/mentiromentro.dart';

void main() {
  test('o placar.json do pipeline abre no mesmo parser do app', () {
    final raw = jsonDecode(
      File('pipeline/fixtures/sample_placar.json').readAsStringSync(),
    );
    final board = ScoreboardParser.parse(raw);
    expect(board.candidatos.map((item) => item.nome), ['Lula', 'Flávio Bolsonaro']);
    expect(board.declaracoes.map((item) => item.veredito.wire),
        containsAll(['falso', 'em_revisao']));
    expect(board.propostas.single.titulo, 'Ampliar vagas em creche');
    expect(board.ataques.single.resumo, contains('mentir'));
    expect(board.linha[0]!['p1'], 1);
    expect(board.linha[0]!['a2'], 1);

    final reading = MentiromentroReading.compute(
      leftName: board.candidatos[0].nome,
      rightName: board.candidatos[1].nome,
      leftVerdadeiro: board.candidatos[0].verdadeiro,
      leftImpreciso: board.candidatos[0].impreciso,
      leftFalso: board.candidatos[0].falso,
      rightVerdadeiro: board.candidatos[1].verdadeiro,
      rightImpreciso: board.candidatos[1].impreciso,
      rightFalso: board.candidatos[1].falso,
    );
    expect(reading.ready, isFalse);
    expect(reading.angleDegrees, 0);
  });
}
