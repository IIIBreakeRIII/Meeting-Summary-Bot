from __future__ import annotations

import json
from pathlib import Path

import typer

from .audio import FFmpegNotFoundError, UnsupportedAudioFormatError
from .config import load_settings, outputs_root
from .render import render_transcript_markdown
from .schemas import TranscriptDocument
from .summarize import summarize_transcript
from .transcribe import transcribe_audio_file

app = typer.Typer(add_completion=False, help="Local-first meeting transcription and summarization")


def _output_dir_for_audio(audio_path: Path) -> Path:
    return outputs_root() / audio_path.stem


def _exit_with_message(message: str) -> None:
    typer.secho(message, err=True, fg=typer.colors.RED)
    raise typer.Exit(code=1)


def _progress(message: str) -> None:
    typer.secho(f"[진행] {message}", fg=typer.colors.CYAN)


@app.command()
def transcribe(audio_path: Path, lang: str | None = typer.Option(None, "--lang")) -> None:
    settings = load_settings()
    output_dir = _output_dir_for_audio(audio_path)
    try:
        normalized_path, transcript = transcribe_audio_file(
            audio_path,
            output_dir=output_dir,
            language=lang,
            model_name=settings.whisper_model,
            use_vad=settings.whisper_use_vad,
            no_gpu=settings.whisper_no_gpu,
            beam_size=settings.whisper_beam_size,
            best_of=settings.whisper_best_of,
            suppress_nst=settings.whisper_suppress_nst,
            progress=_progress,
        )
    except FFmpegNotFoundError as exc:
        _exit_with_message(str(exc))
    except UnsupportedAudioFormatError as exc:
        _exit_with_message(str(exc))
    except RuntimeError as exc:
        _exit_with_message(str(exc))

    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_json_path = output_dir / "transcript.json"
    transcript_md_path = output_dir / "transcript.md"
    transcript_json_path.write_text(
        json.dumps(transcript.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    transcript_md_path.write_text(render_transcript_markdown(transcript), encoding="utf-8")
    typer.echo(f"정규화된 오디오: {normalized_path}")
    typer.echo(f"전사 JSON: {transcript_json_path}")
    typer.echo(f"전사 Markdown: {transcript_md_path}")


@app.command()
def summarize(transcript_json: Path) -> None:
    settings = load_settings()
    try:
        transcript = TranscriptDocument.model_validate_json(transcript_json.read_text(encoding="utf-8"))
        output_dir = transcript_json.parent
        result = summarize_transcript(transcript, output_dir=output_dir, settings=settings, progress=_progress)
    except RuntimeError as exc:
        _exit_with_message(str(exc))
    typer.echo(f"chunk summaries: {result.chunks_path}")
    typer.echo(f"summary JSON: {result.summary_json_path}")
    typer.echo(f"summary Markdown: {result.summary_md_path}")


@app.command()
def run(audio_path: Path, lang: str | None = typer.Option(None, "--lang")) -> None:
    settings = load_settings()
    output_dir = _output_dir_for_audio(audio_path)
    try:
        _progress("전사 시작")
        normalized_path, transcript = transcribe_audio_file(
            audio_path,
            output_dir=output_dir,
            language=lang,
            model_name=settings.whisper_model,
            use_vad=settings.whisper_use_vad,
            no_gpu=settings.whisper_no_gpu,
            beam_size=settings.whisper_beam_size,
            best_of=settings.whisper_best_of,
            suppress_nst=settings.whisper_suppress_nst,
            progress=_progress,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        transcript_json_path = output_dir / "transcript.json"
        transcript_md_path = output_dir / "transcript.md"
        _progress("전사 결과 파일 저장 중")
        transcript_json_path.write_text(
            json.dumps(transcript.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        transcript_md_path.write_text(render_transcript_markdown(transcript), encoding="utf-8")
        _progress("요약 시작")
        result = summarize_transcript(
            transcript,
            output_dir=output_dir,
            settings=settings,
            progress=_progress,
        )
    except FFmpegNotFoundError as exc:
        _exit_with_message(str(exc))
    except UnsupportedAudioFormatError as exc:
        _exit_with_message(str(exc))
    except RuntimeError as exc:
        _exit_with_message(str(exc))
    typer.echo(f"정규화된 오디오: {normalized_path}")
    typer.echo(f"전사 JSON: {transcript_json_path}")
    typer.echo(f"전사 Markdown: {transcript_md_path}")
    typer.echo(f"chunk summaries: {result.chunks_path}")
    typer.echo(f"summary JSON: {result.summary_json_path}")
    typer.echo(f"summary Markdown: {result.summary_md_path}")


if __name__ == "__main__":
    app()
