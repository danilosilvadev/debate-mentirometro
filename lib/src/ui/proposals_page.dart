import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/models.dart';
import '../providers.dart';
import '../theme/placar_theme.dart';
import 'widgets/chrome.dart';

class ProposalsPage extends ConsumerWidget {
  const ProposalsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncBoard = ref.watch(scoreboardProvider);
    final board = asyncBoard.asData?.value.board;
    return Scaffold(
      body: SafeArea(
        child: board == null
            ? const Center(child: Text('Conectando…'))
            : Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(8, 8, 16, 0),
                    child: Row(
                      children: [
                        IconButton(
                          onPressed: () => Navigator.of(context).maybePop(),
                          icon: const Icon(Icons.arrow_back),
                          tooltip: 'Voltar ao placar',
                        ),
                        Expanded(
                          child: Text('Propostas explicadas',
                              style: PlacarType.title(28)),
                        ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1180),
                        child: ListView(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                          children: [
                            Text(
                              'O que cada candidato propôs de concreto, da proposta mais repetida para a mais recente.',
                              style: PlacarType.muted(14.5),
                            ),
                            const SizedBox(height: 12),
                            LayoutBuilder(
                              builder: (context, constraints) {
                                final columns = [
                                  for (final candidate in board.candidatos)
                                    _CandidateProposals(
                                        board: board, candidate: candidate),
                                ];
                                if (constraints.maxWidth < 800) {
                                  return Column(
                                    children: [
                                      for (var i = 0;
                                          i < columns.length;
                                          i++) ...[
                                        if (i > 0) const SizedBox(height: 20),
                                        columns[i],
                                      ],
                                    ],
                                  );
                                }
                                return Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    for (var i = 0;
                                        i < columns.length;
                                        i++) ...[
                                      if (i > 0) const SizedBox(width: 16),
                                      Expanded(child: columns[i]),
                                    ],
                                  ],
                                );
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _CandidateProposals extends StatelessWidget {
  const _CandidateProposals({required this.board, required this.candidate});

  final Scoreboard board;
  final Candidate candidate;

  @override
  Widget build(BuildContext context) {
    final mine = board.propostas
        .where((proposal) => proposal.quem == candidate.id)
        .toList()
      ..sort((a, b) =>
          b.vezes != a.vezes ? b.vezes.compareTo(a.vezes) : b.t.compareTo(a.t));
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(candidate.nome, style: PlacarType.heading(22)),
        const SizedBox(height: 8),
        if (mine.isEmpty)
          const PlacarCard(
            child: Text('Nenhuma proposta concreta até agora.'),
          )
        else
          for (final proposal in mine)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.fromLTRB(12, 12, 14, 12),
              decoration: BoxDecoration(
                color: PlacarColors.tela,
                borderRadius: BorderRadius.circular(10),
                border: const Border(
                  left: BorderSide(color: PlacarColors.proposta, width: 5),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(proposal.titulo, style: PlacarType.strong(16.5)),
                  const SizedBox(height: 4),
                  Text(proposal.explicacao, style: PlacarType.body(15)),
                  if (proposal.vezes > 1)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        'Citada ${proposal.vezes} vezes',
                        style: PlacarType.muted(13),
                      ),
                    ),
                ],
              ),
            ),
      ],
    );
  }
}
