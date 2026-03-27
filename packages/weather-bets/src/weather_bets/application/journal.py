from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from weather_bets.domain.snapshot import extract_selected_bets, normalize_dashboard_snapshot
from weather_bets.paths import DEFAULT_DB_PATH
from weather_bets.persistence.connection import open_connection
from weather_bets.persistence.migrations import apply_migrations
from weather_bets.persistence.repository import (
    get_session_detail,
    insert_decision_session,
    list_bets,
    list_sessions,
    upsert_outcome,
)


def initialize_database(*, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        version = apply_migrations(connection)
    return {"db_path": str(db_path), "schema_version": version}


def record_decision_session(
    payload: dict[str, Any],
    *,
    db_path: Path = DEFAULT_DB_PATH,
    saved_at: str | None = None,
) -> dict[str, Any]:
    snapshot = normalize_dashboard_snapshot(payload)
    selections = extract_selected_bets(snapshot)
    save_time = saved_at or datetime.now(timezone.utc).isoformat()
    with open_connection(db_path) as connection:
        apply_migrations(connection)
        summary = insert_decision_session(
            connection,
            saved_at=save_time,
            snapshot=snapshot,
            selections=selections,
        )
    return {**summary, "db_path": str(db_path)}


def list_decision_sessions(*, db_path: Path = DEFAULT_DB_PATH, limit: int = 20) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        apply_migrations(connection)
        sessions = list_sessions(connection, limit=limit)
    return {"db_path": str(db_path), "sessions": sessions}


def show_decision_session(session_id: int, *, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        apply_migrations(connection)
        session = get_session_detail(connection, session_id)
    return {"db_path": str(db_path), **session}


def list_bet_selections(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    limit: int = 20,
    status: str | None = None,
) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        apply_migrations(connection)
        bets = list_bets(connection, limit=limit, status=status)
    return {"db_path": str(db_path), "bets": bets}


def settle_bet_selection(
    bet_id: int,
    *,
    status: str,
    db_path: Path = DEFAULT_DB_PATH,
    resolved_at: str | None = None,
    actual_temperature_f: float | None = None,
    payout_cents: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    effective_resolved_at = resolved_at or datetime.now(timezone.utc).isoformat()
    with open_connection(db_path) as connection:
        apply_migrations(connection)
        bet = upsert_outcome(
            connection,
            bet_id=bet_id,
            status=status,
            resolved_at=effective_resolved_at,
            actual_temperature_f=actual_temperature_f,
            payout_cents=payout_cents,
            notes=notes,
        )
    return {"db_path": str(db_path), "bet": bet}
