import '../domain/models.dart';
import '../domain/verdict.dart';

class ScoreboardParser {
  const ScoreboardParser._();

  static Scoreboard parse(Object? raw, {bool simulated = false}) {
    final json = _map(raw, 'placar');
    final candidatos = _candidatos(json['candidatos']);
    if (candidatos.isEmpty) {
      throw const FormatException('O placar não trouxe candidatos.');
    }
    return Scoreboard(
      atualizado: _int(json['atualizado']),
      video: _video(json['video']),
      candidatos: candidatos,
      declaracoes: _declaracoes(json['fatos']),
      propostas: _propostas(json['propostas']),
      ataques: _ataques(json['ataques']),
      linha: _linha(json['linha']),
      pausado: json['pausado'] == true,
      simulated: simulated,
      encerrado: _encerrado(json['encerrado']),
      revisao: _revisao(json['revisao']),
      aviso: _string(json['aviso']),
    );
  }

  static List<Candidate> _candidatos(Object? raw) {
    if (raw is! Map) return const [];
    final list = <Candidate>[];
    for (final entry in raw.entries) {
      final body = _map(entry.value, 'candidato');
      final tempo = _mapOrEmpty(body['tempo']);
      list.add(
        Candidate(
          id: entry.key.toString(),
          nome: _string(body['nome']) ?? 'Candidato',
          verdadeiro: _int(body['verdadeiro']),
          impreciso: _int(body['impreciso']),
          falso: _int(body['falso']),
          semDados: _int(body['sem_dados']),
          propostas: _int(body['propostas']),
          ataques: _int(body['ataques']),
          tempo: SpeakingTime(
            proposta: _double(tempo['proposta']),
            ataque: _double(tempo['ataque']),
            defesa: _double(tempo['defesa']),
            balanco: _double(tempo['balanco']),
            outro: _double(tempo['outro']),
          ),
        ),
      );
    }
    return list;
  }

  static VideoInfo? _video(Object? raw) {
    if (raw is! Map) return null;
    final body = _map(raw, 'video');
    return VideoInfo(
      id: _string(body['id']) ?? '',
      aoVivo: body['ao_vivo'] == true,
      inicio: _int(body['inicio']),
      t0: _int(body['t0']),
      comeco: body['comeco'] == null ? null : _int(body['comeco']),
      data: _string(body['data']),
    );
  }

  static EndedInfo? _encerrado(Object? raw) {
    if (raw is! Map) return null;
    final body = _map(raw, 'encerrado');
    final proximo = _string(body['proximo']);
    final texto = _string(body['texto']);
    if (proximo == null || texto == null) return null;
    return EndedInfo(proximo: proximo, texto: texto);
  }

  static List<FactClaim> _declaracoes(Object? raw) {
    if (raw is! List) return const [];
    final claims = <FactClaim>[];
    for (final group in raw) {
      if (group is! Map) continue;
      final body = _map(group, 'fato');
      final tema = _string(body['tema']) ?? '';
      final declaracoes = body['declaracoes'];
      if (declaracoes is! List) continue;
      for (final item in declaracoes) {
        if (item is! Map) continue;
        final decl = _map(item, 'declaracao');
        final afirmacao = _string(decl['afirmacao']) ?? '';
        final t = _int(decl['t']);
        final quem = _string(decl['quem']) ?? '';
        claims.add(
          FactClaim(
            t: t,
            quem: quem,
            tema: tema,
            afirmacao: afirmacao,
            veredito: Verdict.parse(decl['veredito']),
            contexto: _string(decl['contexto']),
            motivo: _string(decl['motivo']),
            fonte: _fonte(decl['fonte']),
            literal: _string(decl['literal']),
            corrigido: _corrigido(decl['corrigido']),
          ).identified(),
        );
      }
    }
    return claims;
  }

  static FactSource? _fonte(Object? raw) {
    if (raw is! Map) return null;
    final body = _map(raw, 'fonte');
    final titulo = _string(body['titulo']);
    final url = _string(body['url']);
    if (titulo == null || url == null) return null;
    return FactSource(titulo: titulo, url: url);
  }

  static Correction? _corrigido(Object? raw) {
    if (raw is! Map) return null;
    if (raw['antes'] == null) return null;
    return Correction(
      antes: Verdict.parse(raw['antes']),
      afirmacaoAntes: _string(raw['afirmacao_antes']),
    );
  }

  static List<Proposal> _propostas(Object? raw) {
    if (raw is! List) return const [];
    final list = <Proposal>[];
    for (final item in raw) {
      if (item is! Map) continue;
      final body = _map(item, 'proposta');
      final titulo = _string(body['titulo']);
      if (titulo == null) continue;
      list.add(
        Proposal(
          quem: _string(body['quem']) ?? '',
          titulo: titulo,
          explicacao: _string(body['explicacao']) ?? '',
          vezes: _int(body['vezes'], fallback: 1),
          t: _int(body['t']),
        ),
      );
    }
    return list;
  }

  static List<Attack> _ataques(Object? raw) {
    if (raw is! List) return const [];
    final list = <Attack>[];
    for (final item in raw) {
      if (item is! Map) continue;
      final body = _map(item, 'ataque');
      final resumo = _string(body['resumo']);
      if (resumo == null) continue;
      list.add(
        Attack(
          quem: _string(body['quem']) ?? '',
          resumo: resumo,
          t: body['t'] == null ? null : _int(body['t']),
        ),
      );
    }
    return list;
  }

  static Map<int, MinuteMark> _linha(Object? raw) {
    if (raw is! Map) return const {};
    final linha = <int, MinuteMark>{};
    for (final entry in raw.entries) {
      final minute = int.tryParse(entry.key.toString());
      if (minute == null || entry.value is! Map) continue;
      final body = _map(entry.value, 'minuto');
      final values = <String, int>{};
      for (final count in body.entries) {
        values[count.key] = _int(count.value);
      }
      linha[minute] = MinuteMark(values);
    }
    return linha;
  }

  static Revision? _revisao(Object? raw) {
    if (raw is! Map) return null;
    final body = _map(raw, 'revisao');
    final resumo = _string(body['resumo']);
    final por = _string(body['por']);
    if (resumo == null || por == null) return null;
    final mudancasRaw = body['mudancas'];
    final mudancas = <RevisionChange>[];
    if (mudancasRaw is List) {
      for (final item in mudancasRaw) {
        if (item is! Map) continue;
        final change = _map(item, 'mudanca');
        final afirmacao = _string(change['afirmacao']);
        if (afirmacao == null) continue;
        final depois = change['depois'];
        mudancas.add(
          RevisionChange(
            quem: _string(change['quem']) ?? '',
            afirmacao: afirmacao,
            antes: Verdict.parse(change['antes']),
            depois:
                depois == null || depois == '' ? null : Verdict.parse(depois),
            motivo: _string(change['motivo']) ?? '',
          ),
        );
      }
    }
    return Revision(
      por: por,
      data: _string(body['data']),
      resumo: resumo,
      antes: _snapshots(body['antes']),
      depois: _snapshots(body['depois']),
      mudancas: mudancas,
      aoVivo: _string(body['ao_vivo']),
    );
  }

  static Map<String, CountSnapshot> _snapshots(Object? raw) {
    if (raw is! Map) return const {};
    final map = <String, CountSnapshot>{};
    for (final entry in raw.entries) {
      if (entry.value is! Map) continue;
      final body = _map(entry.value, 'contagem');
      map[entry.key.toString()] = CountSnapshot(
        verdadeiro: _int(body['verdadeiro']),
        impreciso: _int(body['impreciso']),
        falso: _int(body['falso']),
        semDados: _int(body['sem_dados']),
      );
    }
    return map;
  }

  static Map<String, dynamic> _map(Object? raw, String label) {
    if (raw is Map<String, dynamic>) return raw;
    if (raw is Map) {
      return raw.map((key, value) => MapEntry(key.toString(), value));
    }
    throw FormatException('Esperava um objeto em $label.');
  }

  static Map<String, dynamic> _mapOrEmpty(Object? raw) {
    if (raw is Map<String, dynamic>) return raw;
    if (raw is Map) {
      return raw.map((key, value) => MapEntry(key.toString(), value));
    }
    return const {};
  }

  static int _int(Object? raw, {int fallback = 0}) {
    if (raw is int) return raw;
    if (raw is num) return raw.round();
    if (raw is String) return int.tryParse(raw) ?? fallback;
    return fallback;
  }

  static double _double(Object? raw) {
    if (raw is num) return raw.toDouble();
    if (raw is String) return double.tryParse(raw) ?? 0;
    return 0;
  }

  static String? _string(Object? raw) {
    if (raw is! String) return null;
    final trimmed = raw.trim();
    if (trimmed.isEmpty) return null;
    return raw;
  }
}
