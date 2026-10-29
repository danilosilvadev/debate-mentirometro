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
        # Lê o WAV 16 kHz já cortado pelo ffmpeg. Passar o caminho faz o
        # faster-whisper abrir com PyAV, que quebra em algumas versões do av.
        import soundfile as sf

        audio, _sr = sf.read(str(wav_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        segments, _info = self._model.transcribe(
            audio,
            language="pt",
            vad_filter=True,
            beam_size=1,
        )
        return [
            TranscriptSegment(start_s=item.start, end_s=item.end, text=item.text.strip())
            for item in segments
            if item.text.strip()
        ]


# --- Groq hosted Whisper (API compatível com OpenAI) -------------------------
# Conferido em 21/10/2026 em https://console.groq.com/docs/speech-to-text:
# POST https://api.groq.com/openai/v1/audio/transcriptions, modelo
# `whisper-large-v3-turbo` a US$ 0,04/hora de áudio (cobrança mínima de 10 s
# por pedido), arquivo até 25 MB no plano gratuito.

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class SttError(RuntimeError):
    pass


def _multipart(fields: dict[str, str], file_field: str, filename: str, payload: bytes) -> tuple[bytes, str]:
    import uuid

    boundary = "----placar" + uuid.uuid4().hex
    parts: list[bytes] = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{file_field}"; '
            f'filename="{filename}"\r\nContent-Type: audio/wav\r\n\r\n'
        ).encode()
        + payload
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def urllib_post(url: str, body: bytes, headers: dict[str, str], timeout_s: float) -> tuple[int, str]:
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    try:
        with urlopen(Request(url, data=body, headers=headers, method="POST"), timeout=timeout_s) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except (URLError, TimeoutError, OSError) as exc:
        raise SttError(f"Groq inacessível: {exc}") from exc


class GroqWhisperTranscriber:
    name = "groq"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "whisper-large-v3-turbo",
        timeout_s: float = 8.0,
        language: str = "pt",
        prompt: str = "",
        post=None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s
        self.language = language
        self.prompt = prompt
        self._post = post or urllib_post

    def transcribe(self, wav_path: Path) -> list[TranscriptSegment]:
        import json

        if not self.api_key:
            raise SttError("GROQ_API_KEY não está definida.")
        fields = {
            "model": self.model,
            "language": self.language,
            "response_format": "verbose_json",
            "temperature": "0",
        }
        if self.prompt:
            fields["prompt"] = self.prompt
        body, ctype = _multipart(fields, "file", Path(wav_path).name, Path(wav_path).read_bytes())
        status, text = self._post(
            GROQ_STT_URL,
            body,
            {"Authorization": f"Bearer {self.api_key}", "Content-Type": ctype,
             # Cloudflare da Groq barra o User-Agent padrão do urllib (erro 1010).
             "User-Agent": "placar-pipeline/0.1"},
            self.timeout_s,
        )
        if status != 200:
            raise SttError(f"Groq respondeu {status}: {text[:200]}")
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise SttError("Groq devolveu JSON inválido.") from exc
        segments = data.get("segments") or []
        if not segments and data.get("text"):
            segments = [{"start": 0.0, "end": float(data.get("duration") or 0), "text": data["text"]}]
        return [
            TranscriptSegment(start_s=float(s["start"]), end_s=float(s["end"]), text=str(s["text"]).strip())
            for s in segments
            if str(s.get("text", "")).strip()
        ]


class FallbackTranscriber:
    """Tenta o primário (Groq); em erro ou timeout cai no faster-whisper local."""

    def __init__(self, primary, fallback, *, log=None) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_provider = ""
        self.failures = 0
        self._log = log or (lambda msg: None)

    def transcribe(self, wav_path: Path) -> list[TranscriptSegment]:
        try:
            out = self.primary.transcribe(wav_path)
            self.last_provider = getattr(self.primary, "name", "primary")
            return out
        except Exception as exc:  # noqa: BLE001 - qualquer falha cai no local
            self.failures += 1
            self._log(f"stt primário falhou, usando local: {exc}")
            self.last_provider = "local"
            return self.fallback.transcribe(wav_path)


def build_transcriber(settings) -> object:
    local = FasterWhisperTranscriber(
        model_name=settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute,
    )
    if settings.stt_provider == "groq":
        return FallbackTranscriber(
            GroqWhisperTranscriber(
                api_key=settings.groq_key,
                model=settings.groq_stt_model,
                timeout_s=settings.groq_timeout_s,
            ),
            local,
        )
    return local


def dedupe_overlap(previous_tail: str, text: str, *, max_words: int = 12) -> str:
    """Tira do começo de `text` as palavras que repetem o fim de `previous_tail`.

    A janela de 2 s de sobreposição faz o Whisper transcrever as mesmas
    palavras nos dois blocos. Compara sem pontuação e sem caixa.
    """
    import re

    def norm(word: str) -> str:
        return re.sub(r"[^\wà-ú]", "", word.lower())

    prev = [norm(w) for w in previous_tail.split()][-max_words:]
    words = text.split()
    cur = [norm(w) for w in words]
    # k = palavras cortadas no começo do bloco (ex.: "correntes" de "concorrentes")
    for k in range(0, 3):
        for size in range(min(len(prev), len(cur) - k, max_words), 0 if k == 0 else 1, -1):
            if prev[-size:] == cur[k : k + size] and any(prev[-size:]):
                return " ".join(words[k + size :]).strip()
    return text
