/// Veredito de uma afirmação checável.
///
/// O placar publicado usa estes cinco rótulos. Só [verdadeiro], [impreciso]
/// e [falso] entram no Mentirômetro. [semDados] e [emRevisao] ficam de fora.
enum Verdict {
  verdadeiro,
  impreciso,
  falso,
  semDados,
  emRevisao;

  static Verdict parse(Object? raw) {
    switch (raw) {
      case 'verdadeiro':
        return Verdict.verdadeiro;
      case 'impreciso':
        return Verdict.impreciso;
      case 'falso':
        return Verdict.falso;
      case 'sem_dados':
        return Verdict.semDados;
      case 'em_revisao':
        return Verdict.emRevisao;
      default:
        return Verdict.semDados;
    }
  }

  String get wire {
    switch (this) {
      case Verdict.verdadeiro:
        return 'verdadeiro';
      case Verdict.impreciso:
        return 'impreciso';
      case Verdict.falso:
        return 'falso';
      case Verdict.semDados:
        return 'sem_dados';
      case Verdict.emRevisao:
        return 'em_revisao';
    }
  }

  String get label {
    switch (this) {
      case Verdict.verdadeiro:
        return 'Verdadeiro';
      case Verdict.impreciso:
        return 'Impreciso';
      case Verdict.falso:
        return 'Falso';
      case Verdict.semDados:
        return 'Sem dados';
      case Verdict.emRevisao:
        return 'Em revisão';
    }
  }

  /// Entra na conta de erro do Mentirômetro.
  bool get countsOnScoreboard {
    switch (this) {
      case Verdict.verdadeiro:
      case Verdict.impreciso:
      case Verdict.falso:
        return true;
      case Verdict.semDados:
      case Verdict.emRevisao:
        return false;
    }
  }
}
