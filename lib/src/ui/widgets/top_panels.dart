import 'package:flutter/material.dart';

import '../../domain/mentiromentro.dart';
import '../../domain/models.dart';
import '../../theme/placar_theme.dart';
import '../open_link.dart';
import '../placar_format.dart';
import 'chrome.dart';
import 'gauge.dart';

class TopPanels extends StatelessWidget {
  const TopPanels({required this.board, required this.reading, super.key});

  final Scoreboard board;
  final MentiromentroReading? reading;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 820;
        final visor = Visor(board: board, reading: reading);
        final live =
            wide ? DarkLivePanel(board: board) : LightLiveStrip(board: board);
        if (!wide) {
          return Column(
            children: [
              live,
              const SizedBox(height: 16),
              visor,
            ],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 3, child: live),
            const SizedBox(width: 16),
            Expanded(flex: 2, child: visor),
          ],
        );
      },
    );
  }
}

class Visor extends StatelessWidget {
  const Visor({required this.board, required this.reading, super.key});

  final Scoreboard board;
  final MentiromentroReading? reading;

  @override
  Widget build(BuildContext context) {
    final candidates = board.candidatos;
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 18),
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: PlacarColors.borda, width: 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Mentirômetro',
            textAlign: TextAlign.center,
            style: PlacarType.title(26),
          ),
          const SizedBox(height: 4),
          if (reading == null || candidates.length < 2)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Text(
                'Aguardando os dois candidatos.',
                textAlign: TextAlign.center,
                style: PlacarType.muted(),
              ),
            )
          else ...[
            MentiromentroGauge(
              angleDegrees: reading!.angleDegrees,
              leftName: candidates[0].nome,
              rightName: candidates[1].nome,
              semanticsLabel:
                  'Mentirômetro: ${candidates[0].nome} ${reading!.left.erroPct}% de erro, ${candidates[1].nome} ${reading!.right.erroPct}%',
            ),
            const SizedBox(height: 8),
            Text(
              reading!.headline,
              textAlign: TextAlign.center,
              style: PlacarType.heading(17),
            ),
            const SizedBox(height: 2),
            Text(
              reading!.detail,
              textAlign: TextAlign.center,
              style: PlacarType.muted(12.5),
            ),
            Text(
              reading!.basis,
              textAlign: TextAlign.center,
              style: PlacarType.muted(12.5),
            ),
            const SizedBox(height: 14),
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: CandidateMeter(
                    candidate: candidates[0],
                    index: reading!.left,
                    alignEnd: false,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: CandidateMeter(
                    candidate: candidates[1],
                    index: reading!.right,
                    alignEnd: true,
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class CandidateMeter extends StatelessWidget {
  const CandidateMeter({
    required this.candidate,
    required this.index,
    required this.alignEnd,
    super.key,
  });

  final Candidate candidate;
  final ErrorIndex index;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final align = alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final textAlign = alignEnd ? TextAlign.right : TextAlign.left;
    final shown = index.total == 0 ? '–' : '${index.erroPct}';
    return Column(
      crossAxisAlignment: align,
      children: [
        Text(candidate.nome,
            textAlign: textAlign, style: PlacarType.heading(18)),
        const SizedBox(height: 2),
        Text.rich(
          textAlign: textAlign,
          TextSpan(
            children: [
              TextSpan(
                text: shown,
                style: PlacarType.title(40).copyWith(color: PlacarColors.falso),
              ),
              if (index.total > 0)
                TextSpan(
                  text: '% de erro',
                  style:
                      PlacarType.strong(13).copyWith(color: PlacarColors.falso),
                ),
            ],
          ),
        ),
        const SizedBox(height: 6),
        _SplitBar(
          verdadeiro: index.verdadeiroPct,
          impreciso: index.imprecisoPct,
          falso: index.falsoPct,
          reversed: alignEnd,
        ),
        const SizedBox(height: 4),
        Text(
          '${candidate.verdadeiro} verdadeiro · ${candidate.impreciso} impreciso · ${candidate.falso} falso',
          textAlign: textAlign,
          style: PlacarType.muted(12),
        ),
        Text(
          '${candidate.semDados} sem dados',
          textAlign: textAlign,
          style: PlacarType.muted(12),
        ),
      ],
    );
  }
}

class _SplitBar extends StatelessWidget {
  const _SplitBar({
    required this.verdadeiro,
    required this.impreciso,
    required this.falso,
    required this.reversed,
  });

  final int verdadeiro;
  final int impreciso;
  final int falso;
  final bool reversed;

  @override
  Widget build(BuildContext context) {
    final segments = <Widget>[
      if (verdadeiro > 0) _seg(PlacarColors.verdadeiro, verdadeiro),
      if (impreciso > 0) _seg(PlacarColors.impreciso, impreciso),
      if (falso > 0) _seg(PlacarColors.falso, falso),
    ];
    return Semantics(
      label: '$verdadeiro% verdadeiro, $impreciso% impreciso, $falso% falso',
      child: ClipRRect(
        borderRadius: BorderRadius.circular(5),
        child: SizedBox(
          height: 10,
          child: ColoredBox(
            color: PlacarColors.fundo,
            child: segments.isEmpty
                ? const SizedBox.expand()
                : Row(
                    textDirection:
                        reversed ? TextDirection.rtl : TextDirection.ltr,
                    children: segments,
                  ),
          ),
        ),
      ),
    );
  }

  Widget _seg(Color color, int flex) {
    return Expanded(flex: flex, child: ColoredBox(color: color));
  }
}

class LightLiveStrip extends StatelessWidget {
  const LightLiveStrip({required this.board, super.key});

  final Scoreboard board;

  @override
  Widget build(BuildContext context) {
    return EverySecond(
      builder: (context, now) {
        final status = statusCopy(board, now);
        final ended = board.encerrado;
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: PlacarColors.tela,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              StatusLine(status: status, strong: true),
              const SizedBox(height: 6),
              if (ended != null)
                _Countdown(board: board, now: now, light: true)
              else
                Text(
                  rotuloDuracao(posicaoDoDebate(board, now)),
                  style: PlacarType.muted(14),
                ),
              if (board.video?.hasStream == true && ended == null) ...[
                const SizedBox(height: 10),
                _LiveButton(videoId: board.video!.id),
              ],
            ],
          ),
        );
      },
    );
  }
}

class DarkLivePanel extends StatelessWidget {
  const DarkLivePanel({required this.board, super.key});

  final Scoreboard board;

  @override
  Widget build(BuildContext context) {
    return EverySecond(
      builder: (context, now) {
        final ended = board.encerrado;
        return ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: AspectRatio(
            aspectRatio: ended == null ? 16 / 9 : 16 / 10,
            child: ColoredBox(
              color: PlacarColors.tinta,
              child: ended != null
                  ? _EndedScreen(board: board, now: now)
                  : _Broadcast(board: board, now: now),
            ),
          ),
        );
      },
    );
  }
}

class _Broadcast extends StatelessWidget {
  const _Broadcast({required this.board, required this.now});

  final Scoreboard board;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final video = board.video;
    if (video != null && video.hasStream && !board.simulated) {
      return Stack(
        fit: StackFit.expand,
        children: [
          Image.network(
            'https://i.ytimg.com/vi/${video.id}/hqdefault.jpg',
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
          ),
          const DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [Color(0x66000000), Color(0xCC000000)],
              ),
            ),
          ),
          Center(
            child: _LiveButton(videoId: video.id, onDark: true),
          ),
        ],
      );
    }
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            board.simulated
                ? 'Debate simulado'
                : (board.aviso ?? 'Transmissão'),
            textAlign: TextAlign.center,
            style: PlacarType.title(34).copyWith(color: Colors.white),
          ),
          const SizedBox(height: 10),
          Text(
            rotuloDuracao(posicaoDoDebate(board, now)),
            style:
                PlacarType.heading(22).copyWith(color: PlacarColors.impreciso),
          ),
          const SizedBox(height: 8),
          Text(
            board.simulated
                ? 'Sem sinal de vídeo nesta simulação. Os números ao lado são ilustrativos.'
                : 'A live abre no YouTube quando o placar publica um vídeo.',
            textAlign: TextAlign.center,
            style: PlacarType.body(14).copyWith(color: PlacarColors.borda),
          ),
        ],
      ),
    );
  }
}

class _EndedScreen extends StatelessWidget {
  const _EndedScreen({required this.board, required this.now});

  final Scoreboard board;
  final DateTime now;

  @override
  Widget build(BuildContext context) {
    final ended = board.encerrado!;
    final when = DateTime.tryParse(ended.proximo);
    final videoDate = board.video?.data == null
        ? null
        : DateTime.tryParse(board.video!.data!);
    final day = videoDate == null
        ? dataCurta(board.atualizado)
        : dataCurta(videoDate.millisecondsSinceEpoch);
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            'Debate de $day encerrado · o placar final está logo abaixo',
            textAlign: TextAlign.center,
            style: PlacarType.body(14).copyWith(color: PlacarColors.borda),
          ),
          const SizedBox(height: 10),
          Text(
            'Próximo debate',
            style: PlacarType.strong(15).copyWith(color: PlacarColors.borda),
          ),
          const SizedBox(height: 6),
          Text(
            ended.texto,
            textAlign: TextAlign.center,
            style: PlacarType.title(28).copyWith(color: Colors.white),
          ),
          const SizedBox(height: 8),
          Text(
            when == null ? '' : faltaPara(when, now),
            textAlign: TextAlign.center,
            style: PlacarType.title(32).copyWith(color: PlacarColors.impreciso),
          ),
          const SizedBox(height: 8),
          Text(
            'Estamos aprimorando os métodos de checagem para o próximo debate.',
            textAlign: TextAlign.center,
            style: PlacarType.body(13).copyWith(color: PlacarColors.borda),
          ),
        ],
      ),
    );
  }
}

class _Countdown extends StatelessWidget {
  const _Countdown(
      {required this.board, required this.now, required this.light});

  final Scoreboard board;
  final DateTime now;
  final bool light;

  @override
  Widget build(BuildContext context) {
    final when = DateTime.tryParse(board.encerrado!.proximo);
    if (when == null) return const SizedBox.shrink();
    return Text(
      'próximo debate em ${faltaPara(when, now)}',
      style: PlacarType.muted(14).copyWith(
        color: light ? PlacarColors.apagado : Colors.white,
      ),
    );
  }
}

class _LiveButton extends StatelessWidget {
  const _LiveButton({required this.videoId, this.onDark = false});

  final String videoId;
  final bool onDark;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      style: FilledButton.styleFrom(
        backgroundColor: onDark ? Colors.white : PlacarColors.tinta,
        foregroundColor: onDark ? PlacarColors.tinta : Colors.white,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      ),
      onPressed: () => openExternal('https://www.youtube.com/watch?v=$videoId'),
      child: Text('▶ Ver a live', style: PlacarType.strong(14)),
    );
  }
}

class StatusLine extends StatelessWidget {
  const StatusLine({required this.status, this.strong = false, super.key});

  final StatusCopy status;
  final bool strong;

  @override
  Widget build(BuildContext context) {
    final style = strong ? PlacarType.strong(14) : PlacarType.body(13.5);
    return Row(
      children: [
        PulseDot(on: status.vivo),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            status.texto,
            style: style.copyWith(
              color: status.vivo ? PlacarColors.falso : PlacarColors.apagado,
            ),
          ),
        ),
      ],
    );
  }
}
