"""Pré-carrega o banco com checagens da Google Fact Check Tools API (pt) sobre Lula e Flávio.

Uso: GOOGLE_FACTCHECK_API_KEY=... python scripts/bank_from_factcheck.py [--since 2026-01-01] [--before 2026-10-18]
Grava placar/data/claim_bank_factcheck.json (revisar antes de juntar ao banco). Nunca imprime a chave."""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from placar.claim_bank import numbers, _fold

TOPICS = ["Lula", "Flávio Bolsonaro", "Janja viagens", "dívida pública trilhões", "Banco Master Vorcaro", "Dark Horse filme",
          "INSS fraude aposentados", "Careca do INSS", "Lulinha", "Bolsa Família valor", "Pix criado", "salário mínimo",
          "inflação alimentos", "desemprego recorde", "PIB crescimento", "Mais Médicos", "facções crime organizado",
          "armas de fogo crimes", "feminicídio recorde", "presídios votos Lula", "saidinha presos", "Mensalão",
          "escala 6x1", "tarifaço Estados Unidos", "Petrobras privatizar", "reservas internacionais", "FMI dívida",
          "MEI microempreendedor", "terras indígenas demarcação", "licença-maternidade Flávio", "rachadinha Flávio",
          "mansão Flávio Brasília", "Eduardo Bolsonaro", "Jair Bolsonaro preso", "Bolsonaro vacina", "STF Lula condenado",
          "empresas Paraguai", "falências recorde", "gasolina preço", "Imposto de Renda isenção 5 mil", "Pé-de-Meia",
          "Desenrola", "Farmácia Popular", "Minha Casa Minha Vida", "Bolsonaro salário mínimo aumento real",
          "margem equatorial petróleo", "Polícia Federal troca comando", "Dino", "urnas eletrônicas fraude 2026"]

MAP = [(r"\b(verdadeir|fato\b|correto|true)", "verdadeiro"),
       (r"(exagerad|impreciso|nao e bem assim|distorc|enganos|falta contexto|subestimad|insustentavel|contradit|discutivel|parcial)", "impreciso"),
       (r"\b(falso|fake|false|mentir)", "falso")]


def verdict(rating: str):
    f = _fold(rating)
    for rx, v in MAP:
        if re.search(rx, f):
            return v
    return None


def search(q, key, page=None):
    qs = {"query": q, "languageCode": "pt", "pageSize": 50, "key": key}
    if page:
        qs["pageToken"] = page
    url = "https://factchecktools.googleapis.com/v1alpha1/claims:search?" + urllib.parse.urlencode(qs)
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", default="2026-01-01")
    ap.add_argument("--before", default="")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "placar/data/claim_bank_factcheck.json"))
    a = ap.parse_args()
    key = os.environ.get("GOOGLE_FACTCHECK_API_KEY") or os.environ.get("FACTCHECK_API_KEY")
    if not key:
        print("sem GOOGLE_FACTCHECK_API_KEY: nada a fazer"); return 0
    seen, items = set(), []
    for q in TOPICS:
        try:
            data = search(q, key)
        except Exception as e:  # noqa: BLE001
            print("erro", q, type(e).__name__); continue
        for c in data.get("claims") or []:
            text = (c.get("text") or "").strip()
            for rv in c.get("claimReview") or []:
                date = (rv.get("reviewDate") or c.get("claimDate") or "")[:10]
                if date < a.since or (a.before and date >= a.before):
                    continue
                v = verdict(rv.get("textualRating") or "")
                url = rv.get("url") or ""
                if not v or not url or url in seen or len(text.split()) < 4:
                    continue
                claimant = _fold(c.get("claimant") or "")
                quem = "lula" if "lula" in claimant else "flavio" if "flavio" in claimant else ""
                seen.add(url)
                items.append({"quem": quem, "frase": text[:200], "veredito": v,
                              "motivo": f"{rv.get('publisher', {}).get('name', '')}: {rv.get('textualRating', '')} — {rv.get('title', '')[:200]}",
                              "fonte": rv.get("publisher", {}).get("name", "") or "checador",
                              "url": url, "numeros": sorted(numbers(text))[:3], "data": date,
                              "claimant": c.get("claimant", ""), "origem": "factcheck-api", "min_overlap": 0.75})
        time.sleep(0.2)
    Path(a.out).write_text(json.dumps({"_sobre": "Importado da Google Fact Check Tools API; revisar.", "itens": items},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(items), "itens", Counter(i["veredito"] for i in items), Counter(i["quem"] or "-" for i in items),
          Counter(i["fonte"] for i in items).most_common(8))
    return 0


if __name__ == "__main__":
    sys.exit(main())
