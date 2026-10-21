import 'fact_id.dart';
import 'verdict.dart';

/// Tempo de fala classificado, em segundos.
///
/// A barra do placar usa proposta, ataque, defesa e balanço.
/// [outro] vem no JSON e não entra na barra.
class SpeakingTime {
  const SpeakingTime({
    this.proposta = 0,
    this.ataque = 0,
    this.defesa = 0,
    this.balanco = 0,
    this.outro = 0,
  });

  final double proposta;
  final double ataque;
  final double defesa;
  final double balanco;
  final double outro;

  static const zero = SpeakingTime();
}

class SpeakingShare {
  const SpeakingShare({
    required this.key,
    required this.label,
    required this.seconds,
    required this.percent,
  });

  final String key;
  final String label;
  final double seconds;
  final int percent;
}

/// As quatro fatias da barra, na ordem e com os rótulos do site.
List<SpeakingShare> speakingShares(SpeakingTime time) {
  const parts = <(String, String, double Function(SpeakingTime))>[
    ('proposta', 'propondo', _proposta),
    ('ataque', 'atacando', _ataque),
    ('defesa', 'se defendendo', _defesa),
    ('balanco', 'falando do passado', _balanco),
  ];
  final seconds = parts.map((part) => part.$3(time)).toList();
  final sum = seconds.fold<double>(0, (total, value) => total + value);
  final denom = sum == 0 ? 1.0 : sum;
  return [
    for (var i = 0; i < parts.length; i++)
      SpeakingShare(
        key: parts[i].$1,
        label: parts[i].$2,
        seconds: seconds[i],
        percent: (seconds[i] / denom * 100).round(),
      ),
  ];
}

double _proposta(SpeakingTime time) => time.proposta;
double _ataque(SpeakingTime time) => time.ataque;
double _defesa(SpeakingTime time) => time.defesa;
double _balanco(SpeakingTime time) => time.balanco;

class Candidate {
  const Candidate({
    required this.id,
    required this.nome,
    required this.verdadeiro,
    required this.impreciso,
    required this.falso,
    required this.semDados,
    required this.propostas,
    required this.ataques,
    this.tempo = SpeakingTime.zero,
  });

  final String id;
  final String nome;
  final int verdadeiro;
  final int impreciso;
  final int falso;
  final int semDados;
  final int propostas;
  final int ataques;
  final SpeakingTime tempo;
}

class FactSource {
  const FactSource({required this.titulo, required this.url});

  final String titulo;
  final String url;
}

class Correction {
  const Correction({required this.antes, this.afirmacaoAntes});

  final Verdict antes;
  final String? afirmacaoAntes;
}

class FactClaim {
  const FactClaim({
    required this.t,
    required this.quem,
    required this.tema,
    required this.afirmacao,
    required this.veredito,
    this.contexto,
    this.motivo,
    this.fonte,
    this.literal,
    this.corrigido,
    String? id,
  }) : id = id ?? '';

  final int t;
  final String quem;
  final String tema;
  final String afirmacao;
  final Verdict veredito;
  final String? contexto;
  final String? motivo;
  final FactSource? fonte;
  final String? literal;
  final Correction? corrigido;

  /// Preenchido pelo parser e pela simulação. Vazio só em testes avulsos.
  final String id;

  FactClaim identified() {
    return FactClaim(
      t: t,
      quem: quem,
      tema: tema,
      afirmacao: afirmacao,
      veredito: veredito,
      contexto: contexto,
      motivo: motivo,
      fonte: fonte,
      literal: literal,
      corrigido: corrigido,
      id: factId(t: t, quem: quem, afirmacao: afirmacao),
    );
  }
}

class Proposal {
  const Proposal({
    required this.quem,
    required this.titulo,
    required this.explicacao,
    required this.vezes,
    required this.t,
  });

  final String quem;
  final String titulo;
  final String explicacao;
  final int vezes;
  final int t;
}

class Attack {
  const Attack({required this.quem, required this.resumo, this.t});

  final String quem;
  final String resumo;
  final int? t;
}

/// Contagem de um minuto da linha do tempo. Chaves `a1`, `p1`, `a2`, `p2`.
class MinuteMark {
  const MinuteMark(this.values);

  final Map<String, int> values;

  int operator [](String key) => values[key] ?? 0;
}

class VideoInfo {
  const VideoInfo({
    required this.id,
    required this.aoVivo,
    required this.inicio,
    required this.t0,
    this.comeco,
    this.data,
  });

  final String id;
  final bool aoVivo;
  final int inicio;
  final int t0;
  final int? comeco;
  final String? data;

  int get originMs => comeco ?? t0;

  bool get hasStream => id.isNotEmpty;
}

class EndedInfo {
  const EndedInfo({required this.proximo, required this.texto});

  /// ISO-8601 com fuso, como no JSON (`2026-10-23T21:20:00-03:00`).
  final String proximo;
  final String texto;
}

class CountSnapshot {
  const CountSnapshot({
    required this.verdadeiro,
    required this.impreciso,
    required this.falso,
    required this.semDados,
  });

  final int verdadeiro;
  final int impreciso;
  final int falso;
  final int semDados;
}

class RevisionChange {
  const RevisionChange({
    required this.quem,
    required this.afirmacao,
    required this.antes,
    required this.depois,
    required this.motivo,
  });

  /// Nome do candidato, como vem no JSON da revisão (não o id).
  final String quem;
  final String afirmacao;
  final Verdict antes;

  /// Nulo quando a checagem foi removida na revisão.
  final Verdict? depois;
  final String motivo;
}

class Revision {
  const Revision({
    required this.por,
    required this.resumo,
    required this.antes,
    required this.depois,
    required this.mudancas,
    this.data,
    this.aoVivo,
  });

  final String por;
  final String? data;
  final String resumo;
  final Map<String, CountSnapshot> antes;
  final Map<String, CountSnapshot> depois;
  final List<RevisionChange> mudancas;

  /// Arquivo `placar-<aoVivo>.json` com o placar sem a revisão.
  final String? aoVivo;
}

class Scoreboard {
  const Scoreboard({
    required this.atualizado,
    required this.candidatos,
    required this.declaracoes,
    required this.propostas,
    required this.ataques,
    required this.linha,
    required this.pausado,
    required this.simulated,
    this.video,
    this.encerrado,
    this.revisao,
    this.aviso,
    this.posicaoDebate,
    this.audienciaAgora,
    this.visitas,
  });

  final int atualizado;
  final List<Candidate> candidatos;
  final List<FactClaim> declaracoes;
  final List<Proposal> propostas;
  final List<Attack> ataques;
  final Map<int, MinuteMark> linha;
  final bool pausado;
  final bool simulated;
  final VideoInfo? video;
  final EndedInfo? encerrado;
  final Revision? revisao;
  final String? aviso;

  /// Quando preenchido, o relógio de debate usa esta posição em vez do
  /// relógio de parede. A simulação acelerada depende disso.
  final Duration? posicaoDebate;
  final int? audienciaAgora;
  final int? visitas;

  int get timelineOriginMs => video?.originMs ?? atualizado;

  Candidate? candidateById(String id) {
    for (final candidate in candidatos) {
      if (candidate.id == id) return candidate;
    }
    return null;
  }
}

enum DataOrigin { simulation, remote }

class ScoreboardSnapshot {
  const ScoreboardSnapshot({
    required this.origin,
    this.board,
    this.error,
    this.loading = false,
  });

  final DataOrigin origin;
  final Scoreboard? board;
  final String? error;
  final bool loading;

  bool get hasBoard => board != null;
}
