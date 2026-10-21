import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:placar_da_verdade/src/data/mock_debate.dart';
import 'package:placar_da_verdade/src/data/remote_scoreboard_repository.dart';
import 'package:placar_da_verdade/src/data/scoreboard_parser.dart';
import 'package:placar_da_verdade/src/domain/fact_id.dart';
import 'package:placar_da_verdade/src/domain/fact_query.dart';
import 'package:placar_da_verdade/src/domain/mentiromentro.dart';
import 'package:placar_da_verdade/src/domain/models.dart';
import 'package:placar_da_verdade/src/domain/timeline.dart';
import 'package:placar_da_verdade/src/domain/verdict.dart';
import 'package:placar_da_verdade/src/ui/placar_format.dart';

void main() {
  test('o id do fato bate com o placar web', () {
    const afirmacao =
        'O governo Lula gastou mais de 350 bilhões de reais para tentar se reeleger.';
    expect(
      factId(t: 1792372110099, quem: '2', afirmacao: afirmacao),
      'mvek2rdf21jtzd4e',
    );
  });

  test('o parser lê o JSON público, inclusive revisão e tempo fracionário', () {
    final board = ScoreboardParser.parse(jsonDecode(_fixture));
    expect(board.candidatos.map((c) => c.nome), ['Lula', 'Flávio Bolsonaro']);
    expect(board.candidatos[1].tempo.ataque, 970.3);
    expect(board.declaracoes.single.veredito, Verdict.impreciso);
    expect(board.declaracoes.single.id, 'mvek2rdf21jtzd4e');
    expect(board.declaracoes.single.corrigido?.antes, Verdict.verdadeiro);
    expect(board.linha[5]!['p2'], 1);
    expect(board.encerrado?.texto, contains('TV Globo'));
    expect(board.revisao?.mudancas.single.depois, Verdict.impreciso);
    expect(board.revisao?.aoVivo, '2026-10-18-ao-vivo');
    expect(board.propostas.single.vezes, 2);
    expect(board.simulated, isFalse);
  });

  test('o repositório remoto pede placar.json com cache-buster', () async {
    final client = _FakeClient(_fixture);
    final repo = RemoteScoreboardRepository(
      client: client,
      autostart: false,
      clock: () => DateTime.utc(2026, 10, 21, 12),
    );
    final board = await repo.fetch();
    expect(board.candidatos.first.nome, 'Lula');
    expect(client.lastUri?.path, endsWith('/placar.json'));
    expect(client.lastUri?.queryParameters['t'], isNotEmpty);
    repo.dispose();
  });

  test('a simulação inicial pende para quem tem mais falso e impreciso', () {
    final board = buildSimulatedBoard(
      revealed: simulationInitialReveal,
      now: DateTime.utc(2026, 10, 21, 23),
    );
    expect(board.simulated, isTrue);
    expect(board.candidatos.map((c) => c.nome), ['Lula', 'Flávio Bolsonaro']);
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
    expect(reading.ready, isTrue);
    expect(reading.call, NeedleCall.rightErrsMore);
    expect(reading.angleDegrees, greaterThan(20));
    expect(
      board.declaracoes.where((c) => c.veredito == Verdict.emRevisao),
      isNotEmpty,
    );
    expect(
      board.declaracoes.where((c) => c.veredito == Verdict.semDados),
      isNotEmpty,
    );
  });

  test('colunas de 5 minutos somam ataques e propostas na mesma escala', () {
    final timeline = DebateTimeline.build(
      linha: {
        0: const MinuteMark({'a1': 1, 'p2': 1}),
        4: const MinuteMark({'a1': 2, 'p1': 1, 'a2': 1}),
        5: const MinuteMark({'p1': 3}),
      },
      candidates: const [
        Candidate(
          id: '1',
          nome: 'Lula',
          verdadeiro: 0,
          impreciso: 0,
          falso: 0,
          semDados: 0,
          propostas: 0,
          ataques: 0,
        ),
        Candidate(
          id: '2',
          nome: 'Flávio Bolsonaro',
          verdadeiro: 0,
          impreciso: 0,
          falso: 0,
          semDados: 0,
          propostas: 0,
          ataques: 0,
        ),
      ],
      originMs: 1000000,
    );
    expect(timeline.rows.first.columns, hasLength(2));
    expect(timeline.rows.first.columns[0].attacks, 3);
    expect(timeline.rows.first.columns[0].proposals, 1);
    expect(timeline.rows.first.columns[1].proposals, 3);
    expect(timeline.rows.first.columns[0].startMs, 1000000);
    expect(timeline.rows.first.columns[1].startMs, 1300000);
    expect(timeline.rows[1].columns[0].attacks, 1);
    expect(timeline.rows[1].columns[0].proposals, 1);
    expect(timeline.maxStack, greaterThan(1));
  });

  test('filtros de fato respeitam candidato, veredito, janela e corrigidos',
      () {
    final items = [
      _claim(t: 0, quem: '1', verdict: Verdict.falso),
      _claim(t: 10, quem: '2', verdict: Verdict.verdadeiro, corrected: true),
      _claim(t: 20, quem: '2', verdict: Verdict.impreciso),
    ];
    final byPerson = FactQuery.apply(
      items,
      const FactFilter(quem: '2', verdict: Verdict.falso),
      ignore: 'quem',
    );
    expect(byPerson, hasLength(1));

    final window = FactQuery.apply(
      items,
      const FactFilter(windowStartMs: 10, windowEndMs: 20),
    );
    expect(window.single.t, 10);

    final corrected = FactQuery.sorted(
      FactQuery.apply(items, const FactFilter(onlyCorrected: true)),
      FactOrder.recentes,
    );
    expect(corrected.single.t, 10);

    final recent = FactQuery.sorted(items, FactOrder.recentes);
    expect(recent.first.t, 20);
    expect(FactQuery.highlights(items).first.veredito, Verdict.impreciso);
  });

  test('relógio e números em pt-BR', () {
    expect(formatPt(1284), '1.284');
    expect(formatPt(18440), '18.440');
    expect(hhmm(simulationOrigin.millisecondsSinceEpoch), '21:05');
    final quando = DateTime.utc(2026, 10, 23, 12);
    final agora = DateTime.utc(2026, 10, 21, 9, 30, 15);
    expect(faltaPara(quando, agora), '2 dias 02h 29min 45s');
    expect(faltaPara(agora, quando), 'começando agora');

    final shares = speakingShares(
      const SpeakingTime(proposta: 330, ataque: 870, defesa: 140, balanco: 530),
    );
    expect(shares.map((share) => share.percent), [18, 47, 7, 28]);
  });
}

FactClaim _claim({
  required int t,
  required String quem,
  required Verdict verdict,
  bool corrected = false,
}) {
  return FactClaim(
    t: t,
    quem: quem,
    tema: 'Economia',
    afirmacao: 'Afirmação $t',
    veredito: verdict,
    corrigido: corrected ? const Correction(antes: Verdict.verdadeiro) : null,
    id: 'id-$t',
  );
}

class _FakeClient implements ScoreboardClient {
  _FakeClient(this.body);
  final String body;
  Uri? lastUri;

  @override
  Future<String> get(Uri uri) async {
    lastUri = uri;
    return body;
  }
}

const _fixture = '''
{
  "atualizado": 1792445992096,
  "video": {"id": "abc", "ao_vivo": false, "inicio": 0, "t0": 1, "comeco": 2, "data": "2026-10-19T00:54:04.805Z"},
  "candidatos": {
    "1": {"nome": "Lula", "verdadeiro": 1, "impreciso": 0, "falso": 0, "sem_dados": 1, "propostas": 1, "ataques": 1, "tempo": {"proposta": 10, "ataque": 20.5, "defesa": 0, "balanco": 0, "outro": 3}},
    "2": {"nome": "Flávio Bolsonaro", "verdadeiro": 0, "impreciso": 1, "falso": 0, "sem_dados": 0, "propostas": 2, "ataques": 1, "tempo": {"proposta": 1, "ataque": 970.3, "defesa": 0, "balanco": 0}}
  },
  "fatos": [
    {"tema": "Economia", "declaracoes": [
      {
        "t": 1792372110099,
        "quem": "2",
        "afirmacao": "O governo Lula gastou mais de 350 bilhões de reais para tentar se reeleger.",
        "contexto": "Resposta.",
        "veredito": "impreciso",
        "motivo": "A conta ilustrativa mistura crédito e gasto.",
        "fonte": {"titulo": "Série", "url": "https://exemplo.com/x"},
        "literal": "gastou mais de 350 bilhões",
        "corrigido": {"antes": "verdadeiro"}
      }
    ]}
  ],
  "propostas": [
    {"quem": "2", "titulo": "Classificar facções", "explicacao": "Endurecer o enquadramento.", "vezes": 2, "t": 10}
  ],
  "ataques": [
    {"quem": "2", "resumo": "Chamou o adversário de mentiroso.", "t": 11}
  ],
  "linha": {"5": {"a1": 0, "a2": 0, "p1": 0, "p2": 1}},
  "pausado": false,
  "encerrado": {"proximo": "2026-10-23T21:20:00-03:00", "texto": "Sexta, 23 de outubro, às 21h20, na TV Globo"},
  "revisao": {
    "por": "revisão de exemplo",
    "data": "2026-10-19",
    "resumo": "A transcrição ao vivo errou um número.",
    "antes": {"1": {"verdadeiro": 1, "impreciso": 0, "falso": 0, "sem_dados": 0}, "2": {"verdadeiro": 1, "impreciso": 0, "falso": 0, "sem_dados": 0}},
    "depois": {"1": {"verdadeiro": 1, "impreciso": 0, "falso": 0, "sem_dados": 1}, "2": {"verdadeiro": 0, "impreciso": 1, "falso": 0, "sem_dados": 0}},
    "mudancas": [
      {"quem": "Flávio Bolsonaro", "afirmacao": "Gastou mais de 350 bilhões.", "antes": "verdadeiro", "depois": "impreciso", "motivo": "A conta mistura crédito e gasto."}
    ],
    "ao_vivo": "2026-10-18-ao-vivo"
  }
}
''';
