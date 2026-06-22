from meeting_summarizer.render import render_summary_markdown, render_transcript_markdown
from meeting_summarizer.schemas import (
    ActionItem,
    ActionItemsByOwner,
    ChunkSummary,
    DecisionItem,
    FinalSummary,
    KeyDiscussion,
    NotableQuoteItem,
    OpenQuestionItem,
    RiskItem,
    TranscriptDocument,
    TranscriptSegment,
)


def test_render_transcript_markdown():
    doc = TranscriptDocument(
        audio_file="meeting.m4a",
        language="ko",
        duration_seconds=12.0,
        segments=[TranscriptSegment(id=0, start=0, end=10, speaker=None, text="안녕하세요")],
    )
    md = render_transcript_markdown(doc)
    assert md.startswith("# Transcript: meeting.m4a")
    assert "## Metadata" in md
    assert "[00:00:00 - 00:00:10] 안녕하세요" in md


def test_render_summary_markdown_section_order():
    summary = FinalSummary(
        meeting_title_or_agenda="회의",
        one_line_summary="한 줄",
        overall_summary="전체",
        key_discussions=[KeyDiscussion(topic="주제", summary="요약", source_time_ranges=["00:00:00-00:00:10"])],
        decisions=[DecisionItem(decision="결정", rationale="배경", owner="미정", source_time_ranges=["00:00:00-00:00:10"], confidence="low")],
        risks_or_issues=[RiskItem(issue="리스크", impact="영향", mitigation="대응", source_time_ranges=["00:00:00-00:00:10"])],
        action_items_by_owner=[ActionItemsByOwner(owner="미정", items=[ActionItem(owner="미정", task="할 일", due_date="미정", priority="unknown", source_time_ranges=["00:00:00-00:00:10"])])],
        open_questions_and_next_agenda=[OpenQuestionItem(item="질문", type="open_question", source_time_ranges=["00:00:00-00:00:10"])],
        notable_quotes=[NotableQuoteItem(speaker="알 수 없음", quote="요지", why_it_matters="중요", timestamp="00:00:05", source_time_range="00:00:00-00:00:10")],
    )
    md = render_summary_markdown(summary)
    expected_sections = [
        "# 회의록: 회의",
        "## 한 줄 요약",
        "## 전체 요약",
        "## 주요 논의 사항 정리",
        "## 주요 결정 사항",
        "## 리스크 / 이슈",
        "## 담당자 별 액션 아이템",
        "## 미해결 / 다음 회의 아젠다",
        "## 중요한 발언 with timestamp references",
    ]
    index = -1
    for section in expected_sections:
        next_index = md.index(section)
        assert next_index > index
        index = next_index

