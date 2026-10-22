from placar.transcripts_db import TranscriptDB


def test_put_is_idempotent_and_reads_back(tmp_path):
    db = TranscriptDB(tmp_path / "t.sqlite")
    rows = [{"t_start": 10.0, "t_end": 12.0, "rel_start": 0.0, "rel_end": 2.0, "text": "a", "owned": 1,
             "speaker": "lula", "slot": "1", "confidence": 0.7, "scores": {"lula": 0.7}},
            {"t_start": 12.0, "t_end": 13.0, "rel_start": 2.0, "rel_end": 3.0, "text": "b", "owned": 0}]
    db.put_chunk("d", 1, start_s=10, len_s=10, rows=rows, number_text="270 bilhões")
    db.put_chunk("d", 1, start_s=10, len_s=10, rows=rows)
    assert db.has("d", 1) and not db.has("d", 2)
    assert db.stats("d") == {"chunks": 1, "utterances": 2}
    assert [u["text"] for u in db.utterances("d")] == ["a"]
