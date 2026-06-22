# meeting-summarizer

[Whisper-Transcript-Generator](https://github.com/IIIBreakeRIII/Whisper-Transcript-Generator) 의 Version 2

`meeting-summarizer`는 iPhone에서 녹음한 `m4a`를 포함한 로컬 오디오를 전사한 뒤, 전사 텍스트만 OpenAI로 보내 회의 요약을 만드는 CLI입니다.

현재 전사는 `whisper.cpp`의 `whisper-cli`로 수행하고, 요약은 OpenAI Responses API를 사용합니다. 전사와 요약 진행 상황은 터미널에 표시됩니다.

## 구성

- 로컬 오디오 전사: `whisper.cpp`
- 전사 후 정규화: `ffmpeg`
- 회의 요약: OpenAI API
- 실행 방식: `uv run meeting-summarizer ...`

## 빠른 시작

1. 의존성 설치

```bash
uv sync
```

2. `ffmpeg` 설치

```bash
brew install ffmpeg
```

3. `whisper.cpp` 준비

```bash
git clone https://github.com/ggml-org/whisper.cpp.git
cd whisper.cpp
cmake -B build
cmake --build build -j --config Release
cd models
./download-ggml-model.sh large-v3-turbo
```

4. 프로젝트 루트에 `.env` 설정

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_SUMMARY_MODEL=gpt-5.4-mini
WHISPER_MODEL=/absolute/path/to/whisper.cpp/models/ggml-large-v3-turbo.bin
WHISPER_CLI=/absolute/path/to/whisper.cpp/build/bin/whisper-cli
WHISPER_USE_VAD=false
WHISPER_NO_GPU=true
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_SUPPRESS_NST=true
CHUNK_TARGET_CHARS=24000
```

## 사용법

지원하는 오디오 형식 예시:

- `m4a`
- `mp3`
- `wav`
- `mp4`
- `aac`
- `flac`
- `ogg`

### 전체 실행

전사와 요약을 한 번에 실행합니다.

```bash
uv run meeting-summarizer run path/to/meeting.m4a --lang ko
```

### 전사만 실행

```bash
uv run meeting-summarizer transcribe path/to/meeting.m4a --lang ko
```

### 요약만 실행

전사 결과 JSON이 이미 있을 때 사용합니다.

```bash
uv run meeting-summarizer summarize outputs/meeting/transcript.json
```

## 출력 파일

입력 파일이 `path/to/meeting.m4a`라면 기본 출력 폴더는 `outputs/meeting/`입니다.

- `audio.normalized.wav`
- `transcript.json`
- `transcript.md`
- `chunks.json`
- `summary.json`
- `summary.md`

## 전사 품질 팁

`m4a` 녹음은 그대로 넣어도 되지만, 결과는 내부적으로 `ffmpeg`로 16kHz mono WAV로 바꾼 뒤 전사합니다.

정확도를 높이려면 아래 설정을 유지하는 편이 좋습니다.

- `WHISPER_USE_VAD=false`
- `WHISPER_NO_GPU=true`
- `WHISPER_BEAM_SIZE=5`
- `WHISPER_BEST_OF=5`
- `WHISPER_SUPPRESS_NST=true`

아이폰 녹음처럼 음질이 비교적 좋은 소스는 `m4a` 입력으로도 잘 동작합니다. 다만 전사 품질은 원본 음성의 겹침, 잡음, 말 빠르기, 마이크 거리 영향을 받습니다.

## 진행 상황

실행 중에는 다음처럼 상태가 표시됩니다.

- 전사 시작
- 오디오 정규화 중
- 로컬 전사 중
- 전사 진행률 표시
- 전사 결과 저장 중
- 요약 시작
- chunk 요약 중
- 최종 요약 생성 중
- 요약 저장 완료

## 개인정보 안내

- 오디오는 로컬에서만 전사합니다.
- 요약을 위해서만 전사 텍스트가 OpenAI로 전송됩니다.
- 타임스탬프는 전사 결과에서 보존되며, `summary.md`에서도 참조할 수 있습니다.

## 문제 해결

### `ffmpeg`가 없다고 나올 때

```bash
brew install ffmpeg
```

### `whisper.cpp` CLI를 찾을 수 없다고 나올 때

`WHISPER_CLI`를 절대경로로 지정하세요.

```bash
export WHISPER_CLI=/absolute/path/to/whisper.cpp/build/bin/whisper-cli
```

### 모델 파일을 찾을 수 없다고 나올 때

`WHISPER_MODEL`을 whisper.cpp 모델 파일의 절대경로로 바꾸세요.

```bash
export WHISPER_MODEL=/absolute/path/to/whisper.cpp/models/ggml-large-v3-turbo.bin
```

### Metal 관련 오류가 날 때

이 프로젝트는 기본적으로 `WHISPER_NO_GPU=true`로 실행해서 GPU/Metal 문제를 피합니다. 그래도 오류가 계속 나면 `whisper.cpp`를 다시 빌드하거나 CPU-only 설정을 유지하세요.

### 진행률이 안 보일 때

`whisper.cpp`의 CLI 빌드가 오래되었으면 `-pp` 진행률 출력이 다르게 보일 수 있습니다. 최신 빌드로 다시 컴파일해 보세요.

### 타임스탬프가 부정확할 때

이 프로젝트는 `whisper.cpp`가 생성한 세그먼트 offset을 우선 사용합니다. 그래도 품질이 낮다면 아래를 먼저 점검하세요.

- 녹음 중 겹치는 발화가 많지 않은지 확인
- 마이크와 입 사이 거리를 줄이기
- 잡음을 줄이기
- `large-v3-turbo` 모델이 실제로 사용 중인지 확인

## 권장 설정

처음 쓰는 경우에는 아래 조합으로 시작하는 것을 권장합니다.

```env
WHISPER_USE_VAD=false
WHISPER_NO_GPU=true
WHISPER_BEAM_SIZE=5
WHISPER_BEST_OF=5
WHISPER_SUPPRESS_NST=true
```

`whisper.cpp` 모델 파일과 `whisper-cli` 경로는 `.env`에 절대경로로 넣어 두면 가장 편합니다.
