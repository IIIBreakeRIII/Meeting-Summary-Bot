from __future__ import annotations

from dataclasses import dataclass

from .schemas import TranscriptDocument, TranscriptSegment


@dataclass(frozen=True)
class TranscriptChunk:
    chunk_id: int
    segments: list[TranscriptSegment]

    @property
    def start(self) -> float:
        return self.segments[0].start

    @property
    def end(self) -> float:
        return self.segments[-1].end

    @property
    def source_time_range(self) -> str:
        return f"{format_timestamp(self.start)}-{format_timestamp(self.end)}"


def format_timestamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_time_range(start: float, end: float) -> str:
    return f"{format_timestamp(start)}-{format_timestamp(end)}"


def chunk_transcript(doc: TranscriptDocument, target_chars: int) -> list[TranscriptChunk]:
    chunks: list[TranscriptChunk] = []
    current: list[TranscriptSegment] = []
    current_chars = 0

    for segment in doc.segments:
        segment_cost = len(segment.text) + 32
        if current and current_chars + segment_cost > target_chars:
            chunks.append(TranscriptChunk(chunk_id=len(chunks) + 1, segments=current))
            current = []
            current_chars = 0

        current.append(segment)
        current_chars += segment_cost

    if current:
        chunks.append(TranscriptChunk(chunk_id=len(chunks) + 1, segments=current))

    return chunks


def render_chunk_text(chunk: TranscriptChunk) -> str:
    lines = []
    for segment in chunk.segments:
        lines.append(
            f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}] {segment.text}"
        )
    return "\n".join(lines)

