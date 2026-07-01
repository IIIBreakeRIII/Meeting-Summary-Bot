from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Protocol

from .audio import normalize_audio, probe_duration_seconds
from .chunking import format_timestamp
from .schemas import TranscriptDocument, TranscriptSegment


_PROGRESS_RE = re.compile(r"progress\s*=\s*(\d+)%")
_STALL_TIMEOUT_SECONDS = 900
_POST_100_GRACE_SECONDS = 120
_OUTPUT_TAIL_LIMIT = 200


def _iter_decoded_lines(stream: Any) -> Iterator[str]:
    while True:
        raw_line = stream.readline()
        if not raw_line:
            break
        if isinstance(raw_line, bytes):
            line = raw_line.decode("utf-8", errors="replace")
        else:
            line = str(raw_line)
        yield line.rstrip("\r\n")


def _read_json_text(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


@dataclass
class _ProcessMonitor:
    last_percent: int | None = None
    saw_hundred: bool = False
    last_output_at: float = 0.0
    last_progress_at: float = 0.0
    output_tail: deque[str] = field(default_factory=lambda: deque(maxlen=_OUTPUT_TAIL_LIMIT))
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record_line(self, line: str) -> int | None:
        now = time.monotonic()
        with self.lock:
            self.last_output_at = now
            self.output_tail.append(line)
            match = _PROGRESS_RE.search(line)
            if not match:
                return None
            percent = int(match.group(1))
            if percent != self.last_percent:
                self.last_percent = percent
                self.last_progress_at = now
                if percent >= 100:
                    self.saw_hundred = True
                return percent
            return None

    def snapshot(self) -> tuple[int | None, bool, float, float, list[str]]:
        with self.lock:
            return (
                self.last_percent,
                self.saw_hundred,
                self.last_output_at,
                self.last_progress_at,
                list(self.output_tail),
            )


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
                text=False,
            )
            start_time = time.monotonic()
            monitor = _ProcessMonitor(last_output_at=start_time, last_progress_at=start_time)

            def _drain_output() -> None:
                assert process.stdout is not None
                for line in _iter_decoded_lines(process.stdout):
                    percent = monitor.record_line(line)
                    if progress is not None and percent is not None:
                        progress(f"전사 진행률 {percent}%")

            reader = threading.Thread(target=_drain_output, daemon=True)
            reader.start()

            saw_hundred_reported = False
            return_code: int | None = None
            while True:
                return_code = process.poll()
                if return_code is not None:
                    break

                last_percent, saw_hundred, last_output_at, last_progress_at, tail = monitor.snapshot()
                now = time.monotonic()
                if saw_hundred:
                    if not saw_hundred_reported and progress is not None:
                        progress("전사 100% 도달. 결과 정리 중")
                        saw_hundred_reported = True
                    if now - last_output_at > _POST_100_GRACE_SECONDS:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                        reader.join(timeout=5)
                        tail_text = "\n".join(tail[-20:])
                        raise RuntimeError(
                            "whisper.cpp가 100% 이후 종료되지 않아 중단했습니다.\n"
                            f"명령: {' '.join(command)}\n"
                            f"마지막 출력:\n{tail_text}"
                        )
                else:
                    if now - last_output_at > _STALL_TIMEOUT_SECONDS and now - last_progress_at > _STALL_TIMEOUT_SECONDS:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                        reader.join(timeout=5)
                        tail_text = "\n".join(tail[-20:])
                        raise RuntimeError(
                            "whisper.cpp 전사가 멈춘 것으로 보여 중단했습니다.\n"
                            f"명령: {' '.join(command)}\n"
                            f"마지막 진행률: {last_percent if last_percent is not None else '없음'}\n"
                            f"마지막 출력:\n{tail_text}"
                        )

                time.sleep(1.0)

            reader.join(timeout=5)
            if return_code != 0:
                _, _, _, _, tail = monitor.snapshot()
                tail_text = "\n".join(tail[-20:])
                raise RuntimeError(
                    "whisper.cpp 전사에 실패했습니다.\n"
                    f"명령: {' '.join(command)}\n"
                    f"종료 코드: {return_code}\n"
                    f"마지막 출력:\n{tail_text}"
                )

            json_path = output_prefix.with_name(f"{output_prefix.name}.json")
            if not json_path.exists():
                raise RuntimeError(
                    f"whisper.cpp JSON 결과 파일을 찾을 수 없습니다: {json_path}"
                )
            return json.loads(_read_json_text(json_path))


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
