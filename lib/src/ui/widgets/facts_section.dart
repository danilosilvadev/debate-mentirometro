import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../domain/fact_query.dart';
import '../../domain/models.dart';
import '../../domain/verdict.dart';
import '../../providers.dart';
import '../../theme/placar_theme.dart';
import '../open_link.dart';
import '../placar_format.dart';
import 'chrome.dart';

class FactsSection extends ConsumerWidget {
  const FactsSection({
    required this.board,
    required this.freshIds,
    super.key,
  });

  final Scoreboard board;
  final Set<String> freshIds;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final filter = ref.watch(factFilterProvider);
    final selectedId = ref.watch(selectedFactIdProvider);
    final order = effectiveOrder(board, filter.order);
    final visible =
        FactQuery.sorted(FactQuery.apply(board.declaracoes, filter), order);
    final byPerson = FactQuery.apply(board.declaracoes, filter, ignore: 'quem');
    final byVerdict =
        FactQuery.apply(board.declaracoes, filter, ignore: 'vered');

    int countVerdict(Verdict verdict) =>
        byVerdict.where((claim) => claim.veredito == verdict).length;

    final showRevisionChip =
        board.declaracoes.any((claim) => claim.corrigido != null);
    final correctedCount =
        byVerdict.where((claim) => claim.corrigido != null).length;
    final totalLabel = visible.length == board.declaracoes.length
        ? '(${board.declaracoes.length})'
        : '(${visible.length} de ${board.declaracoes.length})';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text.rich(
          TextSpan(
            children: [
              TextSpan(text: 'Fatos checados ', style: PlacarType.heading(22)),
              TextSpan(text: totalLabel, style: PlacarType.muted(14)),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            FilterPill(
              label: 'Todos',
              count: '${byPerson.length}',
              selected: filter.quem == null,
              onTap: () => ref.read(factFilterProvider.notifier).state =
                  filter.copy(clearQuem: true),
            ),
            for (final candidate in board.candidatos)
              FilterPill(
                label: candidate.nome,
                count:
                    '${byPerson.where((claim) => claim.quem == candidate.id).length}',
                selected: filter.quem == candidate.id,
                onTap: () => ref.read(factFilterProvider.notifier).state =
                    filter.copy(quem: candidate.id),
              ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final verdict in Verdict.values)
              if (verdict != Verdict.emRevisao || countVerdict(verdict) > 0)
                FilterPill(
                  label: verdict.label,
                  count: '${countVerdict(verdict)}',
                  selected: filter.verdict == verdict && !filter.onlyCorrected,
                  dot: _dot(verdict),
                  dashedDot: verdict == Verdict.emRevisao,
                  onTap: () {
                    final same =
                        filter.verdict == verdict && !filter.onlyCorrected;
                    ref.read(factFilterProvider.notifier).state = filter.copy(
                      clearVerdict: same,
                      verdict: same ? null : verdict,
                      onlyCorrected: false,
                    );
                  },
                ),
            if (showRevisionChip)
              FilterPill(
                label: '✎ Corrigidos',
                count: '$correctedCount',
                selected: filter.onlyCorrected,
                onTap: () {
                  ref.read(factFilterProvider.notifier).state = filter.copy(
                    onlyCorrected: !filter.onlyCorrected,
                    clearVerdict: true,
                  );
                },
              ),
          ],
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            if (filter.hasWindow)
              FilterPill(
                label:
                    '${hhmm(filter.windowStartMs!)}–${hhmm(filter.windowEndMs!)} ✕',
                selected: true,
                onTap: () => ref.read(factFilterProvider.notifier).state =
                    filter.copy(clearWindow: true),
              ),
            FilterPill(
              label: order == FactOrder.recentes
                  ? '↓ Mais recentes primeiro'
                  : '↓ Na ordem do debate',
              selected: false,
              onTap: () {
                final next = order == FactOrder.recentes
                    ? FactOrder.debate
                    : FactOrder.recentes;
                ref.read(factFilterProvider.notifier).state =
                    filter.copy(order: next);
              },
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (visible.isEmpty)
          PlacarCard(
            child: Text(
              board.declaracoes.isEmpty
                  ? 'Os fatos aparecem aqui quando um candidato citar um dado que dá para checar.'
                  : 'Nenhum fato com esses filtros.',
              style: PlacarType.muted(),
            ),
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final cards = [
                for (final claim in visible)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: FactCard(
                      board: board,
                      claim: claim,
                      fresh: freshIds.contains(claim.id),
                      forceOpen: selectedId == claim.id,
                    ),
                  ),
              ];
              if (constraints.maxWidth < 860) {
                return Column(children: cards);
              }
              final left = <Widget>[];
              final right = <Widget>[];
              for (var i = 0; i < cards.length; i++) {
                (i.isEven ? left : right).add(cards[i]);
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: Column(children: left)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(children: right)),
                ],
              );
            },
          ),
      ],
    );
  }
}

Color? _dot(Verdict verdict) {
  switch (verdict) {
    case Verdict.verdadeiro:
      return PlacarColors.verdadeiro;
    case Verdict.impreciso:
      return PlacarColors.impreciso;
    case Verdict.falso:
      return PlacarColors.falso;
    case Verdict.semDados:
      return Colors.white;
    case Verdict.emRevisao:
      return null;
  }
}

class FactCard extends StatefulWidget {
  const FactCard({
    required this.board,
    required this.claim,
    required this.fresh,
    required this.forceOpen,
    super.key,
  });

  final Scoreboard board;
  final FactClaim claim;
  final bool fresh;
  final bool forceOpen;

  @override
  State<FactCard> createState() => _FactCardState();
}

class _FactCardState extends State<FactCard> {
  var _open = false;

  @override
  void initState() {
    super.initState();
    _open = widget.forceOpen;
  }

  @override
  void didUpdateWidget(FactCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.forceOpen && !oldWidget.forceOpen) {
      _open = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        Scrollable.ensureVisible(
          context,
          alignment: 0.12,
          duration: const Duration(milliseconds: 350),
        );
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final claim = widget.claim;
    final nome = widget.board.candidateById(claim.quem)?.nome ?? '';
    return AnimatedContainer(
      duration: const Duration(milliseconds: 350),
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
        boxShadow: widget.forceOpen
            ? [
                BoxShadow(
                  color: PlacarColors.proposta.withValues(alpha: 0.45),
                  spreadRadius: 2,
                ),
              ]
            : null,
      ),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border(
            left: BorderSide(color: _edge(claim.veredito), width: 6),
          ),
        ),
        padding: const EdgeInsets.fromLTRB(12, 12, 14, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 6,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                VerdictBadge(verdict: claim.veredito, compact: true),
                Text(nome, style: PlacarType.strong(15)),
                Text(hhmm(claim.t), style: PlacarType.muted(13)),
                Text('· ${claim.tema}', style: PlacarType.muted(13)),
              ],
            ),
            const SizedBox(height: 8),
            Text(claim.afirmacao, style: PlacarType.body(16.5)),
            const SizedBox(height: 4),
            InkWell(
              onTap: () => setState(() => _open = !_open),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(
                  _open ? 'Ocultar dados e fonte' : 'Ver dados e fonte',
                  style: PlacarType.strong(13.5)
                      .copyWith(color: PlacarColors.apagado),
                ),
              ),
            ),
            if (_open) ...[
              if (claim.literal != null)
                Text(
                  'Frase dita: “${claim.literal}”',
                  style: PlacarType.muted(14)
                      .copyWith(fontStyle: FontStyle.italic),
                ),
              if (claim.contexto != null)
                Text(claim.contexto!, style: PlacarType.muted(13.5)),
              if (claim.motivo != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                            text: 'Os dados: ', style: PlacarType.strong(15)),
                        TextSpan(
                            text: claim.motivo, style: PlacarType.body(15)),
                      ],
                    ),
                  ),
                ),
              if (claim.corrigido != null)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    '✎ Revisado após o debate · ao vivo era ${claim.corrigido!.antes.label}'
                    '${claim.corrigido!.afirmacaoAntes == null ? '' : ' (o robô tinha entendido: “${claim.corrigido!.afirmacaoAntes}”)'}',
                    style: PlacarType.muted(13.5),
                  ),
                ),
              const SizedBox(height: 4),
              if (claim.fonte == null)
                Text('Nenhuma fonte encontrada.', style: PlacarType.muted(13.5))
              else
                Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text('Fonte: ', style: PlacarType.muted(13.5)),
                    InkWell(
                      onTap: () => openExternal(claim.fonte!.url),
                      child: Text(
                        '${claim.fonte!.titulo} (${hostOf(claim.fonte!.url)})',
                        style: PlacarType.strong(13.5).copyWith(
                          color: PlacarColors.proposta,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ],
                ),
            ],
            const SizedBox(height: 6),
            OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: PlacarColors.tinta,
                side: const BorderSide(color: PlacarColors.borda),
                shape: const StadiumBorder(),
                visualDensity: VisualDensity.compact,
              ),
              onPressed: () => _share(context),
              child: Text('↗ Compartilhar', style: PlacarType.strong(13.5)),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _share(BuildContext context) async {
    final text = factShareText(widget.board, widget.claim);
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: PlacarColors.tela,
      showDragHandle: true,
      builder: (context) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Compartilhar este fato', style: PlacarType.title(24)),
              const SizedBox(height: 8),
              Text(widget.claim.afirmacao, style: PlacarType.body(15)),
              const SizedBox(height: 14),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilledButton(
                    style: FilledButton.styleFrom(
                        backgroundColor: PlacarColors.verdadeiro),
                    onPressed: () => openExternal(whatsAppUrl(text)),
                    child: const Text('WhatsApp'),
                  ),
                  OutlinedButton(
                    onPressed: () => openExternal(xUrl(text)),
                    child: const Text('Postar no X'),
                  ),
                  OutlinedButton(
                    onPressed: () =>
                        copyText(context, text, ok: 'Texto copiado'),
                    child: const Text('Copiar texto'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
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
