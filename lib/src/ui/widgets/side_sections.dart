import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/placar_endpoints.dart';
import '../../domain/fact_query.dart';
import '../../domain/models.dart';
import '../../domain/verdict.dart';
import '../../providers.dart';
import '../../theme/placar_theme.dart';
import '../open_link.dart';
import '../placar_format.dart';
import 'chrome.dart';

class HighlightsStrip extends ConsumerWidget {
  const HighlightsStrip({required this.board, super.key});

  final Scoreboard board;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = FactQuery.highlights(board.declaracoes);
    if (items.isEmpty) return const SizedBox.shrink();
    final revised = FactQuery.highlightsAreRevisions(board.declaracoes);
    return Padding(
      padding: const EdgeInsets.only(top: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            revised
                ? 'Destaques da revisão: vereditos que mudaram'
                : 'Destaques: últimos falsos e imprecisos',
            style: PlacarType.heading(20),
          ),
          const SizedBox(height: 8),
          SizedBox(
            height: 168,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: items.length,
              separatorBuilder: (context, index) => const SizedBox(width: 12),
              itemBuilder: (context, index) {
                final claim = items[index];
                return _HighlightCard(
                  board: board,
                  claim: claim,
                  onTap: () {
                    ref.read(factFilterProvider.notifier).state =
                        const FactFilter();
                    ref.read(selectedFactIdProvider.notifier).state = claim.id;
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _HighlightCard extends StatelessWidget {
  const _HighlightCard({
    required this.board,
    required this.claim,
    required this.onTap,
  });

  final Scoreboard board;
  final FactClaim claim;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final nome = board.candidateById(claim.quem)?.nome ?? '';
    return SizedBox(
      width: 280,
      child: Material(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(10),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border(
                left: BorderSide(color: _edge(claim.veredito), width: 6),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                VerdictBadge(verdict: claim.veredito, compact: true),
                if (claim.corrigido != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'era ${claim.corrigido!.antes.label}',
                      style: PlacarType.muted(12),
                    ),
                  ),
                const SizedBox(height: 6),
                Text(nome, style: PlacarType.strong(14)),
                const SizedBox(height: 4),
                Expanded(
                  child: Text(
                    claim.afirmacao,
                    maxLines: 4,
                    overflow: TextOverflow.ellipsis,
                    style: PlacarType.body(14.5),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

Color _edge(Verdict verdict) {
  switch (verdict) {
    case Verdict.verdadeiro:
      return PlacarColors.verdadeiro;
    case Verdict.impreciso:
      return PlacarColors.impreciso;
    case Verdict.falso:
      return PlacarColors.falso;
    case Verdict.semDados:
      return PlacarColors.borda;
    case Verdict.emRevisao:
      return PlacarColors.apagado;
  }
}

class RevisionCard extends ConsumerWidget {
  const RevisionCard({required this.board, super.key});

  final Scoreboard board;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final revision = board.revisao;
    if (revision == null || board.candidatos.length < 2) {
      return const SizedBox.shrink();
    }
    final left = board.candidatos[0];
    final right = board.candidatos[1];
    final changed = revision.mudancas
        .where(
            (change) => change.depois != null && change.depois != change.antes)
        .length;
    final removed =
        revision.mudancas.where((change) => change.depois == null).length;
    final filter = ref.watch(factFilterProvider);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
        border: const Border(
          left: BorderSide(color: PlacarColors.proposta, width: 6),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text.rich(
            TextSpan(
              style: PlacarType.body(14.5),
              children: [
                TextSpan(
                  text:
                      '✎ Dados revisados e corrigidos pelo ${revision.por} após o debate. ',
                  style: PlacarType.strong(14.5),
                ),
                TextSpan(
                  text:
                      '$changed vereditos corrigidos · $removed checagens removidas · erro ao vivo → revisado: ',
                ),
                TextSpan(
                  text:
                      '${left.nome} ${erroRevisaoTexto(revision.antes[left.id])} → ${erroRevisaoTexto(revision.depois[left.id])}',
                  style: PlacarType.strong(14.5),
                ),
                const TextSpan(text: ' · '),
                TextSpan(
                  text:
                      '${right.nome} ${erroRevisaoTexto(revision.antes[right.id])} → ${erroRevisaoTexto(revision.depois[right.id])}',
                  style: PlacarType.strong(14.5),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Theme(
            data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(top: 4),
              title:
                  Text('Ver detalhes da revisão', style: PlacarType.strong(15)),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: Text(revision.resumo, style: PlacarType.body(15)),
                ),
                if (!filter.onlyCorrected)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        foregroundColor: PlacarColors.tinta,
                      ),
                      onPressed: () {
                        ref.read(factFilterProvider.notifier).state = filter
                            .copy(onlyCorrected: true, clearVerdict: true);
                      },
                      child: Text(
                        'Mostrar só os fatos corrigidos',
                        style: PlacarType.body(14).copyWith(
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxHeight: 360),
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: revision.mudancas.length,
                    itemBuilder: (context, index) {
                      final change = revision.mudancas[index];
                      final after = change.depois == null
                          ? 'removida'
                          : change.depois == change.antes
                              ? 'mantido, explicação corrigida'
                              : change.depois!.label;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Text.rich(
                          TextSpan(
                            style: PlacarType.body(14.5),
                            children: [
                              TextSpan(
                                text: '${change.quem}: ',
                                style: PlacarType.strong(14.5),
                              ),
                              TextSpan(text: '${change.afirmacao} '),
                              TextSpan(
                                text: '${change.antes.label} → $after',
                                style: PlacarType.strong(14),
                              ),
                              TextSpan(
                                text: '\n${change.motivo}',
                                style: PlacarType.muted(13),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
                if (revision.aoVivo != null &&
                    ref.watch(feedModeProvider) == FeedMode.live &&
                    ref.watch(archiveProvider) != revision.aoVivo)
                  Align(
                    alignment: Alignment.centerLeft,
                    child: TextButton(
                      style: TextButton.styleFrom(
                        padding: EdgeInsets.zero,
                        foregroundColor: PlacarColors.tinta,
                      ),
                      onPressed: () {
                        ref.read(archiveProvider.notifier).state =
                            revision.aoVivo;
                      },
                      child: Text(
                        'Ver o placar como ficou ao vivo, sem a revisão',
                        style: PlacarType.body(14).copyWith(
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class InfoSection extends StatelessWidget {
  const InfoSection({required this.board, super.key});

  final Scoreboard board;

  @override
  Widget build(BuildContext context) {
    final share = placarShareText(board);
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 820;
        final cards = [
          const _HowToRead(),
          _HowItWorks(board: board),
          _ShareBox(text: share),
        ];
        if (!wide) {
          return Column(
            children: [
              for (final card in cards)
                Padding(padding: const EdgeInsets.only(top: 16), child: card),
            ],
          );
        }
        return Padding(
          padding: const EdgeInsets.only(top: 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                if (i > 0) const SizedBox(width: 12),
                Expanded(child: cards[i]),
              ],
            ],
          ),
        );
      },
    );
  }
}

class _HowToRead extends StatelessWidget {
  const _HowToRead();

  @override
  Widget build(BuildContext context) {
    return const PlacarCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _CardTitle('Como ler'),
          _LegendRow(verdict: Verdict.verdadeiro, text: 'os dados confirmam'),
          _LegendRow(
              verdict: Verdict.impreciso,
              text: 'exagerado ou fora de contexto'),
          _LegendRow(verdict: Verdict.falso, text: 'os dados contradizem'),
          _LegendRow(verdict: Verdict.semDados, text: 'não deu para verificar'),
          _LegendRow(
            verdict: Verdict.emRevisao,
            text:
                'o áudio não confirmou a frase; fica fora do placar até a conferência',
          ),
          SizedBox(height: 8),
          Text(
            'O Mentirômetro pende para quem teve mais afirmações falsas ou imprecisas (imprecisa conta meio ponto). "Sem dados" fica de fora.',
          ),
        ],
      ),
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow({required this.verdict, required this.text});

  final Verdict verdict;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          VerdictBadge(verdict: verdict, compact: true),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: PlacarType.body(14.5))),
        ],
      ),
    );
  }
}

class _HowItWorks extends ConsumerWidget {
  const _HowItWorks({required this.board});

  final Scoreboard board;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final archive = ref.watch(archiveProvider);
    return PlacarCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle('Como funciona'),
          const Text(
            'O áudio do debate é transcrito a cada 10 segundos e a voz identifica quem está falando. Uma IA lê cada fala e separa as afirmações que valem checagem (números, dados, atos de governo), as propostas concretas e os ataques ao adversário. Retórica e opinião não viram checagem.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Cada afirmação é buscada na web (agências de checagem, imprensa e dados oficiais) e julgada com as mesmas regras para os dois candidatos.',
          ),
          const SizedBox(height: 8),
          const Text(
            'Antes de publicar um "falso" ou "impreciso", o trecho é ouvido de novo por outros modelos para confirmar a frase exata. Se o áudio não confirmar, o fato fica "em revisão" e não conta no placar.',
          ),
          const SizedBox(height: 8),
          Text.rich(
            TextSpan(
              style: PlacarType.body(),
              children: const [
                TextSpan(
                  text: 'É uma checagem automática e pode errar. ',
                  style: TextStyle(fontWeight: FontWeight.w800),
                ),
                TextSpan(text: 'Confira a fonte antes de compartilhar.'),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            board.simulated
                ? 'Você está na simulação local. O texto acima descreve o placar publicado.'
                : 'Fonte dos dados: ${PlacarEndpoints.describe(archive: archive)}',
            style: PlacarType.muted(13),
          ),
        ],
      ),
    );
  }
}

class _ShareBox extends StatelessWidget {
  const _ShareBox({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return PlacarCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _CardTitle('Mostre o placar'),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: PlacarColors.tinta,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6)),
                ),
                onPressed: () => openExternal(xUrl(text)),
                child: const Text('Postar no X'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: PlacarColors.tinta,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6)),
                ),
                onPressed: () => openExternal(whatsAppUrl(text)),
                child: const Text('Enviar no WhatsApp'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _CardTitle extends StatelessWidget {
  const _CardTitle(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(text, style: PlacarType.heading(18)),
    );
  }
}
