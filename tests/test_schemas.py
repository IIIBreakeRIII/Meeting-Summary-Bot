from pydantic import ValidationError

from meeting_summarizer.schemas import TranscriptDocument


def test_transcript_schema_validation():
    doc = TranscriptDocument.model_validate(
        {
            "audio_file": "meeting.m4a",
            "language": "ko",
            "duration_seconds": 12.5,
            "segments": [
                {"id": 0, "start": 0.0, "end": 10.0, "speaker": None, "text": "안녕하세요"}
            ],
        }
    )
    assert doc.segments[0].text == "안녕하세요"


def test_transcript_schema_rejects_extra_fields():
    try:
        TranscriptDocument.model_validate(
            {
                "audio_file": "meeting.m4a",
                "language": "ko",
                "duration_seconds": 12.5,
                "segments": [],
                "extra": True,
            }
        )
    except ValidationError:
        return
    raise AssertionError("ValidationError가 발생해야 합니다.")

