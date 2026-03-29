from __future__ import annotations

import json
import sqlite3
from typing import Any

from weather_bets.domain.errors import BetSelectionNotFoundError


BET_SELECT_SQL = """
    SELECT
        b.id,
        b.decision_session_id,
        s.saved_at,
        s.dashboard_date,
        s.generated_at,
        b.card_index,
        b.row_index,
        b.city,
        b.state,
        b.timezone,
        b.provider,
        b.provider_series_ticker,
        b.provider_event_ticker,
        b.provider_market_ticker,
        b.event_date,
        b.series_title,
        b.event_date_label,
        b.market_label,
        b.side,
        b.stake_cents,
        b.entry_price_cents,
        b.last_price_cents,
        b.yes_bid_cents,
        b.yes_ask_cents,
        b.no_bid_cents,
        b.no_ask_cents,
        o.outcome_status,
        o.resolved_at,
        o.provider_status,
        o.provider_result,
        o.provider_settlement_value_cents,
        o.provider_close_time,
        o.observed_high_temperature_f,
        o.simulated_contract_count,
        o.simulated_gross_payout_cents,
        o.simulated_net_pnl_cents,
        o.notes
    FROM bet_selections AS b
    JOIN decision_sessions AS s ON s.id = b.decision_session_id
    LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
"""


def insert_decision_session(
    connection: sqlite3.Connection,
    *,
    saved_at: str,
    snapshot: dict[str, Any],
    selections: list[dict[str, Any]],
) -> dict[str, Any]:
    cursor = connection.execute(
        """
        INSERT INTO decision_sessions (saved_at, dashboard_date, generated_at, snapshot_json)
        VALUES (?, ?, ?, ?)
        """,
        (
            saved_at,
            snapshot["dashboard_date"],
            snapshot.get("generated_at"),
            json.dumps(snapshot, indent=2),
        ),
    )
    session_id = int(cursor.lastrowid)
    for selection in selections:
        connection.execute(
            """
            INSERT INTO bet_selections (
                decision_session_id,
                card_index,
                row_index,
                city,
                state,
                timezone,
                provider,
                provider_series_ticker,
                provider_event_ticker,
                provider_market_ticker,
                event_date,
                series_title,
                event_date_label,
                market_label,
                side,
                stake_cents,
                entry_price_cents,
                last_price_cents,
                yes_bid_cents,
                yes_ask_cents,
                no_bid_cents,
                no_ask_cents
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                selection["card_index"],
                selection["row_index"],
                selection["city"],
                selection["state"],
                selection["timezone"],
                selection["provider"],
                selection["provider_series_ticker"],
                selection["provider_event_ticker"],
                selection["provider_market_ticker"],
                selection["event_date"],
                selection["series_title"],
                selection["event_date_label"],
                selection["market_label"],
                selection["side"],
                selection["stake_cents"],
                selection["entry_price_cents"],
                selection["last_price_cents"],
                selection["yes_bid_cents"],
                selection["yes_ask_cents"],
                selection["no_bid_cents"],
                selection["no_ask_cents"],
            ),
        )
    connection.commit()
    return get_session_summary(connection, session_id)


def get_session_summary(connection: sqlite3.Connection, session_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            s.id,
            s.saved_at,
            s.dashboard_date,
            s.generated_at,
            COUNT(b.id) AS selection_count,
            COALESCE(SUM(CASE WHEN o.id IS NOT NULL THEN 1 ELSE 0 END), 0) AS settled_count
        FROM decision_sessions AS s
        LEFT JOIN bet_selections AS b ON b.decision_session_id = s.id
        LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
        WHERE s.id = ?
        GROUP BY s.id
        """,
        (session_id,),
    ).fetchone()
    return _row_to_dict(row)


def list_sessions(connection: sqlite3.Connection, *, limit: int) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT
            s.id,
            s.saved_at,
            s.dashboard_date,
            s.generated_at,
            COUNT(b.id) AS selection_count,
            COALESCE(SUM(CASE WHEN o.id IS NOT NULL THEN 1 ELSE 0 END), 0) AS settled_count
        FROM decision_sessions AS s
        LEFT JOIN bet_selections AS b ON b.decision_session_id = s.id
        LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
        GROUP BY s.id
        ORDER BY s.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def get_session_detail(connection: sqlite3.Connection, session_id: int) -> dict[str, Any]:
    session = connection.execute(
        """
        SELECT id, saved_at, dashboard_date, generated_at, snapshot_json
        FROM decision_sessions
        WHERE id = ?
        """,
        (session_id,),
    ).fetchone()
    if session is None:
        raise BetSelectionNotFoundError(f"Decision session {session_id} was not found.")

    bets = connection.execute(
        f"""
        {BET_SELECT_SQL}
        WHERE b.decision_session_id = ?
        ORDER BY b.id ASC
        """,
        (session_id,),
    ).fetchall()

    return {
        "id": session["id"],
        "saved_at": session["saved_at"],
        "dashboard_date": session["dashboard_date"],
        "generated_at": session["generated_at"],
        "snapshot": json.loads(session["snapshot_json"]),
        "bets": [_row_to_dict(row) for row in bets],
    }


def list_bets(
    connection: sqlite3.Connection,
    *,
    limit: int,
    status: str | None,
    provider: str | None = None,
    bet_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if status == "open":
        clauses.append("o.id IS NULL")
    elif status == "settled":
        clauses.append("o.id IS NOT NULL")
    if provider:
        clauses.append("b.provider = ?")
        params.append(provider)
    if bet_ids:
        placeholders = ",".join("?" for _ in bet_ids)
        clauses.append(f"b.id IN ({placeholders})")
        params.extend(bet_ids)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        {BET_SELECT_SQL}
        {where_sql}
        ORDER BY b.id DESC
        LIMIT ?
        """,
        [*params, limit],
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def upsert_outcome(
    connection: sqlite3.Connection,
    *,
    bet_id: int,
    outcome_status: str,
    resolved_at: str,
    provider_status: str | None,
    provider_result: str | None,
    provider_settlement_value_cents: int | None,
    provider_close_time: str | None,
    observed_high_temperature_f: float | None,
    simulated_contract_count: str | None,
    simulated_gross_payout_cents: int | None,
    simulated_net_pnl_cents: int | None,
    notes: str | None,
) -> dict[str, Any]:
    selection = connection.execute("SELECT id FROM bet_selections WHERE id = ?", (bet_id,)).fetchone()
    if selection is None:
        raise BetSelectionNotFoundError(f"Bet selection {bet_id} was not found.")

    connection.execute(
        """
        INSERT INTO bet_outcomes (
            bet_selection_id,
            outcome_status,
            resolved_at,
            provider_status,
            provider_result,
            provider_settlement_value_cents,
            provider_close_time,
            observed_high_temperature_f,
            simulated_contract_count,
            simulated_gross_payout_cents,
            simulated_net_pnl_cents,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bet_selection_id) DO UPDATE SET
            outcome_status = excluded.outcome_status,
            resolved_at = excluded.resolved_at,
            provider_status = excluded.provider_status,
            provider_result = excluded.provider_result,
            provider_settlement_value_cents = excluded.provider_settlement_value_cents,
            provider_close_time = excluded.provider_close_time,
            observed_high_temperature_f = excluded.observed_high_temperature_f,
            simulated_contract_count = excluded.simulated_contract_count,
            simulated_gross_payout_cents = excluded.simulated_gross_payout_cents,
            simulated_net_pnl_cents = excluded.simulated_net_pnl_cents,
            notes = excluded.notes
        """,
        (
            bet_id,
            outcome_status,
            resolved_at,
            provider_status,
            provider_result,
            provider_settlement_value_cents,
            provider_close_time,
            observed_high_temperature_f,
            simulated_contract_count,
            simulated_gross_payout_cents,
            simulated_net_pnl_cents,
            notes,
        ),
    )
    connection.commit()
    row = connection.execute(
        f"""
        {BET_SELECT_SQL}
        WHERE b.id = ?
        """,
        (bet_id,),
    ).fetchone()
    return _row_to_dict(row)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}
