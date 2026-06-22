# meeting-summarizer 사용 가이드

이 도구는 iPhone 등에서 녹음한 오디오를 로컬에서 전사한 뒤, 전사 텍스트만 OpenAI로 보내 회의 요약을 생성하는 CLI입니다.
현재 전사 엔진은 `whisper.cpp` 기반이며, 전사와 요약 모두 진행 상황이 터미널에 표시됩니다.

## 1. 준비 사항

### 필수

- Python 3.11 이상
- `uv`
- `ffmpeg`
- `whisper.cpp` 빌드와 모델 파일
- OpenAI API 키

### 설치

```bash
uv sync
```

`uv`를 쓰지 않는다면 `requirements.txt`로도 설치할 수 있습니다.

```bash
pip install -r requirements.txt
```

### ffmpeg 설치

macOS에서는 아래처럼 설치합니다.

```bash
brew install ffmpeg
```

### whisper.cpp 설치

전사 엔진으로 `whisper.cpp`의 `whisper-cli`를 사용합니다.

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j --config Release
```

모델은 `whisper.cpp/models/` 아래에서 내려받을 수 있습니다.

```bash
cd models
./download-ggml-model.sh large-v3-turbo
```

권장 모델 파일 예시:

- `whisper.cpp/models/ggml-large-v3-turbo.bin`

실행 파일과 모델 파일을 찾기 어렵다면 `.env`에서 아래처럼 지정할 수 있습니다.

```env
WHISPER_CLI=/절대경로/whisper.cpp/build/bin/whisper-cli
WHISPER_MODEL=/절대경로/whisper.cpp/models/ggml-large-v3-turbo.bin
```

### 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 아래처럼 설정합니다.

```env
OPENAI_API_KEY=your-api-key
OPENAI_SUMMARY_MODEL=gpt-5.4-mini
WHISPER_MODEL=/absolute/path/to/whisper.cpp/models/ggml-large-v3-turbo.bin
CHUNK_TARGET_CHARS=24000
WHISPER_USE_VAD=false
WHISPER_NO_GPU=true
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_SUPPRESS_NST=true
WHISPER_CLI=/absolute/path/to/whisper.cpp/build/bin/whisper-cli
```

기본값:

- `OPENAI_SUMMARY_MODEL`: `gpt-5.4-mini`
- `WHISPER_MODEL`: `models/ggml-large-v3-turbo.bin` 또는 `.env`에 지정한 절대경로
- `CHUNK_TARGET_CHARS`: `24000`
- `WHISPER_USE_VAD`: `false`
- `WHISPER_NO_GPU`: `true`
- `WHISPER_BEAM_SIZE`: `5`
- `WHISPER_BEST_OF`: `5`
- `WHISPER_SUPPRESS_NST`: `true`
- `WHISPER_CLI`: 자동 탐색, 없으면 `.env`로 지정

## 2. 실행 방법

지원하는 오디오 형식 예시:

- `.m4a`
- `.mp3`
- `.wav`
- `.mp4`
- `.aac`
- `.flac`

### 전체 실행

오디오 전사와 요약을 한 번에 실행합니다.

```bash
uv run meeting-summarizer run path/to/meeting.m4a --lang ko
```

실행 중에는 아래처럼 진행 상황이 보입니다.

- `[진행] 전사 시작`
- `[진행] 오디오 정규화 중`
- `[진행] 로컬 전사 중`
- `[진행] 전사 진행률 10%`
- `[진행] 전사 결과 파일 저장 중`
- `[진행] 요약 시작`
- `[진행] chunk 요약 중 (1/N)`
- `[진행] 최종 요약 생성 중`
- `[진행] 요약 저장 완료`

### 전사만 실행

```bash
uv run meeting-summarizer transcribe path/to/meeting.m4a --lang ko
```

### 요약만 실행

전사 결과 JSON이 이미 있을 때 사용합니다.

```bash
uv run meeting-summarizer summarize outputs/meeting/transcript.json
```

## 3. 출력 구조

입력 파일이 `path/to/meeting.m4a`라면 기본 출력 폴더는 다음과 같습니다.

```text
outputs/meeting/
```

생성 파일:

- `audio.normalized.wav`
- `transcript.json`
- `transcript.md`
- `chunks.json`
- `summary.json`
- `summary.md`

## 4. 각 파일의 의미

### `audio.normalized.wav`

- `ffmpeg`로 정규화한 로컬 WAV 파일
- 16kHz mono 형식으로 변환됩니다
- 원본이 `.m4a`여도 이 파일로 변환된 뒤 전사됩니다

### `transcript.json`

- 전사 결과의 JSON
- segment 단위 timestamp가 보존됩니다

### `transcript.md`

- 사람이 읽기 쉬운 전사본
- 각 줄에 `[start - end] text` 형태로 타임스탬프가 들어갑니다

### `chunks.json`

- 전사 세그먼트를 chunk 단위로 나눈 뒤, 각 chunk의 요약 결과를 저장합니다
- chunk마다 `source_time_range`가 포함됩니다

### `summary.json`

- 전체 회의에 대한 통합 요약 JSON
- 결정사항, 리스크, 액션 아이템, 미해결 질문, 중요한 발언이 포함됩니다

### `summary.md`

- 최종 회의록의 Markdown 버전
- 문서 내 섹션 순서는 아래와 같습니다.

1. 회의 제목
2. 한 줄 요약
3. 전체 요약
4. 주요 논의 사항 정리
5. 주요 결정 사항
6. 리스크 / 이슈
7. 담당자 별 액션 아이템
8. 미해결 / 다음 회의 아젠다
9. 중요한 발언 with timestamp references

### `transcript` 시간 정보

- `whisper.cpp`의 세그먼트 offset을 우선 사용합니다
- 시간이 `00:00:00`만 보이면 보통 파서 문제이므로, 최신 버전에서는 수정되어 있습니다

## 5. 작업 흐름

추천 흐름은 아래와 같습니다.

1. 오디오 전사
2. `transcript.json` 확인
3. 필요하면 `summarize`만 별도로 재실행
4. 최종 `summary.md` 확인

긴 회의 파일이면 chunk 요약이 순차적으로 진행되므로, 중간에 어느 chunk를 처리 중인지 확인할 수 있습니다.

예시:

```bash
uv run meeting-summarizer transcribe path/to/meeting.m4a --lang ko
uv run meeting-summarizer summarize outputs/meeting/transcript.json
```

## 6. 개인정보와 보안

- 오디오는 로컬에서만 처리합니다.
- 요약을 위해서만 전사 텍스트가 OpenAI로 전송됩니다.
- 비밀 키는 `.env`에만 두고 커밋하지 않습니다.

## 7. 자주 겪는 문제

### `ffmpeg`를 찾을 수 없다고 나올 때

```bash
brew install ffmpeg
```

### `OPENAI_API_KEY`가 없다고 나올 때

`.env`에 키를 추가하세요.

```env
OPENAI_API_KEY=...
```

### `whisper.cpp` 관련 오류가 날 때

- Apple Silicon 환경인지 확인하세요
- Python 3.11 이상인지 확인하세요
- `uv sync`를 다시 실행해 보세요
- 이 프로젝트는 기본 전사 엔진으로 `whisper.cpp`의 `whisper-cli`를 사용합니다
- `WHISPER_MODEL`은 whisper.cpp용 모델 파일 경로여야 합니다
- 모델 파일이 없다면 `whisper.cpp/models/`에서 내려받아 두세요
- 실행 파일 경로를 직접 지정하려면 `WHISPER_CLI=/절대경로/whisper.cpp/build/bin/whisper-cli`처럼 설정하세요
- `WHISPER_USE_VAD`는 기본적으로 끄고, 필요할 때만 켜 보세요
- `WHISPER_NO_GPU=true`로 Metal 문제를 우회합니다
- 정확도를 올리고 싶으면 `WHISPER_BEAM_SIZE=5`, `WHISPER_BEST_OF=5`, `WHISPER_SUPPRESS_NST=true`를 유지하세요
- `pyenv` 경고가 떠도 `.venv`가 실제로 사용되면 정상입니다

### 요약이 중간에 실패했을 때

- `chunks.json`은 chunk 단위로 저장되므로, 일부 chunk 요약은 남을 수 있습니다
- 이후 `summarize outputs/meeting/transcript.json`으로 다시 시도할 수 있습니다

## 8. Phase별 점검

구현 상태를 확인할 때는 [checklist.md](/Users/devpaul/Dev/MeetingSTT/Meeting-Summary-Bot/checklist.md)를 보면 됩니다.

- Phase 1: scaffold와 설정
- Phase 2: 로컬 전사
- Phase 3: chunking과 요약
- Phase 4: 검증과 문서

## 9. 추천 설정

현재 기준으로 가장 무난한 시작값은 아래입니다.

```env
WHISPER_USE_VAD=false
WHISPER_NO_GPU=true
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_SUPPRESS_NST=true
```

전사 속도가 너무 느리면 `WHISPER_BEAM_SIZE`와 `WHISPER_BEST_OF`를 3 정도로 낮춰 볼 수 있고, 전사 품질이 불안하면 먼저 녹음 환경과 모델 파일 경로를 확인하는 게 좋습니다.
