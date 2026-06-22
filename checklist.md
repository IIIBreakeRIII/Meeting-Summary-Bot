# Phase 1 - Scaffold and shared foundation
- [ ] `uv sync` / `uv run` 동작 여부
- [ ] `pyproject.toml`에 CLI entrypoint가 등록되어 있는지
- [ ] `.env.example`에 필수 환경변수가 있는지
- [ ] `OPENAI_API_KEY`를 읽는지
- [ ] `WHISPER_MODEL`을 환경변수로 바꿀 수 있는지
- [ ] `OPENAI_SUMMARY_MODEL`을 환경변수로 바꿀 수 있는지
- [ ] `CHUNK_TARGET_CHARS`를 환경변수로 바꿀 수 있는지
- [ ] Pydantic 스키마가 extra field를 거부하는지

# Phase 2 - Local transcription
- [ ] `ffmpeg` 없을 때 에러 메시지가 명확한지
- [ ] 오디오가 `audio.normalized.wav`로 저장되는지
- [ ] segment timestamp가 보존되는지
- [ ] `transcript.json`이 생성되는지
- [ ] `transcript.md`가 생성되는지
- [ ] 전사 실패 시 요약 단계가 호출되지 않는지

# Phase 3 - Chunking, summary, rendering
- [ ] chunk가 segment 중간에서 잘리지 않는지
- [ ] chunk마다 `source_time_range`가 있는지
- [ ] chunk 요약이 JSON schema에 맞는지
- [ ] final summary JSON이 스키마에 맞는지
- [ ] final Markdown 섹션 순서가 정확한지
- [ ] 액션 아이템에 담당자/마감일/근거 시간이 있는지
- [ ] 모르는 값이 추측되지 않고 `미정` / `알 수 없음`으로 들어가는지
- [ ] 중복된 결정/액션/리스크/질문이 최종 요약에서 합쳐지는지
- [ ] notable quote에 timestamp reference가 있는지

# Phase 4 - Verification and docs
- [ ] 중간 실패 시 partial output이 저장되는지
- [ ] unit test가 실제 API 호출 없이 통과하는지
- [ ] README에 설치 방법이 있는지
- [ ] README에 macOS ffmpeg 설치 방법이 있는지
- [ ] README에 CLI 사용 예시가 있는지
- [ ] README에 privacy note가 있는지
- [ ] README에 troubleshooting이 있는지

