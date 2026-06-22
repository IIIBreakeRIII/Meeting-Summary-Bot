from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .audio import normalize_audio, probe_duration_seconds
from .chunking import format_timestamp
from .schemas import TranscriptDocument, TranscriptSegment


_PROGRESS_RE = re.compile(r"progress\s*=\s*(\d+)%")


class TranscriptionBackend(Protocol):
    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None,
        model_name: str,
        use_vad: bool,
        no_gpu: bool,
        beam_size: int,
        best_of: int,
        suppress_nst: bool,
        progress: Callable[[str], None] | None = None,
    ) -> Any: ...


@dataclass
class WhisperCppBackend:
    cli_name: str = "whisper-cli"

    def _resolve_cli(self) -> str:
        candidates = [
            os.getenv("WHISPER_CLI"),
            shutil.which(self.cli_name),
            str(Path.cwd() / "build" / "bin" / "whisper-cli"),
            str(Path.cwd() / "whisper.cpp" / "build" / "bin" / "whisper-cli"),
        ]
        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return candidate
        raise RuntimeError(
            "whisper.cpp CLI를 찾을 수 없습니다. `whisper-cli`를 PATH에 두거나 "
            "`WHISPER_CLI`에 실행 파일 경로를 지정하세요."
        )

    def _ensure_model_available(self, model_name: str) -> None:
        model_path = Path(model_name)
        if model_path.exists():
            return
        raise RuntimeError(
            "whisper.cpp 모델 파일을 찾을 수 없습니다.\n"
            f"설정된 WHISPER_MODEL: {model_name}\n"
            "로컬에 해당 파일을 내려받아 두거나 .env에서 WHISPER_MODEL 경로를 수정하세요."
        )

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None,
        model_name: str,
        use_vad: bool,
        no_gpu: bool,
        beam_size: int,
        best_of: int,
        suppress_nst: bool,
        progress: Callable[[str], None] | None = None,
    ) -> Any:
        cli_path = self._resolve_cli()
        self._ensure_model_available(model_name)
        with tempfile.TemporaryDirectory(prefix="whispercpp-", dir=str(audio_path.parent)) as tmpdir:
            output_prefix = Path(tmpdir) / audio_path.stem
            command = [
                cli_path,
                "-m",
                model_name,
                "-f",
                str(audio_path),
                "-ojf",
                "-of",
                str(output_prefix),
                "-np",
                "-l",
                language or "ko",
                "-bs",
                str(beam_size),
                "-bo",
                str(best_of),
                "-pp",
            ]
            if use_vad:
                command.append("--vad")
            if no_gpu:
                command.append("-ng")
            if suppress_nst:
                command.append("-sns")
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            last_percent: int | None = None
            assert process.stdout is not None
            for line in process.stdout:
                line = line.rstrip()
                if progress is not None:
                    match = _PROGRESS_RE.search(line)
                    if match:
                        percent = int(match.group(1))
                        if percent != last_percent:
                            progress(f"전사 진행률 {percent}%")
                            last_percent = percent
            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(
                    "whisper.cpp 전사에 실패했습니다.\n"
                    f"명령: {' '.join(command)}\n"
                    f"종료 코드: {return_code}"
                )

            json_path = output_prefix.with_name(f"{output_prefix.name}.json")
            if not json_path.exists():
                raise RuntimeError(
                    f"whisper.cpp JSON 결과 파일을 찾을 수 없습니다: {json_path}"
                )
            return json.loads(json_path.read_text(encoding="utf-8"))


def _parse_whisper_json(raw_result: Any) -> tuple[str | None, list[dict[str, Any]]]:
    if not isinstance(raw_result, dict):
        return None, []
    result = raw_result.get("result", {})
    language = result.get("language") if isinstance(result, dict) else None
    transcription = raw_result.get("transcription", [])
    if not isinstance(transcription, list):
        transcription = []
    return language, transcription


def _segment_time_from_raw_segment(raw_segment: dict[str, Any]) -> tuple[float, float]:
    offsets = raw_segment.get("offsets", {})
    if isinstance(offsets, dict):
        start_offset = offsets.get("from")
        end_offset = offsets.get("to")
        if isinstance(start_offset, (int, float)) and isinstance(end_offset, (int, float)):
            return float(start_offset) / 1000.0, float(end_offset) / 1000.0

    timestamps = raw_segment.get("timestamps", {})
    if isinstance(timestamps, dict):
        start = _parse_timestamp_to_seconds(timestamps.get("from"))
        end = _parse_timestamp_to_seconds(timestamps.get("to"))
        return start, end

    return 0.0, 0.0


def build_transcript_document(
    *,
    audio_file: str,
    language: str,
    duration_seconds: float,
    raw_result: Any,
) -> TranscriptDocument:
    detected_language, raw_segments = _parse_whisper_json(raw_result)
    segments: list[TranscriptSegment] = []
    for index, raw_segment in enumerate(raw_segments):
        text = str(raw_segment.get("text", "")).strip() if isinstance(raw_segment, dict) else ""
        start = 0.0
        end = 0.0
        if isinstance(raw_segment, dict):
            start, end = _segment_time_from_raw_segment(raw_segment)
        if not text:
            continue
        segments.append(
            TranscriptSegment(id=index, start=start, end=end, speaker=None, text=text)
        )

    return TranscriptDocument(
        audio_file=audio_file,
        language=detected_language or language,
        duration_seconds=duration_seconds,
        segments=segments,
    )


def _parse_timestamp_to_seconds(value: Any) -> float:
    if isinstance(value, str):
        normalized = value.replace(",", ".")
        parts = normalized.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            try:
                return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
            except ValueError:
                return 0.0
    return 0.0


def transcribe_audio_file(
    source_path: Path,
    *,
    output_dir: Path,
    language: str | None,
    model_name: str,
    use_vad: bool = True,
    no_gpu: bool = True,
    beam_size: int = 5,
    best_of: int = 5,
    suppress_nst: bool = True,
    progress: Callable[[str], None] | None = None,
    backend: TranscriptionBackend | None = None,
) -> tuple[Path, TranscriptDocument]:
    backend = backend or WhisperCppBackend()
    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = output_dir / "audio.normalized.wav"
    if progress:
        progress("오디오 정규화 중")
    normalize_audio(source_path, normalized_path)
    if progress:
        progress("로컬 전사 중")
    raw_result = backend.transcribe(
        normalized_path,
        language=language,
        model_name=model_name,
        use_vad=use_vad,
        no_gpu=no_gpu,
        beam_size=beam_size,
        best_of=best_of,
        suppress_nst=suppress_nst,
        progress=progress,
    )
    if progress:
        progress("전사 결과 정리 중")
    duration_seconds = probe_duration_seconds(normalized_path)
    transcript = build_transcript_document(
        audio_file=source_path.name,
        language=language or "unknown",
        duration_seconds=duration_seconds,
        raw_result=raw_result,
    )
    return normalized_path, transcript


def transcript_to_markdown_lines(doc: TranscriptDocument) -> list[str]:
    lines = []
    for segment in doc.segments:
        lines.append(
            f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}] {segment.text}"
        )
    return lines
