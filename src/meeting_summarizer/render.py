from __future__ import annotations

from collections import defaultdict

from .chunking import format_timestamp
from .schemas import ChunkSummaryBundle, FinalSummary, TranscriptDocument


def render_transcript_markdown(doc: TranscriptDocument) -> str:
    lines = [
        f"# Transcript: {doc.audio_file}",
        "",
        "## Metadata",
        "",
        f"- Language: {doc.language}",
        f"- Duration: {doc.duration_seconds}",
        f"- Segment count: {len(doc.segments)}",
        "",
        "## Transcript",
        "",
    ]
    for segment in doc.segments:
        lines.append(
            f"[{format_timestamp(segment.start)} - {format_timestamp(segment.end)}] {segment.text}"
        )
    return "\n".join(lines).rstrip() + "\n"


def render_summary_markdown(summary: FinalSummary) -> str:
    lines = [
        f"# 회의록: {summary.meeting_title_or_agenda}",
        "",
        "## 한 줄 요약",
        "",
        summary.one_line_summary,
        "",
        "## 전체 요약",
        "",
        summary.overall_summary,
        "",
        "## 주요 논의 사항 정리",
        "",
    ]
    for index, item in enumerate(summary.key_discussions, start=1):
        time_ranges = ", ".join(item.source_time_ranges) if item.source_time_ranges else "미정"
        lines.extend(
            [
                f"### {index}. {item.topic}",
                "",
                f"- 요약: {item.summary}",
                f"- 근거 시간: {time_ranges}",
                "",
            ]
        )

    lines.extend(
        [
            "## 주요 결정 사항",
            "",
            "| 결정사항 | 배경 | 담당자 | 신뢰도 | 근거 시간 |",
            "|---|---|---|---|---|",
        ]
    )
    for item in summary.decisions:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.decision,
                    item.rationale,
                    item.owner,
                    item.confidence,
                    ", ".join(item.source_time_ranges) if item.source_time_ranges else "미정",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 리스크 / 이슈",
            "",
            "| 리스크 / 이슈 | 영향 | 대응 방안 | 근거 시간 |",
            "|---|---|---|---|",
        ]
    )
    for item in summary.risks_or_issues:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.issue,
                    item.impact,
                    item.mitigation,
                    ", ".join(item.source_time_ranges) if item.source_time_ranges else "미정",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 담당자 별 액션 아이템",
            "",
            "| 담당자 | 할 일 | 마감일 | 우선순위 | 근거 시간 |",
            "|---|---|---|---|---|",
        ]
    )
    by_owner = defaultdict(list)
    for owner_group in summary.action_items_by_owner:
        by_owner[owner_group.owner].extend(owner_group.items)
    for owner, items in by_owner.items():
        for item in items:
            lines.append(
                "| "
                + " | ".join(
                    [
                        owner,
                        item.task,
                        item.due_date,
                        item.priority,
                        ", ".join(item.source_time_ranges) if item.source_time_ranges else "미정",
                    ]
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## 미해결 / 다음 회의 아젠다",
            "",
            "| 유형 | 항목 | 근거 시간 |",
            "|---|---|---|",
        ]
    )
    for item in summary.open_questions_and_next_agenda:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.type,
                    item.item,
                    ", ".join(item.source_time_ranges) if item.source_time_ranges else "미정",
                ]
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## 중요한 발언 with timestamp references",
            "",
            "| 시간 | 화자 | 발언 / 요지 | 중요한 이유 |",
            "|---|---|---|---|",
        ]
    )
    for item in summary.notable_quotes:
        lines.append(
            "| "
            + " | ".join([item.timestamp, item.speaker, item.quote, item.why_it_matters])
            + " |"
        )

    return "\n".join(lines).rstrip() + "\n"


def render_chunks_bundle_markdown(bundle: ChunkSummaryBundle) -> str:
    lines = [
        f"# Chunk summaries: {bundle.audio_file}",
        "",
    ]
    for chunk in bundle.chunks:
        lines.extend(
            [
                f"## Chunk {chunk.chunk_id}",
                "",
                f"- Time range: {chunk.source_time_range}",
                f"- Key discussions: {len(chunk.key_discussions)}",
                f"- Decisions: {len(chunk.decisions)}",
                f"- Risks: {len(chunk.risks_or_issues)}",
                f"- Action items: {len(chunk.action_items)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"

