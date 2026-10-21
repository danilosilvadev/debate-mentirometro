import 'models.dart';

class TimelineColumn {
  const TimelineColumn({
    required this.block,
    required this.attacks,
    required this.proposals,
    required this.startMs,
    required this.endMs,
  });

  final int block;
  final int attacks;
  final int proposals;
  final int startMs;
  final int endMs;
}

class TimelineRow {
  const TimelineRow({
    required this.candidateId,
    required this.name,
    required this.columns,
  });

  final String candidateId;
  final String name;
  final List<TimelineColumn> columns;
}

class DebateTimeline {
  const DebateTimeline({
    required this.rows,
    required this.labelStep,
    required this.maxStack,
  });

  final List<TimelineRow> rows;

  /// De quantas em quantas colunas o eixo mostra a hora (no máximo ~6 rótulos).
  final int labelStep;
  final int maxStack;

  static const empty = DebateTimeline(rows: [], labelStep: 1, maxStack: 1);

  bool get isEmpty => rows.isEmpty || rows.every((row) => row.columns.isEmpty);

  static DebateTimeline build({
    required Map<int, MinuteMark> linha,
    required List<Candidate> candidates,
    required int originMs,
  }) {
    if (linha.isEmpty || candidates.isEmpty) return empty;
    final minutes = linha.keys.toList();
    final first = minutes.reduce((a, b) => a < b ? a : b);
    final last = minutes.reduce((a, b) => a > b ? a : b);
    final ini = first ~/ 5;
    final fim = last ~/ 5;
    final blocks = [for (var block = ini; block <= fim; block++) block];

    int sum(int block, String key) {
      var total = 0;
      for (var offset = 0; offset < 5; offset++) {
        total += linha[block * 5 + offset]?[key] ?? 0;
      }
      return total;
    }

    var maxStack = 1;
    final rows = <TimelineRow>[];
    for (final candidate in candidates) {
      final columns = <TimelineColumn>[];
      for (final block in blocks) {
        final attacks = sum(block, 'a${candidate.id}');
        final proposals = sum(block, 'p${candidate.id}');
        final stack = attacks + proposals;
        if (stack > maxStack) maxStack = stack;
        columns.add(
          TimelineColumn(
            block: block,
            attacks: attacks,
            proposals: proposals,
            startMs: originMs + block * 300000,
            endMs: originMs + (block + 1) * 300000,
          ),
        );
      }
      rows.add(
        TimelineRow(
          candidateId: candidate.id,
          name: candidate.nome,
          columns: columns,
        ),
      );
    }

    final step = blocks.isEmpty ? 1 : (blocks.length / 6).ceil().clamp(1, 999);
    return DebateTimeline(rows: rows, labelStep: step, maxStack: maxStack);
  }
}
