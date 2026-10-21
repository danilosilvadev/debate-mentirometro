import 'package:flutter/material.dart';

import '../../domain/models.dart';
import '../../theme/placar_theme.dart';
import 'chrome.dart';

class ToneSection extends StatelessWidget {
  const ToneSection({
    required this.board,
    required this.onOpenProposals,
    super.key,
  });

  final Scoreboard board;
  final VoidCallback onOpenProposals;

  @override
  Widget build(BuildContext context) {
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Propostas ou ataques?', style: PlacarType.title(26)),
          const SizedBox(height: 4),
          Text(
            'Quantas vezes cada um apresentou uma proposta concreta e quantas vezes atacou o adversário. A barra mostra como cada um usou o tempo de fala.',
            style: PlacarType.muted(14.5),
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final stacked = constraints.maxWidth < 720;
              final cards = [
                for (final candidate in board.candidatos)
                  CandidateTone(board: board, candidate: candidate),
              ];
              if (stacked) {
                return Column(
                  children: [
                    for (var i = 0; i < cards.length; i++) ...[
                      if (i > 0) const SizedBox(height: 18),
                      cards[i],
                    ],
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < cards.length; i++) ...[
                    if (i > 0) const SizedBox(width: 24),
                    Expanded(child: cards[i]),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: 12),
          TextButton(
            key: const Key('open-proposals'),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              minimumSize: const Size(0, 36),
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              foregroundColor: PlacarColors.tinta,
            ),
            onPressed: onOpenProposals,
            child: Text(
              'Ver as propostas explicadas',
              style: PlacarType.strong(15).copyWith(
                decoration: TextDecoration.underline,
                decorationColor: PlacarColors.tinta,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class CandidateTone extends StatelessWidget {
  const CandidateTone(
      {required this.board, required this.candidate, super.key});

  final Scoreboard board;
  final Candidate candidate;

  @override
  Widget build(BuildContext context) {
    final shares = speakingShares(candidate.tempo);
    final recent =
        board.ataques.where((attack) => attack.quem == candidate.id).take(3);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(candidate.nome, style: PlacarType.heading(20)),
        const SizedBox(height: 6),
        Wrap(
          spacing: 20,
          runSpacing: 8,
          children: [
            _Count(
                value: candidate.propostas,
                label: 'propostas',
                color: PlacarColors.proposta),
            _Count(
                value: candidate.ataques,
                label: 'ataques',
                color: PlacarColors.ataque),
          ],
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(6),
          child: SizedBox(
            height: 12,
            child: Row(
              children: [
                for (final share in shares)
                  if (share.seconds > 0)
                    Expanded(
                      flex: (share.seconds * 10).round().clamp(1, 1000000),
                      child: ColoredBox(color: _toneColor(share.key)),
                    ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            for (final share in shares)
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: _toneColor(share.key),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${share.percent}% ${share.label}',
                    style: PlacarType.muted(12.5),
                  ),
                ],
              ),
          ],
        ),
        if (recent.isNotEmpty) ...[
          const SizedBox(height: 8),
          for (final attack in recent)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(attack.resumo, style: PlacarType.muted(13.5)),
            ),
        ],
      ],
    );
  }
}

class _Count extends StatelessWidget {
  const _Count({required this.value, required this.label, required this.color});

  final int value;
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$value',
            style: PlacarType.title(38).copyWith(color: color, height: 1)),
        Text(label, style: PlacarType.muted(13)),
      ],
    );
  }
}

Color _toneColor(String key) {
  switch (key) {
    case 'proposta':
      return PlacarColors.proposta;
    case 'ataque':
      return PlacarColors.ataque;
    case 'defesa':
      return PlacarColors.defesa;
    case 'balanco':
      return PlacarColors.balanco;
    default:
      return PlacarColors.borda;
  }
}
