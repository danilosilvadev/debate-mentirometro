import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/fact_query.dart';
import '../domain/models.dart';
import '../providers.dart';
import '../theme/placar_theme.dart';
import 'placar_format.dart';
import 'proposals_page.dart';
import 'widgets/chrome.dart';
import 'widgets/facts_section.dart';
import 'widgets/side_sections.dart';
import 'widgets/timeline_section.dart';
import 'widgets/tone_section.dart';
import 'widgets/top_panels.dart';

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncBoard = ref.watch(scoreboardProvider);
    return Scaffold(
      body: SafeArea(
        child: asyncBoard.when(
          loading: () => const _Loading(),
          error: (error, _) => _Failure(
            message: 'Sem conexão com o placar. Tentando de novo…',
            onRetry: () => ref.read(scoreboardRepositoryProvider).refresh(),
          ),
          data: (snapshot) {
            final board = snapshot.board;
            if (board == null) {
              if (snapshot.loading) return const _Loading();
              return _Failure(
                message: snapshot.error ??
                    'Sem conexão com o placar. Tentando de novo…',
                onRetry: () => ref.read(scoreboardRepositoryProvider).refresh(),
              );
            }
            return _Board(snapshot: snapshot);
          },
        ),
      ),
    );
  }
}

class _Loading extends StatelessWidget {
  const _Loading();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Placar da Verdade', style: PlacarType.title(36)),
          const SizedBox(height: 16),
          const Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              PulseDot(on: true),
              SizedBox(width: 8),
              Text('Conectando…'),
            ],
          ),
        ],
      ),
    );
  }
}

class _Failure extends ConsumerWidget {
  const _Failure({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 460),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Placar da Verdade',
                  style: PlacarType.title(32), textAlign: TextAlign.center),
              const SizedBox(height: 12),
              Text(message,
                  textAlign: TextAlign.center, style: PlacarType.body()),
              const SizedBox(height: 16),
              FilledButton(
                  onPressed: onRetry, child: const Text('Tentar agora')),
              TextButton(
                onPressed: () => selectFeedMode(ref, FeedMode.simulation),
                child: const Text('Usar simulação'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Board extends ConsumerStatefulWidget {
  const _Board({required this.snapshot});

  final ScoreboardSnapshot snapshot;

  @override
  ConsumerState<_Board> createState() => _BoardState();
}

class _BoardState extends ConsumerState<_Board> {
  final _scroll = ScrollController();
  final _factsKey = GlobalKey();
  Set<String> _seen = {};
  Set<String> _fresh = {};
  var _pending = 0;
  var _primed = false;
  Timer? _freshTimer;

  Scoreboard get board => widget.snapshot.board!;

  @override
  void initState() {
    super.initState();
    _seen = board.declaracoes.map((claim) => claim.id).toSet();
    _primed = true;
    _scroll.addListener(_onScroll);
  }

  @override
  void didUpdateWidget(_Board oldWidget) {
    super.didUpdateWidget(oldWidget);
    final previous =
        oldWidget.snapshot.board?.declaracoes.map((claim) => claim.id).toSet();
    final ids = board.declaracoes.map((claim) => claim.id).toSet();
    if (!_primed || previous == null) {
      _seen = ids;
      _primed = true;
      return;
    }
    final fresh = ids.difference(_seen);
    _seen = ids;
    if (fresh.isEmpty) return;
    _fresh = fresh;
    _freshTimer?.cancel();
    _freshTimer = Timer(const Duration(seconds: 2), () {
      if (mounted) setState(() => _fresh = {});
    });
    final order = effectiveOrder(board, ref.read(factFilterProvider).order);
    if (_factsOffscreen() &&
        order == FactOrder.recentes &&
        board.encerrado == null) {
      _pending += fresh.length;
    }
  }

  bool _factsOffscreen() {
    final context = _factsKey.currentContext;
    if (context == null) return false;
    final box = context.findRenderObject();
    if (box is! RenderBox || !box.hasSize) return false;
    final top = box.localToGlobal(Offset.zero).dy;
    return top < 0;
  }

  void _onScroll() {
    if (_pending > 0 && !_factsOffscreen() && mounted) {
      setState(() => _pending = 0);
    }
  }

  @override
  void dispose() {
    _freshTimer?.cancel();
    _scroll.removeListener(_onScroll);
    _scroll.dispose();
    super.dispose();
  }

  void _scrollToFacts() {
    final target = _factsKey.currentContext;
    if (target == null) return;
    Scrollable.ensureVisible(
      target,
      alignment: 0.02,
      duration: const Duration(milliseconds: 350),
    );
  }

  @override
  Widget build(BuildContext context) {
    final filter = ref.watch(factFilterProvider);
    final mode = ref.watch(feedModeProvider);
    final reading = leituraDe(board);
    final width = MediaQuery.sizeOf(context).width;

    return Stack(
      children: [
        Column(
          children: [
            _Header(board: board, mode: mode, titleSize: width < 460 ? 30 : 44),
            if (board.simulated)
              const _Banner(
                text:
                    'Simulação com fatos fictícios. Não é a checagem do debate. Toque em Ao vivo para o placar publicado.',
              )
            else if (widget.snapshot.error != null)
              _Banner(text: widget.snapshot.error!),
            Expanded(
              child: RefreshIndicator(
                color: PlacarColors.tinta,
                onRefresh: () =>
                    ref.read(scoreboardRepositoryProvider).refresh(),
                child: Scrollbar(
                  controller: _scroll,
                  child: SingleChildScrollView(
                    key: const Key('board-scroll'),
                    controller: _scroll,
                    physics: const AlwaysScrollableScrollPhysics(),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1180),
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(16, 8, 16, 48),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              TopPanels(board: board, reading: reading),
                              RevisionCard(board: board),
                              HighlightsStrip(board: board),
                              ToneSection(
                                board: board,
                                onOpenProposals: () {
                                  Navigator.of(context).push(
                                    MaterialPageRoute<void>(
                                      builder: (_) => const ProposalsPage(),
                                    ),
                                  );
                                },
                              ),
                              TimelineSection(
                                board: board,
                                filter: filter,
                                onSelect: (column) {
                                  final selected =
                                      filter.windowStartMs == column.startMs;
                                  ref.read(factFilterProvider.notifier).state =
                                      selected
                                          ? filter.copy(clearWindow: true)
                                          : filter.copy(
                                              windowStartMs: column.startMs,
                                              windowEndMs: column.endMs,
                                            );
                                  if (!selected) _scrollToFacts();
                                },
                              ),
                              const SizedBox(height: 16),
                              KeyedSubtree(
                                key: _factsKey,
                                child: FactsSection(
                                    board: board, freshIds: _fresh),
                              ),
                              InfoSection(board: board),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
        if (_pending > 0)
          Positioned(
            left: 0,
            right: 0,
            bottom: 16,
            child: Center(
              child: FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: PlacarColors.tinta,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
                  shape: const StadiumBorder(),
                ),
                onPressed: () {
                  setState(() => _pending = 0);
                  _scrollToFacts();
                },
                child: Text(
                  '↑ $_pending ${_pending == 1 ? 'fato novo' : 'fatos novos'}',
                  style: PlacarType.strong(14).copyWith(color: Colors.white),
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class _Header extends ConsumerWidget {
  const _Header({
    required this.board,
    required this.mode,
    required this.titleSize,
  });

  final Scoreboard board;
  final FeedMode mode;
  final double titleSize;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1180),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: EverySecond(
            builder: (context, now) {
              final status = statusCopy(board, now);
              final audience = board.audienciaAgora;
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text('Placar da Verdade',
                            style: PlacarType.title(titleSize)),
                      ),
                      const SizedBox(width: 12),
                      _ModeSwitch(mode: mode),
                    ],
                  ),
                  const SizedBox(height: 8),
                  StatusLine(status: status),
                  if (audience != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        '${formatPt(audience)} ${audience == 1 ? 'pessoa assistindo' : 'pessoas assistindo'} agora'
                        '${board.visitas == null ? '' : ' · ${formatPt(board.visitas!)} visitas'}',
                        style: PlacarType.muted(13),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _ModeSwitch extends ConsumerWidget {
  const _ModeSwitch({required this.mode});

  final FeedMode mode;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: PlacarColors.borda),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ModeChip(
            label: 'Simulação',
            selected: mode == FeedMode.simulation,
            onTap: () => selectFeedMode(ref, FeedMode.simulation),
          ),
          _ModeChip(
            label: 'Ao vivo',
            selected: mode == FeedMode.live,
            onTap: () => selectFeedMode(ref, FeedMode.live),
          ),
        ],
      ),
    );
  }
}

class _ModeChip extends StatelessWidget {
  const _ModeChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? PlacarColors.tinta : Colors.transparent,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          child: Text(
            label,
            style: PlacarType.strong(13).copyWith(
              color: selected ? Colors.white : PlacarColors.tinta,
            ),
          ),
        ),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: PlacarColors.aviso,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child:
          Text(text, textAlign: TextAlign.center, style: PlacarType.body(13.5)),
    );
  }
}
