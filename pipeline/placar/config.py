"""Configuração por ambiente. Segredos só vêm do ambiente, nunca do código."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return float(raw)


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    claude_bin: str = "claude"
    claude_model: str = "haiku"
    claude_timeout_s: float = 12.0
    session_chunks: int = 8
    openrouter_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3.5-super-vl:free"
    openrouter_timeout_s: float = 20.0
    providers: tuple[str, ...] = ("claude_cli", "groq", "openrouter")
    groq_llm_model: str = "openai/gpt-oss-120b"
    groq_verify_model: str = "qwen/qwen3.8-27b"
    groq_fast_model: str = "openai/gpt-oss-20b"
    groq_llm_timeout_s: float = 10.0
    # Quem confirma falso/impreciso, em ordem; o provedor que julgou nunca confirma a si mesmo.
    verify_providers: tuple[str, ...] = ("groq_verify", "openrouter", "claude_cli", "groq")
    retries: int = 1
    breaker_threshold: int = 3
    breaker_cooldown_s: float = 60.0
    anthropic_key: str = ""
    anthropic_model: str = "claude-haiku-4-5"
    gemini_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    factcheck_key: str = ""
    searxng_url: str = ""
    brave_key: str = ""
    # Desligado no Settings() puro (testes, replay de roteiro); from_env liga por padrão.
    ddg_enabled: bool = False
    chunk_seconds: float = 10.0
    chunk_overlap_seconds: float = 2.0
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute: str = "int8"
    stt_provider: str = "local"
    groq_key: str = ""
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_timeout_s: float = 8.0
    host: str = "127.0.0.1"
    port: int = 8787
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "placar"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "placar"

    @classmethod
    def from_env(cls) -> Settings:
        raw = os.environ.get("LLM_PROVIDERS", "claude_cli,groq,openrouter")
        vraw = os.environ.get("VERIFY_PROVIDERS", "groq_verify,openrouter,claude_cli,groq")
        providers = tuple(part.strip() for part in raw.split(",") if part.strip())
        return cls(
            claude_bin=os.environ.get("CLAUDE_BIN", "claude").strip() or "claude",
            claude_model=os.environ.get("CLAUDE_MODEL", "haiku").strip() or "haiku",
            claude_timeout_s=_float("CLAUDE_TIMEOUT_S", 12.0),
            session_chunks=_int("CLAUDE_SESSION_CHUNKS", 8),
            openrouter_key=os.environ.get("OPENROUTER_API_KEY", "").strip(),
            openrouter_model=os.environ.get(
                "OPENROUTER_MODEL", "nvidia/nemotron-3.5-super-vl:free"
            ).strip(),
            openrouter_timeout_s=_float("OPENROUTER_TIMEOUT_S", 20.0),
            providers=providers,
            verify_providers=tuple(p.strip() for p in vraw.split(",") if p.strip()),
            groq_llm_model=os.environ.get("GROQ_LLM_MODEL", "openai/gpt-oss-120b").strip()
            or "openai/gpt-oss-120b",
            groq_verify_model=os.environ.get("GROQ_VERIFY_MODEL", "qwen/qwen3.8-27b").strip()
            or "qwen/qwen3.8-27b",
            groq_fast_model=os.environ.get("GROQ_FAST_MODEL", "openai/gpt-oss-20b").strip(),
            groq_llm_timeout_s=_float("GROQ_LLM_TIMEOUT_S", 10.0),
            retries=_int("LLM_RETRIES", 1),
            breaker_threshold=_int("LLM_BREAKER_THRESHOLD", 3),
            breaker_cooldown_s=_float("LLM_BREAKER_COOLDOWN_S", 60.0),
            anthropic_key=os.environ.get("ANTHROPIC_API_KEY", "").strip(),
            anthropic_model=os.environ.get(
                "ANTHROPIC_MODEL", "claude-haiku-4-5"
            ).strip(),
            gemini_key=os.environ.get("GEMINI_API_KEY", "").strip(),
            gemini_model=os.environ.get(
                "GEMINI_MODEL", "gemini-2.5-flash-lite"
            ).strip(),
            factcheck_key=os.environ.get("FACTCHECK_API_KEY", "").strip(),
            searxng_url=os.environ.get("SEARXNG_URL", "").strip().rstrip("/"),
            brave_key=os.environ.get("BRAVE_API_KEY", "").strip(),
            ddg_enabled=os.environ.get("RETRIEVE_DDG", "1").strip() != "0",
            chunk_seconds=_float("CHUNK_SECONDS", 10.0),
            chunk_overlap_seconds=_float("CHUNK_OVERLAP_SECONDS", 2.0),
            whisper_model=os.environ.get("WHISPER_MODEL", "small").strip() or "small",
            whisper_device=os.environ.get("WHISPER_DEVICE", "cpu").strip() or "cpu",
            whisper_compute=os.environ.get("WHISPER_COMPUTE", "int8").strip() or "int8",
            stt_provider=(os.environ.get("STT_PROVIDER", "local").strip().lower() or "local"),
            groq_key=os.environ.get("GROQ_API_KEY", "").strip(),
            groq_stt_model=os.environ.get("GROQ_STT_MODEL", "whisper-large-v3-turbo").strip()
            or "whisper-large-v3-turbo",
            groq_timeout_s=_float("GROQ_TIMEOUT_S", 8.0),
            host=os.environ.get("PLACAR_HOST", "127.0.0.1").strip() or "127.0.0.1",
            port=_int("PLACAR_PORT", 8787),
            supabase_url=os.environ.get("SUPABASE_URL", "").strip().rstrip("/"),
            supabase_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
            supabase_bucket=os.environ.get("SUPABASE_BUCKET", "placar").strip()
            or "placar",
            r2_account_id=os.environ.get("R2_ACCOUNT_ID", "").strip(),
            r2_access_key_id=os.environ.get("R2_ACCESS_KEY_ID", "").strip(),
            r2_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY", "").strip(),
            r2_bucket=os.environ.get("R2_BUCKET", "placar").strip() or "placar",
        )
