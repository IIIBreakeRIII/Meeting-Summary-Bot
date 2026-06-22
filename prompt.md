You are implementing a local-first meeting transcription and summarization pipeline for macOS Apple Silicon.

Build a Python 3.11+ CLI project named `meeting-summarizer`.

Goal:
Create a pipeline that takes a 1–2 hour meeting audio file, transcribes it locally using Whisper, then summarizes the transcript using OpenAI GPT-5.4 mini via the Responses API. The output should be both machine-readable JSON and human-readable Markdown.

Core privacy principle:
- Audio must be processed locally only.
- Only transcript text may be sent to OpenAI for summarization.
- The pipeline must preserve timestamp references so the summary can be traced back to the transcript.
- The model must not invent owners, due dates, risks, decisions, or speakers.

Target machine:
- Apple Silicon MacBook Pro
- 24GB unified memory

Tech stack:
- Python 3.11+
- `uv` for dependency management
- `typer` for CLI
- `pydantic` for schemas
- `python-dotenv` for config
- `openai` official Python SDK
- `ffmpeg` via subprocess for audio normalization
- Prefer `mlx-whisper` for Apple Silicon local transcription
- Add a clean abstraction so `faster-whisper` can be added later as a fallback

Models:
- Default transcription model: `mlx-community/whisper-large-v3-turbo`
- Default summary model: `gpt-5.4-mini`
- The summary model name must be configurable via environment variable `OPENAI_SUMMARY_MODEL`.
- The Whisper model name must be configurable via environment variable `WHISPER_MODEL`.

Environment variables:
```env
OPENAI_API_KEY=
OPENAI_SUMMARY_MODEL=gpt-5.4-mini
WHISPER_MODEL=mlx-community/whisper-large-v3-turbo
CHUNK_TARGET_CHARS=24000
```

Project structure:
```text
meeting-summarizer/
  README.md
  pyproject.toml
  .env.example

  src/
    meeting_summarizer/
      __init__.py
      cli.py
      config.py
      audio.py
      transcribe.py
      chunking.py
      summarize.py
      schemas.py
      render.py

  outputs/
    .gitkeep

  tests/
    test_chunking.py
    test_render.py
    test_schemas.py
```

Required CLI commands:

1. `meeting-summarizer transcribe AUDIO_PATH --lang ko`
   - Normalize audio to 16kHz mono WAV using ffmpeg.
   - Run local Whisper transcription.
   - Preserve segment-level timestamps.
   - Save:
     - `outputs/<audio_stem>/audio.normalized.wav`
     - `outputs/<audio_stem>/transcript.json`
     - `outputs/<audio_stem>/transcript.md`

2. `meeting-summarizer summarize TRANSCRIPT_JSON`
   - Load transcript JSON.
   - Chunk transcript into manageable blocks.
   - Do not split in the middle of a transcript segment.
   - Summarize each chunk using OpenAI Responses API.
   - Generate a final integrated meeting summary.
   - Save:
     - `outputs/<audio_stem>/chunks.json`
     - `outputs/<audio_stem>/summary.json`
     - `outputs/<audio_stem>/summary.md`

3. `meeting-summarizer run AUDIO_PATH --lang ko`
   - Execute transcription and summarization end-to-end.

Transcript JSON schema:
```json
{
  "audio_file": "original filename",
  "language": "ko",
  "duration_seconds": 0,
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 10.5,
      "speaker": null,
      "text": "transcribed text"
    }
  ]
}
```

Chunk summary JSON schema:
```json
{
  "chunk_id": 1,
  "source_time_range": "00:00:00-00:12:30",
  "key_discussions": [
    {
      "topic": "논의 주제",
      "summary": "논의 내용 요약",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "decisions": [
    {
      "decision": "결정된 내용",
      "rationale": "결정 배경 또는 이유. 알 수 없으면 '알 수 없음'.",
      "owner": "담당자 또는 '미정'",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"],
      "confidence": "high | medium | low"
    }
  ],
  "risks_or_issues": [
    {
      "issue": "리스크 또는 이슈",
      "impact": "예상 영향. 알 수 없으면 '알 수 없음'.",
      "mitigation": "대응 방안. 없으면 '미정'.",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "action_items": [
    {
      "owner": "담당자명 또는 '미정'",
      "task": "해야 할 일",
      "due_date": "마감일 또는 '미정'",
      "priority": "high | medium | low | unknown",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "open_questions_and_next_agenda": [
    {
      "item": "미해결 질문 또는 다음 회의 아젠다",
      "type": "open_question | next_agenda",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "notable_quotes": [
    {
      "speaker": "화자명 또는 '알 수 없음'",
      "quote": "중요한 발언 요약 또는 짧은 인용",
      "why_it_matters": "이 발언이 중요한 이유",
      "timestamp": "HH:MM:SS",
      "source_time_range": "HH:MM:SS-HH:MM:SS"
    }
  ]
}
```

Final summary JSON schema:
```json
{
  "meeting_title_or_agenda": "회의 제목 또는 아젠다",
  "one_line_summary": "회의 전체를 한 문장으로 요약",
  "overall_summary": "회의 전체 요약. 5~10문장 또는 3~5개 문단.",
  "key_discussions": [
    {
      "topic": "논의 주제",
      "summary": "논의 내용 요약",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "decisions": [
    {
      "decision": "결정된 내용",
      "rationale": "결정 배경 또는 이유. 알 수 없으면 '알 수 없음'.",
      "owner": "담당자 또는 '미정'",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"],
      "confidence": "high | medium | low"
    }
  ],
  "risks_or_issues": [
    {
      "issue": "리스크 또는 이슈",
      "impact": "예상 영향. 알 수 없으면 '알 수 없음'.",
      "mitigation": "대응 방안. 없으면 '미정'.",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "action_items_by_owner": [
    {
      "owner": "담당자명 또는 '미정'",
      "items": [
        {
          "task": "해야 할 일",
          "due_date": "마감일 또는 '미정'",
          "priority": "high | medium | low | unknown",
          "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
        }
      ]
    }
  ],
  "open_questions_and_next_agenda": [
    {
      "item": "미해결 질문 또는 다음 회의 아젠다",
      "type": "open_question | next_agenda",
      "source_time_ranges": ["HH:MM:SS-HH:MM:SS"]
    }
  ],
  "notable_quotes": [
    {
      "speaker": "화자명 또는 '알 수 없음'",
      "quote": "중요한 발언 요약 또는 짧은 인용",
      "why_it_matters": "이 발언이 중요한 이유",
      "timestamp": "HH:MM:SS",
      "source_time_range": "HH:MM:SS-HH:MM:SS"
    }
  ]
}
```

Markdown output must use this exact section order:
```markdown
# 회의록: <회의 제목(아젠다)>

## 한 줄 요약

<회의 전체를 한 문장으로 요약>

## 전체 요약

<회의 전체 요약>

## 주요 논의 사항 정리

### 1. <논의 주제>

- 요약:
- 근거 시간:

## 주요 결정 사항

| 결정사항 | 배경 | 담당자 | 신뢰도 | 근거 시간 |
|---|---|---|---|---|

## 리스크 / 이슈

| 리스크 / 이슈 | 영향 | 대응 방안 | 근거 시간 |
|---|---|---|---|

## 담당자 별 액션 아이템

| 담당자 | 할 일 | 마감일 | 우선순위 | 근거 시간 |
|---|---|---|---|---|

## 미해결 / 다음 회의 아젠다

| 유형 | 항목 | 근거 시간 |
|---|---|---|

## 중요한 발언 with timestamp references

| 시간 | 화자 | 발언 / 요지 | 중요한 이유 |
|---|---|---|---|
```

Chunking rules:
- Preserve timestamps.
- Do not split in the middle of a segment.
- Target chunk size should be configurable.
- Default chunk target: `CHUNK_TARGET_CHARS=24000`.
- Each chunk summary must include source time ranges.
- The final summary must merge duplicate action items, duplicate decisions, duplicate risks, and duplicate open questions.
- If a transcript is short enough, it may still go through the same chunk summary then final summary flow for consistency.

OpenAI summarization requirements:
- Use the OpenAI Python SDK.
- Use the Responses API.
- Use Structured Outputs / JSON schema if available through the SDK.
- If strict structured output fails, retry once with a repair prompt.
- Temperature should be low, around 0.2.
- Prompts should be Korean-first.
- The model must not invent owners, deadlines, speakers, decisions, or risks.
- Unknown owners should be `"미정"`.
- Unknown deadlines should be `"미정"`.
- Unknown speakers should be `"알 수 없음"`.
- Unknown dates should be `"알 수 없음"`.
- Weakly supported items should have `"confidence": "low"` where the schema supports confidence.

Chunk summary prompt behavior:
For each transcript chunk, extract:
- 주요 논의 사항
- 주요 결정 사항
- 리스크 / 이슈
- 담당자 별 액션 아이템
- 미해결 질문 / 다음 회의 아젠다
- 중요한 발언 with timestamp references

Final summary prompt behavior:
Merge all chunk summaries into one clean Korean meeting note with exactly these sections:
1. 회의 제목(아젠다)
2. 한 줄 요약
3. 전체 요약
4. 주요 논의 사항 정리
5. 주요 결정 사항
6. 리스크 / 이슈
7. 담당자 별 액션 아이템
8. 미해결 / 다음 회의 아젠다
9. 중요한 발언 with timestamp references

Important quote rules:
- Important quotes do not need to be verbatim if transcript quality is uncertain.
- Prefer concise quote-like summaries with accurate timestamp references.
- Include why the quote matters.
- Do not fabricate speaker names.

Transcript Markdown format:
```markdown
# Transcript: <audio filename>

## Metadata

- Language:
- Duration:
- Segment count:

## Transcript

[00:00:00 - 00:00:10] text
[00:00:10 - 00:00:20] text
```

Error handling:
- If ffmpeg is missing, show a clear installation message for macOS: `brew install ffmpeg`.
- If OpenAI API key is missing, show a clear `.env` setup message.
- If transcription fails, do not call the summarization step.
- If summarization fails halfway, save partial chunk summaries.
- If JSON parsing fails, retry once with a JSON repair prompt.
- Log progress clearly for long audio files.

Testing:
- Add unit tests for chunking.
- Add unit tests for timestamp formatting.
- Add unit tests for Markdown rendering.
- Add unit tests for Pydantic schema validation.
- Do not require real OpenAI API calls in unit tests; mock them.

README must include:
- Installation steps with `uv`
- ffmpeg installation instructions for macOS
- `.env.example`
- CLI usage examples
- Output file explanation
- Privacy note explaining that audio transcription is local, but transcript text is sent to OpenAI for summarization
- Troubleshooting section for ffmpeg, OpenAI API key, and mlx-whisper installation

Acceptance criteria:
- `uv run meeting-summarizer run path/to/meeting.m4a --lang ko` works.
- It creates:
  - `audio.normalized.wav`
  - `transcript.json`
  - `transcript.md`
  - `chunks.json`
  - `summary.json`
  - `summary.md`
- The final Markdown contains exactly the requested sections.
- Every decision, action item, risk, open question, and notable quote should include timestamp references when available.
- The code is modular, typed where practical, and easy to extend.
- No secrets are committed.
- The project should be usable as an MVP without additional manual steps beyond installing dependencies, installing ffmpeg, and setting `OPENAI_API_KEY`.
