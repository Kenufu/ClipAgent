import json
import sqlite3
from datetime import datetime, timezone

from .config import DATABASE, JOBS


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    JOBS.mkdir(parents=True, exist_ok=True)
    with _connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                phase TEXT NOT NULL,
                instruction TEXT NOT NULL,
                options_json TEXT NOT NULL,
                assets_json TEXT NOT NULL,
                transcript_json TEXT NOT NULL,
                timeline_json TEXT NOT NULL,
                report_json TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 0,
                error TEXT
            )"""
        )
        db.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL REFERENCES jobs(id),
                at TEXT NOT NULL,
                phase TEXT NOT NULL,
                message TEXT NOT NULL
            )"""
        )


def create_job(job_id, instruction, options, assets):
    now = _now()
    with _connect() as db:
        db.execute(
            """INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                job_id, now, now, "queued", "queued", instruction,
                json.dumps(options), json.dumps(assets), "[]", "[]", "{}", 0, None,
            ),
        )
    event(job_id, "queued", "Job created")


def update_job(job_id, **fields):
    allowed = {"status", "phase", "instruction", "options", "assets", "transcript", "timeline", "report", "version", "error"}
    if not fields or set(fields) - allowed:
        raise ValueError("Invalid job fields")
    values = {}
    for key, value in fields.items():
        column = f"{key}_json" if key in {"options", "assets", "transcript", "timeline", "report"} else key
        values[column] = json.dumps(value) if column.endswith("_json") else value
    values["updated_at"] = _now()
    assignments = ", ".join(f"{key} = ?" for key in values)
    with _connect() as db:
        db.execute(f"UPDATE jobs SET {assignments} WHERE id = ?", (*values.values(), job_id))


def event(job_id, phase, message):
    with _connect() as db:
        db.execute(
            "INSERT INTO events (job_id, at, phase, message) VALUES (?, ?, ?, ?)",
            (job_id, _now(), phase, message),
        )
    update_job(job_id, phase=phase)


def get_job(job_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        events = db.execute(
            "SELECT at, phase, message FROM events WHERE job_id = ? ORDER BY id", (job_id,)
        ).fetchall()
    result = dict(row)
    for name in ("options", "assets", "transcript", "timeline", "report"):
        result[name] = json.loads(result.pop(f"{name}_json"))
    result["events"] = [dict(item) for item in events]
    return result


def list_jobs(limit=20):
    with _connect() as db:
        rows = db.execute(
            "SELECT id, created_at, updated_at, status, phase, instruction FROM jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
