import 'package:flutter/material.dart';

import '../../domain/fact_query.dart';
import '../../domain/models.dart';
import '../../domain/timeline.dart';
import '../../theme/placar_theme.dart';
import '../placar_format.dart';
import 'chrome.dart';

class TimelineSection extends StatelessWidget {
  const TimelineSection({
    required this.board,
    required this.filter,
    required this.onSelect,
    super.key,
  });

  final Scoreboard board;
  final FactFilter filter;
  final void Function(TimelineColumn column) onSelect;

  @override
  Widget build(BuildContext context) {
    final timeline = DebateTimeline.build(
      linha: board.linha,
      candidates: board.candidatos,
      originMs: board.timelineOriginMs,
    );
    return SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Linha do tempo', style: PlacarType.title(26)),
          const SizedBox(height: 4),
          Text(
            'Quando cada um atacou e quando apresentou propostas, a cada 5 minutos de debate. Toque numa coluna para ver os fatos checados daqueles minutos.',
            style: PlacarType.muted(14.5),
          ),
          const SizedBox(height: 12),
          const Wrap(
            spacing: 16,
            children: [
              _LegendDot(color: PlacarColors.ataque, label: 'Ataques'),
              _LegendDot(color: PlacarColors.proposta, label: 'Propostas'),
            ],
          ),
          const SizedBox(height: 12),
          if (timeline.isEmpty)
            Text(
              'A linha do tempo começa no primeiro ataque ou proposta.',
              style: PlacarType.muted(),
            )
          else
            _Chart(timeline: timeline, filter: filter, onSelect: onSelect),
        ],
      ),
    );
  }
}

class _Chart extends StatelessWidget {
  const _Chart({
    required this.timeline,
    required this.filter,
    required this.onSelect,
  });

  final DebateTimeline timeline;
  final FactFilter filter;
  final void Function(TimelineColumn column) onSelect;

  @override
  Widget build(BuildContext context) {
    final columns = timeline.rows.first.columns;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 108,
          child: Column(
            children: [
              for (final row in timeline.rows)
                SizedBox(
                  height: 80,
                  child: Align(
                    alignment: Alignment.bottomLeft,
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 6, right: 8),
                      child: Text(
                        row.name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: PlacarType.heading(15),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (final row in timeline.rows)
                  SizedBox(
                    height: 80,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        for (final column in row.columns)
                          _ColumnButton(
                            column: column,
                            candidateId: row.candidateId,
                            name: row.name,
                            maxStack: timeline.maxStack,
                            active: filter.windowStartMs == column.startMs,
                            onTap: () => onSelect(column),
                          ),
                      ],
                    ),
                  ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    for (var i = 0; i < columns.length; i++)
                      SizedBox(
                        width: 26,
                        child: Text(
                          i % timeline.labelStep == 0
                              ? hhmm(columns[i].startMs)
                              : '',
                          style: PlacarType.muted(11),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ColumnButton extends StatelessWidget {
  const _ColumnButton({
    required this.column,
    required this.candidateId,
    required this.name,
    required this.maxStack,
    required this.active,
    required this.onTap,
  });

  final TimelineColumn column;
  final String candidateId;
  final String name;
  final int maxStack;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final attacks = column.attacks;
    final proposals = column.proposals;
    final label =
        '${hhmm(column.startMs)}–${hhmm(column.endMs)}: $attacks ${attacks == 1 ? 'ataque' : 'ataques'}, $proposals ${proposals == 1 ? 'proposta' : 'propostas'}. Toque para ver os fatos desses minutos';
    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: Semantics(
        button: true,
        label: '$name, $label',
        child: Material(
          color: active ? PlacarColors.fundo : Colors.transparent,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
          child: InkWell(
            key: Key('timeline-$candidateId-${column.startMs}'),
            onTap: onTap,
            child: Container(
              width: 24,
              height: 72,
              alignment: Alignment.bottomCenter,
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(
                    color: active ? PlacarColors.proposta : PlacarColors.borda,
                    width: active ? 3 : 1,
                  ),
                ),
              ),
              child: _Bars(
                  attacks: attacks, proposals: proposals, maxStack: maxStack),
            ),
          ),
        ),
      ),
    );
  }
}

class _Bars extends StatelessWidget {
  const _Bars({
    required this.attacks,
    required this.proposals,
    required this.maxStack,
  });

  final int attacks;
  final int proposals;
  final int maxStack;

  @override
  Widget build(BuildContext context) {
    const gap = 2.0;
    final both = attacks > 0 && proposals > 0;
    final inner = 70 - (both ? gap : 0);
    final attackH = attacks / maxStack * inner;
    final proposalH = proposals / maxStack * inner;
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        if (attacks > 0)
          Container(
            height: attackH.clamp(2, 70).toDouble(),
            decoration: const BoxDecoration(
              color: PlacarColors.ataque,
              borderRadius: BorderRadius.vertical(top: Radius.circular(3)),
            ),
          ),
        if (both) const SizedBox(height: gap),
        if (proposals > 0)
          Container(
            height: proposalH.clamp(2, 70).toDouble(),
            color: PlacarColors.proposta,
          ),
      ],
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 6),
        Text(label, style: PlacarType.muted(13.5)),
      ],
    );
  }
}
