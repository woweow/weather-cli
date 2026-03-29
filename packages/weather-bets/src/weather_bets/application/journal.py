from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from weather_bets.domain.errors import BetSelectionNotFoundError
from weather_bets.domain.simulator import simulate_pnl
from weather_bets.domain.snapshot import extract_selected_bets, normalize_dashboard_snapshot
from weather_bets.paths import DEFAULT_DB_PATH
from weather_bets.persistence.connection import open_connection
from weather_bets.persistence.migrations import SCHEMA_VERSION, initialize_schema, reset_database_file
from weather_bets.persistence.repository import (
    get_session_detail,
    insert_decision_session,
    list_bets,
    list_sessions,
    upsert_outcome,
)


def initialize_database(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reset: bool = False,
) -> dict[str, Any]:
    if reset:
        reset_database_file(db_path)
    with open_connection(db_path) as connection:
        version = initialize_schema(connection)
    return {"db_path": str(db_path), "schema_version": version, "reset": reset}


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
        initialize_schema(connection)
        summary = insert_decision_session(
            connection,
            saved_at=save_time,
            snapshot=snapshot,
            selections=selections,
        )
    return {**summary, "db_path": str(db_path), "schema_version": SCHEMA_VERSION}


def list_decision_sessions(*, db_path: Path = DEFAULT_DB_PATH, limit: int = 20) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        initialize_schema(connection)
        sessions = list_sessions(connection, limit=limit)
    return {"db_path": str(db_path), "schema_version": SCHEMA_VERSION, "sessions": sessions}


def show_decision_session(session_id: int, *, db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        initialize_schema(connection)
        session = get_session_detail(connection, session_id)
    return {"db_path": str(db_path), "schema_version": SCHEMA_VERSION, **session}


def list_bet_selections(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    limit: int = 20,
    status: str | None = None,
    provider: str | None = None,
    bet_ids: list[int] | None = None,
) -> dict[str, Any]:
    with open_connection(db_path) as connection:
        initialize_schema(connection)
        bets = list_bets(connection, limit=limit, status=status, provider=provider, bet_ids=bet_ids)
    return {"db_path": str(db_path), "schema_version": SCHEMA_VERSION, "bets": bets}


def settle_bet_selection(
    bet_id: int,
    *,
    status: str,
    db_path: Path = DEFAULT_DB_PATH,
    resolved_at: str | None = None,
    observed_high_temperature_f: float | None = None,
    payout_cents: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    return resolve_bet_selection(
        bet_id,
        outcome_status=status,
        db_path=db_path,
        resolved_at=resolved_at,
        observed_high_temperature_f=observed_high_temperature_f,
        payout_cents=payout_cents,
        notes=notes,
    )


def resolve_bet_selection(
    bet_id: int,
    *,
    outcome_status: str,
    db_path: Path = DEFAULT_DB_PATH,
    resolved_at: str | None = None,
    provider_status: str | None = None,
    provider_result: str | None = None,
    provider_settlement_value_cents: int | None = None,
    provider_close_time: str | None = None,
    observed_high_temperature_f: float | None = None,
    payout_cents: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    effective_resolved_at = resolved_at or datetime.now(timezone.utc).isoformat()
    with open_connection(db_path) as connection:
        initialize_schema(connection)
        selection_rows = list_bets(connection, limit=1, status=None, provider=None, bet_ids=[bet_id])
        if not selection_rows:
            raise BetSelectionNotFoundError(f"Bet selection {bet_id} was not found.")
        selection = selection_rows[0]
        simulation = simulate_pnl(
            stake_cents=selection["stake_cents"],
            entry_price_cents=selection["entry_price_cents"],
            outcome_status=outcome_status,
            payout_override_cents=payout_cents,
        )
        bet = upsert_outcome(
            connection,
            bet_id=bet_id,
            outcome_status=outcome_status,
            resolved_at=effective_resolved_at,
            provider_status=provider_status,
            provider_result=provider_result,
            provider_settlement_value_cents=provider_settlement_value_cents,
            provider_close_time=provider_close_time,
            observed_high_temperature_f=observed_high_temperature_f,
            simulated_contract_count=simulation["simulated_contract_count"],
            simulated_gross_payout_cents=simulation["simulated_gross_payout_cents"],
            simulated_net_pnl_cents=simulation["simulated_net_pnl_cents"],
            notes=notes,
        )
    return {"db_path": str(db_path), "schema_version": SCHEMA_VERSION, "bet": bet}
