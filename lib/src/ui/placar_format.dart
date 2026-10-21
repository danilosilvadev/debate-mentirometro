import '../domain/mentiromentro.dart';
import '../domain/models.dart';

/// Brasília não tem horário de verão desde 2019: UTC−3 o ano inteiro.
DateTime saoPaulo(int epochMs) {
  return DateTime.fromMillisecondsSinceEpoch(epochMs, isUtc: true)
      .subtract(const Duration(hours: 3));
}

String hhmm(int epochMs) {
  final time = saoPaulo(epochMs);
  final hour = time.hour.toString().padLeft(2, '0');
  final minute = time.minute.toString().padLeft(2, '0');
  return '$hour:$minute';
}

String dataCurta(int epochMs) {
  final time = saoPaulo(epochMs);
  return '${time.day}/${time.month}';
}

String formatPt(int value) {
  final negative = value < 0;
  final digits = value.abs().toString();
  final buffer = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buffer.write('.');
    buffer.write(digits[i]);
  }
  return negative ? '-$buffer' : buffer.toString();
}

String faltaPara(DateTime quando, DateTime agora) {
  var seconds = quando.difference(agora).inSeconds;
  if (seconds <= 0) return 'começando agora';
  final days = seconds ~/ 86400;
  seconds %= 86400;
  final hours = seconds ~/ 3600;
  seconds %= 3600;
  final minutes = seconds ~/ 60;
  final secs = seconds % 60;
  String dois(int n) => n.toString().padLeft(2, '0');
  final dias = days == 0 ? '' : '$days ${days == 1 ? 'dia ' : 'dias '}';
  return '$dias${dois(hours)}h ${dois(minutes)}min ${dois(secs)}s';
}

String rotuloDuracao(Duration elapsed) {
  final minutes = elapsed.inMinutes;
  if (minutes >= 60) {
    final hours = minutes ~/ 60;
    final rest = (minutes % 60).toString().padLeft(2, '0');
    return 'rolando há ${hours}h$rest';
  }
  return 'rolando há $minutes min';
}

Duration posicaoDoDebate(Scoreboard board, DateTime now) {
  final marked = board.posicaoDebate;
  if (marked != null) return marked;
  final video = board.video;
  if (video == null) return Duration.zero;
  if (video.aoVivo) {
    return Duration(milliseconds: now.millisecondsSinceEpoch - video.originMs);
  }
  return Duration(seconds: video.inicio) +
      now.difference(DateTime.fromMillisecondsSinceEpoch(video.t0));
}

class StatusCopy {
  const StatusCopy({required this.vivo, required this.texto});

  final bool vivo;
  final String texto;
}

StatusCopy statusCopy(Scoreboard board, DateTime now) {
  if (board.simulated) {
    if (board.encerrado != null) {
      return const StatusCopy(
          vivo: false, texto: 'Simulação encerrada · placar final');
    }
    final pausa = board.pausado ? ' · pausada' : '';
    return StatusCopy(
        vivo: true, texto: 'Simulação$pausa · fatos ilustrativos');
  }
  if (board.encerrado != null) {
    return const StatusCopy(
        vivo: false, texto: 'Debate encerrado · placar final');
  }
  final updated = DateTime.fromMillisecondsSinceEpoch(board.atualizado);
  final seconds = now.difference(updated).inSeconds;
  final vivo = seconds < 120;
  final video = board.video;
  var reprise = '';
  if (video != null && !video.aoVivo && video.data != null) {
    final parsed = DateTime.tryParse(video.data!);
    if (parsed != null) {
      reprise =
          ' · reprise do debate de ${dataCurta(parsed.millisecondsSinceEpoch)}';
    }
  }
  final pausa = board.pausado ? ' · checagem automática pausada' : '';
  if (vivo) {
    return StatusCopy(
      vivo: true,
      texto: 'Ao vivo · checagem ~30s atrás da TV$reprise$pausa',
    );
  }
  final minutes = (seconds / 60).round();
  return StatusCopy(
      vivo: false, texto: 'Última atualização há $minutes min$pausa');
}

String faixaTexto(StatusCopy status, Scoreboard board) {
  if (board.encerrado != null) return 'Debate encerrado';
  if (board.simulated) return 'Simulação';
  return status.vivo ? 'Ao vivo' : 'Debate encerrado ou pausado';
}

String erroVisivel(Candidate candidate) {
  final total = candidate.verdadeiro + candidate.impreciso + candidate.falso;
  if (total == 0) return '–';
  final erro = (candidate.falso + candidate.impreciso / 2) / total;
  return '${(erro * 100).round()}';
}

String placarShareText(Scoreboard board) {
  if (board.candidatos.length < 2) return 'Placar da Verdade';
  final left = board.candidatos[0];
  final right = board.candidatos[1];
  final estado = board.encerrado != null
      ? ' (placar final)'
      : board.simulated
          ? ' (simulação)'
          : ', ao vivo';
  String pct(Candidate candidate) {
    final value = erroVisivel(candidate);
    return value == '–' ? '–' : '$value%';
  }

  final resumo =
      '${left.nome} ${pct(left)} x ${right.nome} ${pct(right)} de erro';
  final tons =
      '${left.nome}: ${left.propostas} propostas x ${left.ataques} ataques. '
      '${right.nome}: ${right.propostas} propostas x ${right.ataques} ataques';
  final aviso = board.simulated
      ? '\nFatos fictícios, gerados para demonstrar o aplicativo.'
      : '';
  return 'Mentirômetro do debate$estado: $resumo\n$tons$aviso\nhttps://placar.zenithonacademy.com.br/';
}

String factShareText(Scoreboard board, FactClaim claim) {
  final nome = board.candidateById(claim.quem)?.nome ?? '';
  final motivo = claim.motivo == null ? '' : ' ${claim.motivo}';
  final link = board.simulated
      ? '\n\n(Simulação do aplicativo — fato fictício.)'
      : '\n\nVeja a fonte: https://placar.zenithonacademy.com.br/#fato-${claim.id}';
  return '$nome disse: "${claim.afirmacao}" → ${claim.veredito.label}.$motivo$link';
}

String hostOf(String url) {
  final uri = Uri.tryParse(url);
  if (uri == null || uri.host.isEmpty) return '';
  return uri.host.replaceFirst(RegExp(r'^www\.'), '');
}

/// Porcentagem de erro da revisão, ou nulo quando não há fato checável.
int? erroRevisao(CountSnapshot counts) {
  final total = counts.verdadeiro + counts.impreciso + counts.falso;
  if (total == 0) return null;
  return ((counts.falso + counts.impreciso / 2) / total * 100).round();
}

String erroRevisaoTexto(CountSnapshot? counts) {
  if (counts == null) return '–';
  final value = erroRevisao(counts);
  return value == null ? '–' : '$value%';
}

MentiromentroReading? leituraDe(Scoreboard board) {
  if (board.candidatos.length < 2) return null;
  final left = board.candidatos[0];
  final right = board.candidatos[1];
  return MentiromentroReading.compute(
    leftName: left.nome,
    rightName: right.nome,
    leftVerdadeiro: left.verdadeiro,
    leftImpreciso: left.impreciso,
    leftFalso: left.falso,
    rightVerdadeiro: right.verdadeiro,
    rightImpreciso: right.impreciso,
    rightFalso: right.falso,
  );
}
