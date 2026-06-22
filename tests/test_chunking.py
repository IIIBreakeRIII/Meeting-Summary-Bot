from meeting_summarizer.chunking import chunk_transcript, format_time_range, format_timestamp
from meeting_summarizer.schemas import TranscriptDocument, TranscriptSegment
from meeting_summarizer.transcribe import build_transcript_document


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65.9) == "00:01:05"
    assert format_timestamp(3661) == "01:01:01"


def test_format_time_range():
    assert format_time_range(10, 20.2) == "00:00:10-00:00:20"


def test_chunk_transcript_does_not_split_segments():
    doc = TranscriptDocument(
        audio_file="meeting.m4a",
        language="ko",
        duration_seconds=20.0,
        segments=[
            TranscriptSegment(id=0, start=0.0, end=5.0, speaker=None, text="a" * 10),
            TranscriptSegment(id=1, start=5.0, end=10.0, speaker=None, text="b" * 10),
            TranscriptSegment(id=2, start=10.0, end=15.0, speaker=None, text="c" * 10),
        ],
    )
    chunks = chunk_transcript(doc, target_chars=50)
    assert len(chunks) == 3
    assert chunks[0].source_time_range == "00:00:00-00:00:05"


def test_build_transcript_document_from_whisper_cpp_json():
    doc = build_transcript_document(
        audio_file="meeting.m4a",
        language="ko",
        duration_seconds=12.0,
        raw_result={
            "result": {"language": "ko"},
            "transcription": [
                {"timestamps": {"from": "00:00:00", "to": "00:00:05"}, "text": "안녕하세요"},
                {"timestamps": {"from": "00:00:05", "to": "00:00:10"}, "text": "반갑습니다"},
            ],
        },
    )
    assert doc.language == "ko"
    assert doc.segments[0].start == 0.0
    assert doc.segments[1].end == 10.0
