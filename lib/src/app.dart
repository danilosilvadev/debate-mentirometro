import 'package:flutter/material.dart';

import 'theme/placar_theme.dart';
import 'ui/home_page.dart';

class PlacarApp extends StatelessWidget {
  const PlacarApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Placar da Verdade',
      debugShowCheckedModeBanner: false,
      theme: placarTheme(),
      builder: (context, child) {
        return DefaultTextStyle(
          style: PlacarType.body(),
          child: child ?? const SizedBox.shrink(),
        );
      },
      home: const HomePage(),
    );
  }
}
