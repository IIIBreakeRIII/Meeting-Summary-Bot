from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TranscriptSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    start: float
    end: float
    speaker: str | None = None
    text: str


class TranscriptDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_file: str
    language: str
    duration_seconds: float
    segments: list[TranscriptSegment] = Field(default_factory=list)


class KeyDiscussion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str
    summary: str
    source_time_ranges: list[str] = Field(default_factory=list)


class DecisionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    rationale: str
    owner: str
    source_time_ranges: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]


class RiskItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue: str
    impact: str
    mitigation: str
    source_time_ranges: list[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    task: str
    due_date: str
    priority: Literal["high", "medium", "low", "unknown"]
    source_time_ranges: list[str] = Field(default_factory=list)


class OpenQuestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    type: Literal["open_question", "next_agenda"]
    source_time_ranges: list[str] = Field(default_factory=list)


class NotableQuoteItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker: str
    quote: str
    why_it_matters: str
    timestamp: str
    source_time_range: str


class ChunkSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: int
    source_time_range: str
    key_discussions: list[KeyDiscussion] = Field(default_factory=list)
    decisions: list[DecisionItem] = Field(default_factory=list)
    risks_or_issues: list[RiskItem] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    open_questions_and_next_agenda: list[OpenQuestionItem] = Field(default_factory=list)
    notable_quotes: list[NotableQuoteItem] = Field(default_factory=list)


class ChunkSummaryBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audio_file: str
    language: str
    chunk_target_chars: int
    chunks: list[ChunkSummary] = Field(default_factory=list)


class ActionItemsByOwner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner: str
    items: list[ActionItem] = Field(default_factory=list)


class FinalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_title_or_agenda: str
    one_line_summary: str
    overall_summary: str
    key_discussions: list[KeyDiscussion] = Field(default_factory=list)
    decisions: list[DecisionItem] = Field(default_factory=list)
    risks_or_issues: list[RiskItem] = Field(default_factory=list)
    action_items_by_owner: list[ActionItemsByOwner] = Field(default_factory=list)
    open_questions_and_next_agenda: list[OpenQuestionItem] = Field(default_factory=list)
    notable_quotes: list[NotableQuoteItem] = Field(default_factory=list)

