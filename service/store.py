"""SQLite report storage. Snapshot data is persisted with the validated result."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing, contextmanager
from pathlib import Path

from agents.models import AnalysisResult, ReportStatus
from tools.base import utc_now

ACTIVE_STATES = {"queued", "running"}


class ReportStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS reports (
                run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
                symbol TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL
            )""")
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, demo_mode INTEGER NOT NULL,
                    state TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    report_status TEXT, error TEXT, cursor INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS research_events (
                    run_id TEXT NOT NULL, seq INTEGER NOT NULL, kind TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY (run_id, seq), FOREIGN KEY (run_id) REFERENCES research_runs (run_id)
                );
            """)

    @contextmanager
    def _connect(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            yield connection

    @staticmethod
    def _save(connection, result: AnalysisResult):
        connection.execute(
            "INSERT INTO reports VALUES (?, ?, ?, ?, ?)",
            (result.run_id, result.created_at, result.symbol, result.status, result.model_dump_json()),
        )

    def save(self, result: AnalysisResult) -> None:
        # INSERT deliberately refuses to overwrite a report's data snapshot.
        with self._connect() as connection:
            self._save(connection, result)

    def get(self, run_id: str) -> AnalysisResult | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM reports WHERE run_id = ?", (run_id,)
            ).fetchone()
        return AnalysisResult.model_validate_json(row[0]) if row else None

    def list(
        self,
        limit: int = 20,
        offset: int = 0,
        *,
        symbol: str | None = None,
        status: ReportStatus | None = None,
    ) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT run_id, created_at, symbol, status,
                          json_extract(payload, '$.provider') AS provider,
                          json_extract(payload, '$.model') AS model,
                          coalesce(json_extract(payload, '$.version'), 1) AS version
                   FROM reports WHERE (? IS NULL OR symbol = ?) AND (? IS NULL OR status = ?)
                   ORDER BY created_at DESC, run_id DESC LIMIT ? OFFSET ?""",
                (symbol, symbol.upper() if symbol else None, status, status, limit, offset),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _get_run(connection, run_id: str) -> dict | None:
        row = connection.execute("SELECT * FROM research_runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row, demo_mode=bool(row["demo_mode"])) if row else None

    @classmethod
    def _event(cls, connection, run_id: str, kind: str, data: dict | None = None) -> dict:
        connection.execute(
            "UPDATE research_runs SET cursor = cursor + 1, updated_at = ? WHERE run_id = ?",
            (utc_now(), run_id),
        )
        run = cls._get_run(connection, run_id)
        connection.execute(
            "INSERT INTO research_events VALUES (?, ?, ?, ?)",
            (run_id, run["cursor"], kind, json.dumps(run if data is None else data)),
        )
        return run

    def create_run(self, run_id: str, symbol: str, demo_mode: bool) -> dict:
        now = utc_now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO research_runs (run_id, symbol, demo_mode, state, created_at, updated_at)
                   VALUES (?, ?, ?, 'queued', ?, ?)""",
                (run_id, symbol, demo_mode, now, now),
            )
            return self._event(connection, run_id, "run")

    def start_run(self, run_id: str) -> bool:
        with self._connect() as connection:
            updated = connection.execute(
                "UPDATE research_runs SET state = 'running' WHERE run_id = ? AND state = 'queued'",
                (run_id,),
            )
            if not updated.rowcount:
                return False
            self._event(connection, run_id, "run")
            return True

    def record_progress(self, run_id: str, data: dict) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            run = self._get_run(connection, run_id)
            if run and run["state"] == "running":
                self._event(connection, run_id, "node", data)

    def finish_run(self, run_id: str, result: AnalysisResult | None = None, error: str | None = None):
        if result is not None and result.run_id != run_id:
            raise ValueError("Report run ID does not match the queued run")
        with self._connect() as connection:
            updated = connection.execute(
                """UPDATE research_runs SET state = ?, report_status = ?, error = ?
                   WHERE run_id = ? AND state IN ('queued', 'running')""",
                ("finished" if result else "failed", result.status if result else None, error, run_id),
            )
            if updated.rowcount:
                if result is not None:
                    self._save(connection, result)
                self._event(connection, run_id, "terminal")

    def interrupt_runs(self) -> None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT run_id FROM research_runs WHERE state IN ('queued', 'running')"
            ).fetchall()
            for (run_id,) in rows:
                connection.execute(
                    "UPDATE research_runs SET state = 'failed', error = 'interrupted' WHERE run_id = ?",
                    (run_id,),
                )
                self._event(connection, run_id, "terminal")

    def get_run(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            return self._get_run(connection, run_id)

    def events_after(self, run_id: str, cursor: int) -> tuple[dict | None, list[tuple]]:
        with self._connect() as connection:
            connection.execute("BEGIN")
            run = self._get_run(connection, run_id)
            rows = connection.execute(
                """SELECT seq, kind, data FROM research_events
                   WHERE run_id = ? AND seq > ? ORDER BY seq LIMIT 100""",
                (run_id, cursor),
            ).fetchall()
            return run, [tuple(row) for row in rows]
