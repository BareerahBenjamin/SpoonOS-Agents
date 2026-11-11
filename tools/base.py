"""SpoonOS tools with validated inputs and a synchronous compatibility API."""

import asyncio
import os
from datetime import datetime, timezone
from typing import ClassVar

import requests
from pydantic import BaseModel, ConfigDict, Field, field_validator
from spoon_ai.tools.base import BaseTool


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def demo_enabled(value: bool | None) -> bool:
    if value is not None:
        return value
    raw = os.getenv("DEMO_MODE", "false").lower()
    if raw not in {"true", "false"}:
        raise ValueError("DEMO_MODE must be true or false")
    return raw == "true"


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DataQualityError(ValueError):
    """A safe, application-authored explanation of missing or invalid source data."""


class AssetInput(ToolInput):
    symbol: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9-]+$")

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.upper()


class ResearchTool(BaseTool):
    input_model: ClassVar[type[BaseModel]]
    demo_mode: bool = Field(default_factory=lambda: demo_enabled(None), exclude=True)

    def run(self, **kwargs) -> dict:
        args = self.input_model.model_validate(kwargs)
        return self._run(**args.model_dump())

    async def execute(self, **kwargs) -> dict:
        return await asyncio.to_thread(self.run, **kwargs)

    def _run(self, **kwargs) -> dict:
        raise NotImplementedError


def metadata(status: str, source: str, *, updated_at=None, error=None) -> dict:
    return {
        "status": status,
        "source": source,
        "fetched_at": utc_now(),
        "updated_at": updated_at,
        "error": error,
    }


def request_json(method: str, url: str, **kwargs):
    """Retry transient collection failures once; callers expose explicit unavailability."""
    for attempt in range(2):
        try:
            response = requests.request(method, url, timeout=(5, 15), **kwargs)
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt:
                raise
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if attempt or (code != 429 and code < 500):
                raise


def failure_reason(exc: Exception) -> str:
    # HTTP exception strings may contain authenticated URLs or request details.
    if isinstance(exc, DataQualityError):
        return str(exc)
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        return f"Upstream HTTP {exc.response.status_code}"
    if isinstance(exc, requests.Timeout):
        return "Upstream request timed out"
    if isinstance(exc, requests.RequestException):
        return "Upstream connection failed"
    return "Invalid or incomplete upstream data"
