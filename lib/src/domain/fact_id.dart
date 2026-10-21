/// Mesmo id estável do site: base36(t) + quem + hash da afirmação.
///
/// O hash é o do placar web (`(s * 31 + code) >>> 0`, semente 7), para que
/// um fato do JSON público abra o mesmo `#fato-…` no site.
String factId({
  required int t,
  required String quem,
  required String afirmacao,
}) {
  var hash = 7;
  for (final codePoint in afirmacao.runes) {
    hash = (hash * 31 + codePoint) & 0xFFFFFFFF;
  }
  return '${t.toRadixString(36)}$quem${hash.toRadixString(36)}';
}
