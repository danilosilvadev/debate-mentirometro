import 'dart:async';

import 'package:flutter/material.dart';

import '../../domain/verdict.dart';
import '../../theme/placar_theme.dart';

class PulseDot extends StatefulWidget {
  const PulseDot(
      {required this.on, this.color = PlacarColors.falso, super.key});

  final bool on;
  final Color color;

  @override
  State<PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<PulseDot> {
  Timer? _timer;
  var _dim = false;

  @override
  void initState() {
    super.initState();
    _sync();
  }

  @override
  void didUpdateWidget(PulseDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.on != widget.on) _sync();
  }

  void _sync() {
    _timer?.cancel();
    if (!widget.on) {
      _dim = false;
      return;
    }
    _timer = Timer.periodic(const Duration(milliseconds: 800), (_) {
      if (mounted) setState(() => _dim = !_dim);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.disableAnimationsOf(context);
    final opacity = !widget.on || reduce || !_dim ? 1.0 : 0.25;
    return AnimatedOpacity(
      duration: const Duration(milliseconds: 400),
      opacity: opacity,
      child: Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: widget.on ? widget.color : PlacarColors.borda,
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

class EverySecond extends StatefulWidget {
  const EverySecond({required this.builder, super.key});

  final Widget Function(BuildContext context, DateTime now) builder;

  @override
  State<EverySecond> createState() => _EverySecondState();
}

class _EverySecondState extends State<EverySecond> {
  Timer? _timer;
  DateTime _now = DateTime.now();

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => widget.builder(context, _now);
}

class VerdictBadge extends StatelessWidget {
  const VerdictBadge({required this.verdict, this.compact = false, super.key});

  final Verdict verdict;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final background = switch (verdict) {
      Verdict.verdadeiro => PlacarColors.verdadeiro,
      Verdict.impreciso => PlacarColors.impreciso,
      Verdict.falso => PlacarColors.falso,
      Verdict.semDados => Colors.white,
      Verdict.emRevisao => PlacarColors.fundo,
    };
    final foreground = switch (verdict) {
      Verdict.semDados || Verdict.emRevisao => PlacarColors.tinta,
      _ => Colors.white,
    };
    final label = Text(
      verdict.label,
      style: PlacarType.heading(compact ? 12 : 13.5).copyWith(
        color: foreground,
        height: 1.1,
      ),
    );
    final child = Padding(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 10,
        vertical: compact ? 4 : 6,
      ),
      child: label,
    );
    if (verdict == Verdict.emRevisao) {
      return DashedBorder(
        color: PlacarColors.apagado,
        radius: 6,
        child: child,
      );
    }
    return Container(
      constraints: BoxConstraints(minWidth: compact ? 0 : 108),
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(6),
        border: verdict == Verdict.semDados
            ? Border.all(color: PlacarColors.borda)
            : null,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.18),
            offset: const Offset(0, 1),
          ),
        ],
      ),
      foregroundDecoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        border: Border(
          bottom: BorderSide(
            color: Colors.black.withValues(alpha: 0.28),
            width: 3,
          ),
        ),
      ),
      child: child,
    );
  }
}

class DashedBorder extends StatelessWidget {
  const DashedBorder({
    required this.child,
    required this.color,
    this.radius = 6,
    super.key,
  });

  final Widget child;
  final Color color;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _DashPainter(color: color, radius: radius),
      child: child,
    );
  }
}

class _DashPainter extends CustomPainter {
  _DashPainter({required this.color, required this.radius});

  final Color color;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2;
    final path = Path()
      ..addRRect(
        RRect.fromRectAndRadius(
          Offset.zero & size,
          Radius.circular(radius),
        ),
      );
    const dash = 4.0;
    const gap = 3.0;
    for (final metric in path.computeMetrics()) {
      var distance = 0.0;
      while (distance < metric.length) {
        final next = (distance + dash).clamp(0, metric.length).toDouble();
        canvas.drawPath(metric.extractPath(distance, next), paint);
        distance = next + gap;
      }
    }
  }

  @override
  bool shouldRepaint(_DashPainter oldDelegate) =>
      oldDelegate.color != color || oldDelegate.radius != radius;
}

class FilterPill extends StatelessWidget {
  const FilterPill({
    required this.label,
    required this.selected,
    required this.onTap,
    this.count,
    this.dot,
    this.dashedDot = false,
    super.key,
  });

  final String label;
  final String? count;
  final bool selected;
  final VoidCallback onTap;
  final Color? dot;
  final bool dashedDot;

  @override
  Widget build(BuildContext context) {
    final foreground = selected ? Colors.white : PlacarColors.tinta;
    final muted = selected ? const Color(0xFFDDDDDD) : PlacarColors.apagado;
    return Material(
      color: selected ? PlacarColors.tinta : PlacarColors.tela,
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(999),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected ? PlacarColors.tinta : PlacarColors.borda,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (dot != null || dashedDot) ...[
                _Dot(color: dot, dashed: dashedDot),
                const SizedBox(width: 6),
              ],
              Text(label,
                  style: PlacarType.strong(13.5).copyWith(color: foreground)),
              if (count != null) ...[
                const SizedBox(width: 6),
                Text(count!,
                    style: PlacarType.muted(13).copyWith(color: muted)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.color, required this.dashed});

  final Color? color;
  final bool dashed;

  @override
  Widget build(BuildContext context) {
    if (dashed) {
      return const DashedBorder(
        color: PlacarColors.apagado,
        radius: 2,
        child: SizedBox(width: 10, height: 10),
      );
    }
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color ?? PlacarColors.borda,
        borderRadius: BorderRadius.circular(2),
        border: color == Colors.white
            ? Border.all(color: PlacarColors.borda)
            : null,
      ),
    );
  }
}

class SectionCard extends StatelessWidget {
  const SectionCard({required this.child, this.padding, super.key});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 16),
      padding: padding ?? const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
      ),
      child: child,
    );
  }
}

class PlacarCard extends StatelessWidget {
  const PlacarCard({required this.child, super.key});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: PlacarColors.tela,
        borderRadius: BorderRadius.circular(10),
      ),
      child: child,
    );
  }
}
