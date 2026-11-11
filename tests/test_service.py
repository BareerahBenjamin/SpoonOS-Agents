import json
import sqlite3
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from spoon_ai.chat import ChatBot

from agents.graph_agent import CryptoAnalysisGraph
from agents.models import AnalysisResult, ModelReport
from service.app import create_app
from service.store import ReportStore
from tools.base import utc_now


def result_fixture():
    return AnalysisResult(
        run_id=str(uuid4()),
        snapshot_id=str(uuid4()),
        created_at=utc_now(),
        symbol="BTC",
        provider="openai",
        model="gpt-4.1-mini",
        status="completed",
        recommendation="HOLD",
        reasoning="快照说明",
        model_report=ModelReport(
            recommendation="HOLD",
            summary="摘要",
            reasoning="快照说明",
            evidence_ids=["price"],
            limitations=[],
        ),
        data={"price_data": {"current_price": 12345}},
        evidence=[{"id": "price"}],
    )


def test_store_reopens_and_refuses_snapshot_overwrite(tmp_path):
    path = str(tmp_path / "research.sqlite3")
    result = result_fixture()
    ReportStore(path).save(result)
    assert ReportStore(path).get(result.run_id) == result
    assert ReportStore(path).list()[0]["run_id"] == result.run_id
    with pytest.raises(sqlite3.IntegrityError):
        ReportStore(path).save(result)


def test_research_api_saves_and_retrieves_snapshot(monkeypatch, tmp_path):
    result = result_fixture()
    monkeypatch.setattr(CryptoAnalysisGraph, "arun", AsyncMock(return_value=result))
    path = str(tmp_path / "research.sqlite3")
    with TestClient(create_app(path)) as client:
        assert client.get("/health").json()["sdk"] == "spoon-ai-sdk"
        created = client.post("/research", json={"symbol": "btc"})
        assert created.status_code == 201
        assert client.get(f"/research/{result.run_id}").json() == created.json()
        assert client.get("/research").json()[0]["run_id"] == result.run_id
        assert client.get(f"/research/{uuid4()}").status_code == 404
        assert client.post("/research", json={"symbol": "../btc"}).status_code == 422
    with TestClient(create_app(path)) as client:
        assert client.get(f"/research/{result.run_id}").json()["snapshot_id"] == result.snapshot_id


def test_followup_uses_saved_prices_and_checks_citations(monkeypatch, tmp_path):
    result = result_fixture()
    path = str(tmp_path / "research.sqlite3")
    ReportStore(path).save(result)
    ask = AsyncMock(
        return_value=json.dumps({"answer": "根据快照价格 12345", "evidence_ids": ["price"]})
    )
    monkeypatch.setattr(ChatBot, "ask", ask)
    with TestClient(create_app(path)) as client:
        response = client.post(
            f"/research/{result.run_id}/questions", json={"question": "为什么？"}
        )
        assert response.status_code == 200
        prompt = ask.call_args.kwargs["messages"][0]["content"]
        assert "12345" in prompt and result.snapshot_id in prompt
        ask.return_value = json.dumps({"answer": "Bad citation", "evidence_ids": ["invented"]})
        assert (
            client.post(
                f"/research/{result.run_id}/questions", json={"question": "why"}
            ).status_code
            == 502
        )


def test_missing_model_configuration_returns_service_error(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY")
    with TestClient(create_app(str(tmp_path / "research.sqlite3"))) as client:
        response = client.post("/research", json={"symbol": "BTC"})
        assert response.status_code == 503
        assert "OPENAI_API_KEY" in response.json()["detail"]
