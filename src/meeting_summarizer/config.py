from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    openai_summary_model: str
    whisper_model: str
    chunk_target_chars: int
    whisper_use_vad: bool
    whisper_no_gpu: bool
    whisper_beam_size: int
    whisper_best_of: int
    whisper_suppress_nst: bool


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_summary_model=os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5.4-mini"),
        whisper_model=os.getenv("WHISPER_MODEL", "models/ggml-large-v3-turbo.bin"),
        chunk_target_chars=int(os.getenv("CHUNK_TARGET_CHARS", "24000")),
        whisper_use_vad=os.getenv("WHISPER_USE_VAD", "false").lower() in {"1", "true", "yes", "on"},
        whisper_no_gpu=os.getenv("WHISPER_NO_GPU", "true").lower() in {"1", "true", "yes", "on"},
        whisper_beam_size=int(os.getenv("WHISPER_BEAM_SIZE", "5")),
        whisper_best_of=int(os.getenv("WHISPER_BEST_OF", "5")),
        whisper_suppress_nst=os.getenv("WHISPER_SUPPRESS_NST", "true").lower() in {"1", "true", "yes", "on"},
    )


def ensure_openai_key(settings: Settings) -> str:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가하세요."
        )
    return settings.openai_api_key


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def outputs_root() -> Path:
    return project_root() / "outputs"
