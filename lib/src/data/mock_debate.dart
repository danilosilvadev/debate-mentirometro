import '../domain/mentiromentro.dart';
import '../domain/models.dart';
import '../domain/verdict.dart';

/// Roteiro fictício de um debate. Os números, as fontes e as frases são
/// ilustrativos — o app deixa isso explícito na interface.
///
/// O relógio do debate começa às 21:05 no horário de Brasília
/// (00:05 UTC de 20/10/2026).
final simulationOrigin = DateTime.utc(2026, 10, 20, 0, 5);

const simulationLiveTail = 4;

int get simulationInitialReveal => simulatedEvents.length - simulationLiveTail;

sealed class SimBeat {
  const SimBeat(this.at);
  final Duration at;
}

class ClaimBeat extends SimBeat {
  const ClaimBeat(
    super.at, {
    required this.quem,
    required this.tema,
    required this.afirmacao,
    required this.veredito,
    required this.motivo,
    this.contexto,
    this.literal,
    this.fonteTitulo,
    this.fonteUrl,
  });

  final String quem;
  final String tema;
  final String afirmacao;
  final Verdict veredito;
  final String motivo;
  final String? contexto;
  final String? literal;
  final String? fonteTitulo;
  final String? fonteUrl;
}

class ProposalBeat extends SimBeat {
  const ProposalBeat(
    super.at, {
    required this.quem,
    required this.titulo,
    required this.explicacao,
  });

  final String quem;
  final String titulo;
  final String explicacao;
}

class AttackBeat extends SimBeat {
  const AttackBeat(super.at, {required this.quem, required this.resumo});

  final String quem;
  final String resumo;
}

const _fonte = 'Série ilustrativa do placar';

const simulatedEvents = <SimBeat>[
  AttackBeat(
    Duration(minutes: 3, seconds: 10),
    quem: '2',
    resumo: 'Disse que o adversário não entrega resultado nenhum em segurança.',
  ),
  ClaimBeat(
    Duration(minutes: 4, seconds: 20),
    quem: '1',
    tema: 'Economia',
    afirmacao:
        'O salário mínimo teve aumento real acima da inflação nos últimos dois anos.',
    literal: 'o salário mínimo subiu acima da inflação nesses dois anos',
    contexto: 'Resposta sobre renda e custo de vida.',
    veredito: Verdict.verdadeiro,
    motivo:
        'Na série ilustrativa do placar, o piso foi reajustado acima do IPCA nos dois anos do roteiro.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/salario-minimo',
  ),
  ProposalBeat(
    Duration(minutes: 5, seconds: 5),
    quem: '1',
    titulo: 'Reajustar o salário mínimo pela inflação e pelo PIB',
    explicacao:
        'Propõe manter o reajuste pelo INPC mais o crescimento do PIB, para preservar ganho real do piso.',
  ),
  ClaimBeat(
    Duration(minutes: 6, seconds: 40),
    quem: '2',
    tema: 'Agro',
    afirmacao: 'O Brasil é o maior exportador mundial de soja.',
    literal: 'nós somos o maior exportador de soja do mundo',
    contexto: 'Bloco sobre comércio exterior.',
    veredito: Verdict.verdadeiro,
    motivo:
        'A série ilustrativa de exportação coloca o país na liderança mundial de soja.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/soja',
  ),
  AttackBeat(
    Duration(minutes: 7, seconds: 15),
    quem: '1',
    resumo:
        'Acusou o adversário de só prometer privatização e não apresentar números.',
  ),
  ProposalBeat(
    Duration(minutes: 8, seconds: 30),
    quem: '2',
    titulo: 'Classificar facções como organizações terroristas',
    explicacao:
        'Pretende enquadrar PCC, Comando Vermelho e milícias nessa categoria para endurecer pena e regime.',
  ),
  ClaimBeat(
    Duration(minutes: 9, seconds: 10),
    quem: '1',
    tema: 'Social',
    afirmacao: 'O Bolsa Família cobre mais de 20 milhões de famílias.',
    contexto: 'Defesa dos programas de transferência de renda.',
    veredito: Verdict.verdadeiro,
    motivo:
        'A base ilustrativa do placar traz mais de 20 milhões de famílias no programa.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/bolsa-familia',
  ),
  AttackBeat(
    Duration(minutes: 10, seconds: 5),
    quem: '2',
    resumo: 'Ironizou o adversário por ler estatística de gabinete.',
  ),
  AttackBeat(
    Duration(minutes: 11, seconds: 20),
    quem: '2',
    resumo: 'Chamou o programa social de máquina de comprar voto.',
  ),
  ClaimBeat(
    Duration(minutes: 12, seconds: 45),
    quem: '2',
    tema: 'Economia',
    afirmacao:
        'O governo gastou mais de R\$ 500 bilhões em medidas eleitorais.',
    literal: 'gastou mais de 500 bilhões para se reeleger',
    contexto: 'Ataque ao custo das medidas anunciadas no ano eleitoral.',
    veredito: Verdict.impreciso,
    motivo:
        'A soma ilustrativa fica na casa de R\$ 350 bilhões, não acima de R\$ 500 bilhões. Parte do que entrou na conta não é gasto direto.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/gasto-eleitoral',
  ),
  ProposalBeat(
    Duration(minutes: 13, seconds: 30),
    quem: '1',
    titulo: 'Expandir o Farmácia Popular',
    explicacao:
        'Quer incluir mais medicamentos de uso contínuo na lista gratuita do programa.',
  ),
  ClaimBeat(
    Duration(minutes: 14, seconds: 50),
    quem: '1',
    tema: 'Meio ambiente',
    afirmacao: 'O desmatamento na Amazônia caiu em relação ao ano passado.',
    contexto: 'Resposta sobre fiscalização ambiental.',
    veredito: Verdict.verdadeiro,
    motivo:
        'O recorte anual ilustrativo mostra queda na área derrubada em relação ao ano anterior.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/desmatamento',
  ),
  AttackBeat(
    Duration(minutes: 15, seconds: 40),
    quem: '1',
    resumo: 'Disse que o adversário nega dado de desmatamento quando convém.',
  ),
  ProposalBeat(
    Duration(minutes: 16, seconds: 15),
    quem: '2',
    titulo: 'Programa de emprego jovem no primeiro ano',
    explicacao:
        'Subsídio temporário para a primeira contratação formal de jovens de 18 a 24 anos.',
  ),
  ClaimBeat(
    Duration(minutes: 17, seconds: 25),
    quem: '2',
    tema: 'Economia',
    afirmacao: 'O desemprego hoje é o maior dos últimos vinte anos.',
    literal: 'o desemprego está o maior em vinte anos',
    contexto: 'Crítica à geração de vagas.',
    veredito: Verdict.falso,
    motivo:
        'A taxa ilustrativa está entre as menores da série de vinte anos, não a maior.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/desemprego',
  ),
  ClaimBeat(
    Duration(minutes: 18, seconds: 35),
    quem: '1',
    tema: 'Economia',
    afirmacao: 'O saldo de empregos formais neste ano já passou de 1 milhão.',
    contexto: 'Resposta direta sobre a taxa de desemprego.',
    veredito: Verdict.verdadeiro,
    motivo: 'O saldo ilustrativo de vagas formais no ano passa de 1 milhão.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/empregos',
  ),
  AttackBeat(
    Duration(minutes: 19, seconds: 10),
    quem: '1',
    resumo: 'Disse que o adversário promete o que já está em lei.',
  ),
  AttackBeat(
    Duration(minutes: 20, seconds: 20),
    quem: '2',
    resumo: 'Acusou o governo de maquiar o desemprego com trabalho informal.',
  ),
  ProposalBeat(
    Duration(minutes: 21, seconds: 5),
    quem: '1',
    titulo: 'Desmatamento ilegal zero até o fim do mandato',
    explicacao:
        'Compromisso de zerar o desmatamento ilegal na Amazônia até o último ano de governo, com fiscalização e cadastro ambiental.',
  ),
  ClaimBeat(
    Duration(minutes: 22, seconds: 40),
    quem: '2',
    tema: 'Educação',
    afirmacao: 'O Brasil é o último do mundo em matemática no PISA.',
    literal: 'somos o último do mundo em matemática',
    contexto: 'Bloco de educação básica.',
    veredito: Verdict.falso,
    motivo:
        'No recorte ilustrativo, o país fica na parte de baixo do ranking, mas não é o último do mundo.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/pisa',
  ),
  AttackBeat(
    Duration(minutes: 23, seconds: 15),
    quem: '1',
    resumo: 'Acusou o adversário de copiar plano de governo antigo.',
  ),
  ProposalBeat(
    Duration(minutes: 24, seconds: 30),
    quem: '2',
    titulo: 'Reduzir impostos sobre combustíveis',
    explicacao:
        'Corte de tributos federais na gasolina e no diesel para baixar o preço na bomba.',
  ),
  ClaimBeat(
    Duration(minutes: 25, seconds: 45),
    quem: '1',
    tema: 'Energia',
    afirmacao: 'A conta de luz caiu pela metade para a tarifa social.',
    contexto: 'Defesa da política tarifária.',
    veredito: Verdict.impreciso,
    motivo:
        'A tarifa social ilustrativa caiu, mas cerca de 30%, não pela metade.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/tarifa-social',
  ),
  AttackBeat(
    Duration(minutes: 26, seconds: 20),
    quem: '1',
    resumo:
        'Disse que o adversário usa o preço da gasolina como slogan, sem plano.',
  ),
  AttackBeat(
    Duration(minutes: 27, seconds: 5),
    quem: '2',
    resumo: 'Acusou o adversário de usar o microfone para comício.',
  ),
  ClaimBeat(
    Duration(minutes: 28, seconds: 30),
    quem: '2',
    tema: 'Energia',
    afirmacao: 'A gasolina passou de R\$ 8 em todas as capitais.',
    literal: 'a gasolina está mais de 8 reais em toda capital',
    contexto: 'Ataque ao custo dos combustíveis.',
    veredito: Verdict.falso,
    motivo:
        'A média ilustrativa das capitais está abaixo de R\$ 8. Nenhuma capital do roteiro está toda acima desse valor.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/gasolina',
  ),
  ProposalBeat(
    Duration(minutes: 29, seconds: 40),
    quem: '2',
    titulo: 'Privatizar estatais do setor elétrico',
    explicacao:
        'Venda de empresas públicas de energia, com o recurso usado para abater dívida.',
  ),
  ClaimBeat(
    Duration(minutes: 30, seconds: 15),
    quem: '1',
    tema: 'Economia',
    afirmacao: 'A inflação de alimentos está negativa no acumulado do ano.',
    contexto: 'Resposta sobre o custo da cesta básica.',
    veredito: Verdict.falso,
    motivo:
        'O índice ilustrativo de alimentos no ano segue positivo, não negativo.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/alimentos',
  ),
  AttackBeat(
    Duration(minutes: 32, seconds: 10),
    quem: '2',
    resumo: 'Repetiu que o adversário quebrou o país e não admite erro.',
  ),
  ProposalBeat(
    Duration(minutes: 33, seconds: 20),
    quem: '1',
    titulo: 'Tarifa social de energia para famílias de baixa renda',
    explicacao:
        'Famílias de baixa renda pagariam uma faixa menor na conta de luz, com a diferença rateada na tarifa.',
  ),
  ClaimBeat(
    Duration(minutes: 34, seconds: 25),
    quem: '2',
    tema: 'Segurança',
    afirmacao: 'O número de homicídios caiu pela metade no último ano.',
    contexto: 'Balanço de segurança pública.',
    veredito: Verdict.impreciso,
    motivo:
        'Houve queda ilustrativa de homicídios, mas perto de 10%, não pela metade.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/homicidios',
  ),
  AttackBeat(
    Duration(minutes: 35, seconds: 30),
    quem: '1',
    resumo: 'Disse que o adversário não distingue dado de slogan.',
  ),
  ClaimBeat(
    Duration(minutes: 36, seconds: 15),
    quem: '1',
    tema: 'Saúde',
    afirmacao: 'Vamos zerar a fila de cirurgias eletivas em doze meses.',
    contexto: 'Proposta de campanha, ainda sem execução.',
    veredito: Verdict.semDados,
    motivo:
        'Meta futura. Não há série ilustrativa para confirmar se a fila zera em doze meses.',
  ),
  ProposalBeat(
    Duration(minutes: 37, seconds: 40),
    quem: '2',
    titulo: 'Escola cívico-militar em cada capital',
    explicacao:
        'Pelo menos uma escola com gestão compartilhada com as forças de segurança em cada capital.',
  ),
  AttackBeat(
    Duration(minutes: 38, seconds: 20),
    quem: '1',
    resumo: 'Acusou o adversário de querer transformar escola em quartel.',
  ),
  AttackBeat(
    Duration(minutes: 39, seconds: 10),
    quem: '2',
    resumo: 'Repetiu que tudo isso é culpa de quem está sentado do outro lado.',
  ),
  ClaimBeat(
    Duration(minutes: 40, seconds: 35),
    quem: '2',
    tema: 'Economia',
    afirmacao: 'A inflação deste mês passou de 20%.',
    literal: 'a inflação do mês já passou de vinte por cento',
    contexto: 'Consideração sobre o custo de vida.',
    veredito: Verdict.falso,
    motivo: 'O índice ilustrativo do mês está na casa de 0,5%, não 20%.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/inflacao-mes',
  ),
  ProposalBeat(
    Duration(minutes: 41, seconds: 15),
    quem: '1',
    titulo: 'Tarifa social de energia para famílias de baixa renda',
    explicacao:
        'Famílias de baixa renda pagariam uma faixa menor na conta de luz, com a diferença rateada na tarifa.',
  ),
  ClaimBeat(
    Duration(minutes: 42, seconds: 20),
    quem: '2',
    tema: 'Segurança',
    afirmacao:
        'No primeiro mês, vou classificar as principais facções como terroristas.',
    contexto: 'Promessa de início de governo.',
    veredito: Verdict.semDados,
    motivo:
        'Promessa de governo. Não dá para checar um ato que ainda não aconteceu.',
  ),
  AttackBeat(
    Duration(minutes: 43, seconds: 5),
    quem: '2',
    resumo: 'Disse que o adversário tem medo de enfrentar facção.',
  ),
  ClaimBeat(
    Duration(minutes: 44, seconds: 30),
    quem: '1',
    tema: 'Economia',
    afirmacao: 'A taxa básica de juros já está abaixo de 8%.',
    literal: null,
    contexto: 'Trecho em que a transcrição automática hesitou no número.',
    veredito: Verdict.emRevisao,
    motivo:
        'O áudio automático não confirmou o número. A frase fica de fora do placar até a conferência.',
  ),
  ClaimBeat(
    Duration(minutes: 46, seconds: 10),
    quem: '2',
    tema: 'Saúde',
    afirmacao: 'Fechamos 5 mil leitos de UTI neste ano.',
    contexto: 'A transcrição não bateu com o que se ouve no trecho.',
    veredito: Verdict.emRevisao,
    motivo:
        'O áudio não confirmou “5 mil leitos”. Fora do placar até a conferência.',
  ),
  AttackBeat(
    Duration(minutes: 47, seconds: 25),
    quem: '1',
    resumo: 'Disse que o adversário inventa número de leito para assustar.',
  ),
  // Entram ao vivo, um a um, depois que o app abre.
  ClaimBeat(
    Duration(minutes: 49, seconds: 15),
    quem: '1',
    tema: 'Energia',
    afirmacao: 'A matriz elétrica brasileira é majoritariamente renovável.',
    contexto: 'Resposta sobre a conta de luz e a origem da energia.',
    veredito: Verdict.verdadeiro,
    motivo:
        'A matriz ilustrativa tem mais da metade da geração em fonte renovável.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/matriz-eletrica',
  ),
  ClaimBeat(
    Duration(minutes: 50, seconds: 40),
    quem: '2',
    tema: 'Economia',
    afirmacao: 'O salário mínimo perdeu para a inflação nos últimos 12 meses.',
    contexto: 'Tréplica sobre o piso nacional.',
    veredito: Verdict.impreciso,
    motivo:
        'No roteiro, o piso teve ganho real. Dizer que perdeu para a inflação em doze meses exagera o dado ilustrativo.',
    fonteTitulo: _fonte,
    fonteUrl: 'https://exemplo.com/simulacao/salario-12-meses',
  ),
  AttackBeat(
    Duration(minutes: 51, seconds: 20),
    quem: '2',
    resumo: 'Nas considerações finais, chamou o adversário de mentiroso.',
  ),
  ProposalBeat(
    Duration(minutes: 52, seconds: 10),
    quem: '1',
    titulo: 'Ampliar vagas em creche',
    explicacao:
        'Meta de abrir novas vagas em creche pública nas capitais, em tempo integral.',
  ),
];

const _lulaTime = SpeakingTime(
  proposta: 330,
  ataque: 870,
  defesa: 140,
  balanco: 530,
);

const _flavioTime = SpeakingTime(
  proposta: 890,
  ataque: 970,
  defesa: 80,
  balanco: 100,
);

Scoreboard buildSimulatedBoard({
  required int revealed,
  required DateTime now,
  DateTime? finishedAt,
}) {
  final count = revealed.clamp(0, simulatedEvents.length);
  final events = simulatedEvents.take(count).toList();
  final origin = simulationOrigin.millisecondsSinceEpoch;

  final claims = <FactClaim>[];
  final proposals = <Proposal>[];
  final attacks = <Attack>[];
  final linha = <int, Map<String, int>>{};

  void bump(Duration at, String key) {
    final minute = at.inMilliseconds ~/ 60000;
    final bucket = linha.putIfAbsent(minute, () => <String, int>{});
    bucket[key] = (bucket[key] ?? 0) + 1;
  }

  for (final beat in events) {
    final t = origin + beat.at.inMilliseconds;
    switch (beat) {
      case ClaimBeat():
        final fonte = beat.fonteTitulo != null && beat.fonteUrl != null
            ? FactSource(titulo: beat.fonteTitulo!, url: beat.fonteUrl!)
            : null;
        claims.add(
          FactClaim(
            t: t,
            quem: beat.quem,
            tema: beat.tema,
            afirmacao: beat.afirmacao,
            veredito: beat.veredito,
            contexto: beat.contexto,
            motivo: beat.motivo,
            literal: beat.literal,
            fonte: fonte,
          ).identified(),
        );
      case ProposalBeat():
        final existing = proposals.indexWhere(
          (proposal) =>
              proposal.quem == beat.quem && proposal.titulo == beat.titulo,
        );
        if (existing >= 0) {
          final previous = proposals[existing];
          proposals[existing] = Proposal(
            quem: previous.quem,
            titulo: previous.titulo,
            explicacao: previous.explicacao,
            vezes: previous.vezes + 1,
            t: t,
          );
        } else {
          proposals.add(
            Proposal(
              quem: beat.quem,
              titulo: beat.titulo,
              explicacao: beat.explicacao,
              vezes: 1,
              t: t,
            ),
          );
        }
        bump(beat.at, 'p${beat.quem}');
      case AttackBeat():
        attacks.add(Attack(quem: beat.quem, resumo: beat.resumo, t: t));
        bump(beat.at, 'a${beat.quem}');
    }
  }

  Candidate candidate(String id, String nome, SpeakingTime tempo) {
    final tally = VerdictTally.from(
      claims.where((claim) => claim.quem == id).map((claim) => claim.veredito),
    );
    final proposalCount = proposals
        .where((proposal) => proposal.quem == id)
        .fold<int>(0, (sum, proposal) => sum + proposal.vezes);
    final attackCount = attacks.where((attack) => attack.quem == id).length;
    return Candidate(
      id: id,
      nome: nome,
      verdadeiro: tally.verdadeiro,
      impreciso: tally.impreciso,
      falso: tally.falso,
      semDados: tally.semDados,
      propostas: proposalCount,
      ataques: attackCount,
      tempo: tempo,
    );
  }

  attacks.sort((a, b) => (b.t ?? 0).compareTo(a.t ?? 0));

  final position = events.isEmpty
      ? Duration.zero
      : events.last.at +
          (finishedAt == null ? Duration.zero : now.difference(finishedAt));

  return Scoreboard(
    atualizado: now.millisecondsSinceEpoch,
    video: VideoInfo(
      id: '',
      aoVivo: true,
      inicio: 0,
      t0: now.millisecondsSinceEpoch,
      comeco: origin,
      data: '2026-10-19T21:05:00-03:00',
    ),
    candidatos: [
      candidate('1', 'Lula', _lulaTime),
      candidate('2', 'Flávio Bolsonaro', _flavioTime),
    ],
    declaracoes: claims,
    propostas: proposals,
    ataques: attacks,
    linha: {
      for (final entry in linha.entries) entry.key: MinuteMark(entry.value),
    },
    pausado: false,
    simulated: true,
    posicaoDebate: position.isNegative ? Duration.zero : position,
    audienciaAgora: 1284 + count * 7,
    visitas: 18440 + count * 3,
  );
}
