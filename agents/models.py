"""Validated report and evidence contracts for the research workbench."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Recommendation = Literal["BUY", "HOLD", "SELL"]
ReportStatus = Literal["completed", "partial", "unavailable", "failed", "demo"]


class ModelReport(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recommendation: Recommendation
    summary: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    limitations: list[str]


class AnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    snapshot_id: str
    version: int = 1
    created_at: str
    symbol: str
    provider: str
    model: str
    status: ReportStatus
    recommendation: Recommendation | None = None
    rule_signal: Recommendation | None = None
    confidence: None = None  # Deprecated compatibility field, never a fabricated probability.
    reasoning: str
    model_report: ModelReport | None = None
    disagreement: bool = False
    limitations: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    data: dict
