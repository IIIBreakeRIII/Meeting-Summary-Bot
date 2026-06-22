from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    pass


SUPPORTED_AUDIO_SUFFIXES = {
    ".m4a",
    ".mp3",
    ".wav",
    ".aiff",
    ".aif",
    ".mp4",
    ".aac",
    ".flac",
    ".ogg",
    ".webm",
    ".m4b",
    ".mov",
}


class UnsupportedAudioFormatError(RuntimeError):
    pass


def ensure_supported_audio_file(source_path: Path) -> None:
    if source_path.suffix.lower() not in SUPPORTED_AUDIO_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_AUDIO_SUFFIXES))
        raise UnsupportedAudioFormatError(
            f"지원하지 않는 오디오 형식입니다: {source_path.suffix or '(없음)'}."
            f" 지원 형식: {supported}"
        )


def ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegNotFoundError(
            "ffmpeg를 찾을 수 없습니다. macOS에서는 `brew install ffmpeg`로 설치하세요."
        )


def normalize_audio(source_path: Path, destination_path: Path) -> None:
    ensure_ffmpeg_available()
    ensure_supported_audio_file(source_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-vn",
        "-c:a",
        "pcm_s16le",
        str(destination_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "오디오 정규화에 실패했습니다.\n"
            f"명령: {' '.join(command)}\n"
            f"stderr: {result.stderr.strip()}"
        )


def probe_duration_seconds(audio_path: Path) -> float:
    if shutil.which("ffprobe") is None:
        return 0.0
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0
