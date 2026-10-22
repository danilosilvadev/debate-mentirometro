from placar.replay_data import build


def test_build_places_items_at_quote_time_and_keeps_lines():
    snap = {"video": {"id": "v", "t0": 1000}, "candidatos": {},
            "fatos": [{"tema": "x", "declaracoes": [{"t": 1000 + 420_000, "quem": "2", "literal": "O PT já governa esse país há 20 anos",
                                                    "afirmacao": "PT 20/24", "veredito": "falso"}]}],
            "propostas": [{"t": 1000, "quem": "1", "titulo": "Sem match", "explicacao": "zzz qqq"}],
            "ataques": [{"t": 1000 + 420_000, "quem": "2", "resumo": "Ataque: “a sua vida melhorou”"}]}
    tr = [{"t_s": 760.0, "dur_s": 3.0, "slot": "other", "text": "Candidato Flávio, dois minutos."},
          {"t_s": 763.7, "dur_s": 4.0, "slot": "2", "text": "O PT já governa esse país..."},
          {"t_s": 767.7, "dur_s": 3.0, "slot": "2", "text": "há 20 anos dos últimos 24. A sua vida melhorou?"}]
    out = build(snap, tr, offset_s=340)
    claim = out["fatos"][0]["declaracoes"][0]
    assert claim["vs"] == 770.7  # a citação atravessa 2 linhas: fim da segunda
    assert out["propostas"][0]["vs"] == 340.0  # sem citação achada: início do turno
    assert out["ataques"][0]["vs"] == 770.7
    assert out["replay"] == {"video": "v", "inicio": 340, "fim": 770.7}
    assert len(out["linhas"]) == 3 and out["linhas"][1]["quem"] == "2"
