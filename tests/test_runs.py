import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from service.app import create_app
from service.store import ReportStore
from tools.crypto_tools import CryptoPriceTool


def decode(stream):
    records = []
    for block in stream.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "id" in fields:
            records.append((int(fields["id"]), fields["event"], json.loads(fields["data"])))
    return records


@pytest.mark.asyncio
async def test_streams_live_progress_and_completes_after_disconnect(monkeypatch, tmp_path):
    release_price = asyncio.Event()
    actual_execute = CryptoPriceTool.execute

    async def delayed_price(self, **kwargs):
        await release_price.wait()
        return await actual_execute(self, **kwargs)

    monkeypatch.setattr(CryptoPriceTool, "execute", delayed_price)
    app = create_app(str(tmp_path / "runs.sqlite3"))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post("/research/runs", json={"symbol": "btc", "demo_mode": True})
        assert created.status_code == 202
        run_id = created.json()["run_id"]
        path = f"/research/runs/{run_id}/events"
        messages = asyncio.Queue()
        disconnect = asyncio.Event()
        sent_request = False

        async def receive():
            nonlocal sent_request
            if not sent_request:
                sent_request = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await disconnect.wait()
            return {"type": "http.disconnect"}

        scope = {
            "type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1", "method": "GET", "scheme": "http",
            "path": path, "raw_path": path.encode(), "query_string": b"", "headers": [],
            "client": ("127.0.0.1", 1234), "server": ("test", 80),
        }
        stream = asyncio.create_task(app(scope, receive, messages.put))
        seen = []
        try:
            async with asyncio.timeout(5):
                headers = dict((await messages.get())["headers"])
                assert headers[b"content-type"].startswith(b"text/event-stream")
                assert headers[b"x-accel-buffering"] == b"no"
                while not any(row.get("node") == "collect_price" for _, _, row in seen):
                    seen.extend(decode((await messages.get())["body"].decode()))
            assert seen[-1][2]["phase"] == "started"
            assert (await client.get(f"/research/runs/{run_id}")).json()["state"] == "running"
            assert (await client.get(f"/research/{run_id}")).status_code == 404
        finally:
            disconnect.set()
            try:
                await asyncio.wait_for(stream, 5)
            finally:
                release_price.set()

        cursor = seen[-1][0]
        async with asyncio.timeout(10):
            # Last-Event-ID takes priority over the reload fallback query parameter.
            replay = await client.get(f"{path}?after=0", headers={"Last-Event-ID": str(cursor)})
        remaining = decode(replay.text)
        assert remaining[0][0] == cursor + 1
        assert [seq for seq, _, _ in seen + remaining] == list(range(1, remaining[-1][0] + 1))
        assert remaining[-1][1] == "terminal"
        assert remaining[-1][2]["report_status"] == "demo"
        report = (await client.get(f"/research/{run_id}")).json()
        assert report["run_id"] == run_id and report["status"] == "demo"
        assert {row["node"] for row in report["events"]} == {
            "collect_price", "collect_history", "collect_news", "calculate_indicators", "data_quality"
        }
        assert (await client.get("/research")).json()[0]["run_id"] == run_id
        rows = (await client.get("/research?symbol=btc&status=demo")).json()
        assert len(rows) == 1 and rows[0]["model"] == report["model"] and rows[0]["version"] == 1
        assert (await client.get("/research?symbol=eth")).json() == []
        assert decode((await client.get(f"{path}?after={remaining[-1][0]}")).text) == []
        assert (await client.get(path, headers={"Last-Event-ID": "nope"})).status_code == 400
        assert (await client.get(f"{path}?after=999")).status_code == 400


def test_restart_marks_orphaned_work_interrupted(tmp_path):
    path = str(tmp_path / "runs.sqlite3")
    run_id = str(uuid4())
    store = ReportStore(path)
    store.create_run(run_id, "BTC", True)
    store.start_run(run_id)
    with TestClient(create_app(path)) as client:
        run = client.get(f"/research/runs/{run_id}").json()
        assert run["state"] == "failed" and run["error"] == "interrupted"
        response = client.get(f"/research/runs/{run_id}/events?after=2")
        assert decode(response.text) == [(3, "terminal", run)]
        assert client.get(f"/research/{run_id}").status_code == 404


def test_settings_exposes_configuration_flags_only(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sensitive-test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "your-tavily-key")
    with TestClient(create_app(str(tmp_path / "runs.sqlite3"))) as client:
        response = client.get("/settings")
        assert response.json()["model"]["configured"] is True
        assert response.json()["tavily"]["configured"] is False
        assert "sensitive-test-key" not in response.text
