import json
from pathlib import Path

import jsonschema

from placar.audio import chunk_windows, ffmpeg_chunk_args
from placar.config import Settings
from placar.mockllm import mock_router
from placar.replay import load_script, replay
from placar.retrieve import Retriever
from placar.schemas import EVENT_SCHEMA, PLACAR_SCHEMA
from placar.serve import response_for
from placar.speaker import cosine, match_speaker
from placar.upload import upload_r2, upload_supabase

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "sample_debate.json"
SAMPLE_OUT = ROOT / "fixtures" / "sample_placar.json"


def test_janelas_de_10s_com_2s_de_sobreposicao():
    windows = chunk_windows(30, chunk_s=10, overlap_s=2)
    assert windows[0] == (0.0, 10.0)
    assert windows[1] == (8.0, 10.0)
    assert windows[-1][0] == 24.0
    assert abs(windows[-1][1] - 6.0) < 0.01
    args = ffmpeg_chunk_args("ao-vivo", "c.wav", start_s=8, duration_s=10)
    assert args[0] == "ffmpeg"
    assert "-ac" in args and "1" in args
    assert "16000" in args


def test_amostra_de_voz_escolhe_o_candidato():
    enrolled = {"1": [1.0, 0.0, 0.0], "2": [0.0, 1.0, 0.0]}
    assert match_speaker([0.9, 0.1, 0.0], enrolled) == "1"
    assert match_speaker([0.1, 0.1, 1.0], enrolled) == "other"
    assert cosine([1, 0], [1, 0]) == 1


def test_replay_mock_escreve_placar_e_relatorio():
    script = load_script(FIXTURE)

    def http(url, timeout_s):
        if "350" in url or "gastos" in url or "bilh" in url:
            return 200, json.dumps(
                {
                    "claims": [
                        {
                            "text": "gasto ilustrativo",
                            "claimReview": [
                                {
                                    "title": "Checagem ilustrativa",
                                    "url": "https://exemplo.com/gastometro",
                                }
                            ],
                        }
                    ]
                }
            )
        return 200, json.dumps({"claims": []})

    router = mock_router()
    snapshot, events, report = replay(
        script,
        router,
        Retriever(Settings(factcheck_key="teste"), http=http),
        speed=0,
        clock_ms=lambda: 1700000016000,
    )
    jsonschema.validate(snapshot, PLACAR_SCHEMA)
    assert snapshot["candidatos"]["2"]["falso"] == 1
    assert snapshot["candidatos"]["2"]["ataques"] == 1
    assert snapshot["candidatos"]["1"]["propostas"] == 1
    # Inflação ficou em revisão: o segundo modelo discordou, então não entra no placar.
    assert snapshot["candidatos"]["1"]["impreciso"] == 0
    assert snapshot["candidatos"]["1"]["verdadeiro"] == 0
    verdicts = [
        item["veredito"]
        for group in snapshot["fatos"]
        for item in group["declaracoes"]
    ]
    assert "falso" in verdicts
    assert "em_revisao" in verdicts
    assert "impreciso" not in verdicts
    assert snapshot["linha"]["0"]["p1"] == 1
    assert snapshot["linha"]["0"]["a2"] == 1
    assert events[0]["v"] == 1
    jsonschema.validate(events[0], EVENT_SCHEMA)
    assert report.failover_pct > 0
    assert "mock-openrouter" in report.provider_counts
    assert report.stage_ms["classify"]["mean"] >= 0
    assert report.utterances == 5
    sleeps = []
    replay(
        script,
        mock_router(),
        Retriever(Settings()),
        speed=1,
        sleeper=sleeps.append,
        clock_ms=lambda: 1700000016000,
    )
    assert sleeps == [4.0, 4.0, 4.0, 4.0]
    SAMPLE_OUT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    site_sample = ROOT.parent / "site" / "sample"
    site_sample.mkdir(parents=True, exist_ok=True)
    (site_sample / "placar.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "fixtures" / "sample_report.json").write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def test_servidor_local_expoe_o_json_com_cors(tmp_path):
    (tmp_path / "placar.json").write_text("{}", encoding="utf-8")
    status, content_type, body = response_for(tmp_path, "/placar.json?t=3")
    assert status == 200
    assert "json" in content_type
    assert body == b"{}"


def test_upload_supabase_e_r2_montam_o_pedido():
    settings = Settings(
        supabase_url="https://abc.supabase.co",
        supabase_key="service-role",
        supabase_bucket="placar",
        r2_account_id="account",
        r2_access_key_id="AKIA",
        r2_secret_access_key="secret",
        r2_bucket="placar",
    )
    seen = []

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b""

    def opener(request, timeout=20):
        seen.append(request)
        return Resp()

    upload_supabase(settings, b"{}", opener=opener)
    assert "supabase.co/storage" in seen[0].full_url
    assert seen[0].headers["Authorization"] == "Bearer service-role"
    from datetime import datetime, timezone

    upload_r2(settings, b"{}", opener=opener, now=datetime(2026, 10, 21, tzinfo=timezone.utc))
    assert seen[1].headers["Authorization"].startswith("AWS4-HMAC-SHA256 ")
    assert "account.r2.cloudflarestorage.com" in seen[1].full_url
