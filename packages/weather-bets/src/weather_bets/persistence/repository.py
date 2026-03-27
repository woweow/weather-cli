from __future__ import annotations

import json
import sqlite3
from typing import Any

from weather_bets.domain.errors import BetSelectionNotFoundError


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
                series_title,
                event_ticker,
                event_date_label,
                market_label,
                side,
                last_price_cents,
                yes_bid_cents,
                yes_ask_cents,
                no_bid_cents,
                no_ask_cents
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                selection["card_index"],
                selection["row_index"],
                selection["city"],
                selection["state"],
                selection["timezone"],
                selection["series_title"],
                selection["event_ticker"],
                selection["event_date_label"],
                selection["market_label"],
                selection["side"],
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
        """
        SELECT
            b.id,
            b.decision_session_id,
            b.card_index,
            b.row_index,
            b.city,
            b.state,
            b.timezone,
            b.series_title,
            b.event_ticker,
            b.event_date_label,
            b.market_label,
            b.side,
            b.last_price_cents,
            b.yes_bid_cents,
            b.yes_ask_cents,
            b.no_bid_cents,
            b.no_ask_cents,
            o.status AS outcome_status,
            o.resolved_at,
            o.actual_temperature_f,
            o.payout_cents,
            o.notes
        FROM bet_selections AS b
        LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
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
) -> list[dict[str, Any]]:
    clauses = []
    params: list[Any] = []
    if status == "open":
        clauses.append("o.id IS NULL")
    elif status == "settled":
        clauses.append("o.id IS NOT NULL")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(
        f"""
        SELECT
            b.id,
            b.decision_session_id,
            s.saved_at,
            s.dashboard_date,
            b.card_index,
            b.row_index,
            b.city,
            b.state,
            b.timezone,
            b.series_title,
            b.event_ticker,
            b.event_date_label,
            b.market_label,
            b.side,
            b.last_price_cents,
            b.yes_bid_cents,
            b.yes_ask_cents,
            b.no_bid_cents,
            b.no_ask_cents,
            o.status AS outcome_status,
            o.resolved_at,
            o.actual_temperature_f,
            o.payout_cents,
            o.notes
        FROM bet_selections AS b
        JOIN decision_sessions AS s ON s.id = b.decision_session_id
        LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
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
    status: str,
    resolved_at: str,
    actual_temperature_f: float | None,
    payout_cents: int | None,
    notes: str | None,
) -> dict[str, Any]:
    selection = connection.execute(
        "SELECT id FROM bet_selections WHERE id = ?",
        (bet_id,),
    ).fetchone()
    if selection is None:
        raise BetSelectionNotFoundError(f"Bet selection {bet_id} was not found.")

    connection.execute(
        """
        INSERT INTO bet_outcomes (
            bet_selection_id,
            status,
            resolved_at,
            actual_temperature_f,
            payout_cents,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(bet_selection_id) DO UPDATE SET
            status = excluded.status,
            resolved_at = excluded.resolved_at,
            actual_temperature_f = excluded.actual_temperature_f,
            payout_cents = excluded.payout_cents,
            notes = excluded.notes
        """,
        (bet_id, status, resolved_at, actual_temperature_f, payout_cents, notes),
    )
    connection.commit()
    row = connection.execute(
        """
        SELECT
            b.id,
            b.decision_session_id,
            s.saved_at,
            s.dashboard_date,
            b.card_index,
            b.row_index,
            b.city,
            b.state,
            b.timezone,
            b.series_title,
            b.event_ticker,
            b.event_date_label,
            b.market_label,
            b.side,
            b.last_price_cents,
            b.yes_bid_cents,
            b.yes_ask_cents,
            b.no_bid_cents,
            b.no_ask_cents,
            o.status AS outcome_status,
            o.resolved_at,
            o.actual_temperature_f,
            o.payout_cents,
            o.notes
        FROM bet_selections AS b
        JOIN decision_sessions AS s ON s.id = b.decision_session_id
        LEFT JOIN bet_outcomes AS o ON o.bet_selection_id = b.id
        WHERE b.id = ?
        """,
        (bet_id,),
    ).fetchone()
    return _row_to_dict(row)


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {key: row[key] for key in row.keys()}
