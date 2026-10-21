"""Transcrição pt-BR. faster-whisper quando o pacote está instalado."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TranscriptSegment:
    start_s: float
    end_s: float
    text: str


class FasterWhisperTranscriber:
    def __init__(
        self,
        *,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def transcribe(self, wav_path: Path) -> list[TranscriptSegment]:
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper não está instalado. "
                    "Use pip install 'placar-pipeline[whisper]' numa máquina com o modelo."
                ) from exc
            self._model = WhisperModel(
                self.model_name, device=self.device, compute_type=self.compute_type
            )
        segments, _info = self._model.transcribe(
            str(wav_path),
            language="pt",
            vad_filter=True,
            beam_size=1,
        )
        return [
            TranscriptSegment(start_s=item.start, end_s=item.end, text=item.text.strip())
            for item in segments
            if item.text.strip()
        ]
