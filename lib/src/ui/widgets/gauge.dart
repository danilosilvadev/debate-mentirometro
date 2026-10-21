import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../theme/placar_theme.dart';

/// Arco do Mentirômetro: vermelho nas pontas, cinza no meio, ponteiro no centro.
///
/// O ângulo segue o site. 0 aponta para cima. Positivo gira no sentido horário,
/// para o candidato da direita.
class MentiromentroGauge extends StatelessWidget {
  const MentiromentroGauge({
    required this.angleDegrees,
    required this.leftName,
    required this.rightName,
    required this.semanticsLabel,
    super.key,
  });

  final double angleDegrees;
  final String leftName;
  final String rightName;
  final String semanticsLabel;

  @override
  Widget build(BuildContext context) {
    final reduce = MediaQuery.disableAnimationsOf(context);
    return Semantics(
      label: semanticsLabel,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = math.min(constraints.maxWidth, 320.0);
          final height = width * 170 / 300;
          return Center(
            child: SizedBox(
              width: width,
              height: height,
              child: TweenAnimationBuilder<double>(
                tween: Tween(begin: 0, end: angleDegrees),
                duration:
                    reduce ? Duration.zero : const Duration(milliseconds: 1000),
                curve: const Cubic(0.3, 1.5, 0.5, 1),
                builder: (context, angle, _) {
                  return Stack(
                    children: [
                      CustomPaint(
                        size: Size(width, height),
                        painter: _GaugePainter(angleDegrees: angle),
                      ),
                      Positioned(
                        left: width * 0.04,
                        bottom: 0,
                        width: width * 0.34,
                        child: Text(
                          leftName,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: PlacarType.strong(12.5),
                        ),
                      ),
                      Positioned(
                        right: width * 0.04,
                        bottom: 0,
                        width: width * 0.38,
                        child: Text(
                          rightName,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.right,
                          style: PlacarType.strong(12.5),
                        ),
                      ),
                    ],
                  );
                },
              ),
            ),
          );
        },
      ),
    );
  }
}

class _GaugePainter extends CustomPainter {
  _GaugePainter({required this.angleDegrees});

  final double angleDegrees;

  @override
  void paint(Canvas canvas, Size size) {
    final sx = size.width / 300;
    final sy = size.height / 170;
    canvas.save();
    canvas.scale(sx, sy);

    final rect = Rect.fromCircle(center: const Offset(150, 150), radius: 120);
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 22
      ..strokeCap = StrokeCap.butt;

    canvas.drawArc(
        rect, math.pi, math.pi / 3, false, stroke..color = PlacarColors.falso);
    canvas.drawArc(
      rect,
      math.pi + math.pi / 3,
      math.pi / 3,
      false,
      stroke..color = PlacarColors.borda,
    );
    canvas.drawArc(
      rect,
      math.pi + 2 * math.pi / 3,
      math.pi / 3,
      false,
      stroke..color = PlacarColors.falso,
    );

    canvas.save();
    canvas.translate(150, 150);
    canvas.rotate(angleDegrees * math.pi / 180);
    final needle = Path()
      ..moveTo(0, -102)
      ..lineTo(4.2, -2)
      ..lineTo(-4.2, -2)
      ..close();
    canvas.drawPath(needle, Paint()..color = PlacarColors.tinta);
    canvas.restore();

    canvas.drawCircle(
      const Offset(150, 150),
      10,
      Paint()..color = PlacarColors.tinta,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_GaugePainter oldDelegate) =>
      oldDelegate.angleDegrees != angleDegrees;
}
