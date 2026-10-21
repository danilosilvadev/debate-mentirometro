import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

Future<void> openExternal(String url) async {
  final uri = Uri.tryParse(url);
  if (uri == null || !(uri.isScheme('https') || uri.isScheme('http'))) return;
  try {
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    // O aparelho pode não ter um app para o endereço.
  }
}

Future<void> copyText(BuildContext context, String text,
    {String ok = 'Texto copiado'}) async {
  await Clipboard.setData(ClipboardData(text: text));
  if (!context.mounted) return;
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
}

String whatsAppUrl(String text) =>
    'https://wa.me/?text=${Uri.encodeComponent(text)}';

String xUrl(String text) =>
    'https://x.com/intent/post?text=${Uri.encodeComponent(text)}';
