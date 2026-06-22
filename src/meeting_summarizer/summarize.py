from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI
from pydantic import ValidationError

from .chunking import TranscriptChunk, chunk_transcript, render_chunk_text
from .config import Settings, ensure_openai_key
from .render import render_summary_markdown
from .schemas import ChunkSummary, ChunkSummaryBundle, FinalSummary, TranscriptDocument


def _openai_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    def _walk(node: Any) -> Any:
        if isinstance(node, list):
            return [_walk(item) for item in node]
        if not isinstance(node, dict):
            return node

        transformed = {key: _walk(value) for key, value in node.items()}

        if transformed.get("type") == "object" and "properties" in transformed:
            properties = transformed["properties"]
            if isinstance(properties, dict):
                transformed["required"] = list(properties.keys())
            transformed["additionalProperties"] = False

        if "items" in transformed:
            transformed["items"] = _walk(transformed["items"])

        for key in ("anyOf", "oneOf", "allOf", "$defs"):
            if key in transformed:
                transformed[key] = _walk(transformed[key])

        return transformed

    return _walk(schema)


CHUNK_SUMMARY_SCHEMA: dict[str, Any] = _openai_strict_schema(ChunkSummary.model_json_schema())
FINAL_SUMMARY_SCHEMA: dict[str, Any] = _openai_strict_schema(FinalSummary.model_json_schema())


@dataclass
class SummarizationResult:
    chunks_bundle: ChunkSummaryBundle
    final_summary: FinalSummary
    chunks_path: Path
    summary_json_path: Path
    summary_md_path: Path


def _openai_client(settings: Settings) -> OpenAI:
    return OpenAI(api_key=ensure_openai_key(settings))


def _validate_model(model: type[Any], payload: Any) -> Any:
    return model.model_validate(payload)


def _parse_json_with_repair(
    *,
    text: str,
    repair_prompt: str,
    client: OpenAI,
    model_name: str,
    schema: dict[str, Any],
    validator: type[Any],
) -> Any:
    try:
        return _validate_model(validator, json.loads(text))
    except (json.JSONDecodeError, ValidationError):
        repaired = client.responses.create(
            model=model_name,
            input=repair_prompt,
            temperature=0.2,
            text={
                "format": {
                    "type": "json_schema",
                    "name": validator.__name__,
                    "schema": schema,
                    "strict": True,
                }
            },
        )
        repaired_text = getattr(repaired, "output_text", None) or ""
        return _validate_model(validator, json.loads(repaired_text))


def _make_response(
    client: OpenAI,
    *,
    model_name: str,
    prompt: str,
    schema_name: str,
    schema: dict[str, Any],
) -> Any:
    return client.responses.create(
        model=model_name,
        input=prompt,
        temperature=0.2,
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": schema,
                "strict": True,
            }
        },
    )


def _chunk_prompt(chunk: TranscriptChunk) -> str:
    return f"""다음은 회의 전사 일부입니다. 한국어로만 요약하세요.

원칙:
- 오디오가 아니라 전사 텍스트만 사용하세요.
- 사실을 추측하지 마세요.
- 담당자, 마감일, 화자, 결정, 리스크를 임의로 만들지 마세요.
- 모르면 반드시 \"미정\" 또는 \"알 수 없음\"을 사용하세요.
- 모든 항목은 근거 시간 범위를 포함하세요.

chunk_id: {chunk.chunk_id}
source_time_range: {chunk.source_time_range}

전사:
{render_chunk_text(chunk)}
"""


def _final_prompt(bundle: ChunkSummaryBundle) -> str:
    chunk_payload = json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2)
    return f"""다음은 여러 chunk의 회의 요약입니다. 한국어로 최종 회의록을 만드세요.

원칙:
- 중복되는 결정, 액션 아이템, 리스크, 질문은 합쳐서 정리하세요.
- 오디오가 아니라 chunk summaries만 사용하세요.
- 사실을 추측하지 마세요.
- 담당자, 마감일, 화자, 결정, 리스크를 임의로 만들지 마세요.
- 모르면 반드시 \"미정\" 또는 \"알 수 없음\"을 사용하세요.
- 각 항목은 가능한 경우 source_time_ranges를 유지하세요.

chunk summaries:
{chunk_payload}
"""


def summarize_transcript(
    transcript: TranscriptDocument,
    *,
    output_dir: Path,
    settings: Settings,
    client: OpenAI | None = None,
    progress: Callable[[str], None] | None = None,
) -> SummarizationResult:
    client = client or _openai_client(settings)
    chunks = chunk_transcript(transcript, settings.chunk_target_chars)

    chunk_summaries: list[ChunkSummary] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    chunks_path = output_dir / "chunks.json"
    summary_json_path = output_dir / "summary.json"
    summary_md_path = output_dir / "summary.md"

    if progress:
        progress(f"chunk 요약 준비 중 ({len(chunks)}개)")

    for index, chunk in enumerate(chunks, start=1):
        if progress:
            progress(f"chunk 요약 중 ({index}/{len(chunks)})")
        response = _make_response(
            client,
            model_name=settings.openai_summary_model,
            prompt=_chunk_prompt(chunk),
            schema_name="chunk_summary",
            schema=CHUNK_SUMMARY_SCHEMA,
        )
        response_text = getattr(response, "output_text", None) or ""
        repair_prompt = (
            "다음 응답을 유효한 JSON으로 고쳐 주세요. 스키마를 지키고, "
            "새로운 사실을 추가하지 마세요.\n\n"
            f"응답:\n{response_text}"
        )
        chunk_summary = _parse_json_with_repair(
            text=response_text,
            repair_prompt=repair_prompt,
            client=client,
            model_name=settings.openai_summary_model,
            schema=CHUNK_SUMMARY_SCHEMA,
            validator=ChunkSummary,
        )
        chunk_summaries.append(chunk_summary)
        if progress:
            progress(f"chunk 저장 중 ({index}/{len(chunks)})")
        bundle = ChunkSummaryBundle(
            audio_file=transcript.audio_file,
            language=transcript.language,
            chunk_target_chars=settings.chunk_target_chars,
            chunks=chunk_summaries,
        )
        chunks_path.write_text(
            json.dumps(bundle.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    bundle = ChunkSummaryBundle(
        audio_file=transcript.audio_file,
        language=transcript.language,
        chunk_target_chars=settings.chunk_target_chars,
        chunks=chunk_summaries,
    )

    if progress:
        progress("최종 요약 생성 중")
    final_response = _make_response(
        client,
        model_name=settings.openai_summary_model,
        prompt=_final_prompt(bundle),
        schema_name="final_summary",
        schema=FINAL_SUMMARY_SCHEMA,
    )
    final_text = getattr(final_response, "output_text", None) or ""
    final_repair_prompt = (
        "다음 응답을 유효한 JSON으로 고쳐 주세요. 스키마를 지키고, "
        "중복 항목은 합치고, 새로운 사실을 추가하지 마세요.\n\n"
        f"응답:\n{final_text}"
    )
    final_summary = _parse_json_with_repair(
        text=final_text,
        repair_prompt=final_repair_prompt,
        client=client,
        model_name=settings.openai_summary_model,
        schema=FINAL_SUMMARY_SCHEMA,
        validator=FinalSummary,
    )

    summary_json_path.write_text(
        json.dumps(final_summary.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    summary_md_path.write_text(render_summary_markdown(final_summary), encoding="utf-8")
    if progress:
        progress("요약 저장 완료")

    return SummarizationResult(
        chunks_bundle=bundle,
        final_summary=final_summary,
        chunks_path=chunks_path,
        summary_json_path=summary_json_path,
        summary_md_path=summary_md_path,
    )
