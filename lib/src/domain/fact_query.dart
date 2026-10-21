import 'models.dart';
import 'verdict.dart';

enum FactOrder { recentes, debate }

class FactFilter {
  const FactFilter({
    this.quem,
    this.verdict,
    this.onlyCorrected = false,
    this.windowStartMs,
    this.windowEndMs,
    this.order,
  });

  /// Nulo = todos os candidatos.
  final String? quem;
  final Verdict? verdict;
  final bool onlyCorrected;
  final int? windowStartMs;
  final int? windowEndMs;

  /// Nulo = ordem automática (ao vivo, recentes; depois do debate, ordem do debate).
  final FactOrder? order;

  bool get hasWindow => windowStartMs != null && windowEndMs != null;

  FactFilter copy({
    String? quem,
    bool clearQuem = false,
    Verdict? verdict,
    bool clearVerdict = false,
    bool? onlyCorrected,
    int? windowStartMs,
    int? windowEndMs,
    bool clearWindow = false,
    FactOrder? order,
    bool clearOrder = false,
  }) {
    return FactFilter(
      quem: clearQuem ? null : (quem ?? this.quem),
      verdict: clearVerdict ? null : (verdict ?? this.verdict),
      onlyCorrected: onlyCorrected ?? this.onlyCorrected,
      windowStartMs: clearWindow ? null : (windowStartMs ?? this.windowStartMs),
      windowEndMs: clearWindow ? null : (windowEndMs ?? this.windowEndMs),
      order: clearOrder ? null : (order ?? this.order),
    );
  }
}

FactOrder effectiveOrder(Scoreboard board, FactOrder? override) {
  if (override != null) return override;
  if (board.encerrado != null || board.revisao != null) return FactOrder.debate;
  return FactOrder.recentes;
}

class FactQuery {
  const FactQuery._();

  static bool _verdictOk(FactClaim claim, FactFilter filter) {
    if (filter.onlyCorrected) return claim.corrigido != null;
    if (filter.verdict == null) return true;
    return claim.veredito == filter.verdict;
  }

  static bool _windowOk(FactClaim claim, FactFilter filter) {
    if (!filter.hasWindow) return true;
    return claim.t >= filter.windowStartMs! && claim.t < filter.windowEndMs!;
  }

  /// [ignore] replica o site: `'quem'` não filtra candidato, `'vered'` não filtra veredito.
  static List<FactClaim> apply(
    List<FactClaim> items,
    FactFilter filter, {
    String? ignore,
  }) {
    return [
      for (final claim in items)
        if ((ignore == 'quem' ||
                filter.quem == null ||
                claim.quem == filter.quem) &&
            (ignore == 'vered' || _verdictOk(claim, filter)) &&
            _windowOk(claim, filter))
          claim,
    ];
  }

  static List<FactClaim> sorted(List<FactClaim> items, FactOrder order) {
    final copy = [...items];
    copy.sort(
      (a, b) =>
          order == FactOrder.recentes ? b.t.compareTo(a.t) : a.t.compareTo(b.t),
    );
    return copy;
  }

  static List<FactClaim> highlights(List<FactClaim> items) {
    final changed = items
        .where(
          (claim) =>
              claim.corrigido != null &&
              claim.corrigido!.antes != claim.veredito,
        )
        .toList();
    final source = changed.isNotEmpty
        ? changed
        : items
            .where(
              (claim) =>
                  claim.veredito == Verdict.falso ||
                  claim.veredito == Verdict.impreciso,
            )
            .toList();
    source.sort((a, b) => b.t.compareTo(a.t));
    if (source.length > 8) return source.sublist(0, 8);
    return source;
  }

  static bool highlightsAreRevisions(List<FactClaim> items) {
    return items.any(
      (claim) =>
          claim.corrigido != null && claim.corrigido!.antes != claim.veredito,
    );
  }
}
