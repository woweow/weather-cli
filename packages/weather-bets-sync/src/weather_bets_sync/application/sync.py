from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from kalshi_weather_markets_cli.adapters.client import KalshiPublicClient
from weather_bets.application import list_bet_selections, resolve_bet_selection
from weather_bets.domain.simulator import simulate_pnl
from weather_bets.paths import DEFAULT_DB_PATH
from weather_cli.adapters.geocoding import OpenMeteoGeocoder
from weather_cli.adapters.http import JsonHttpClient
from weather_cli.adapters.noaa import NoaaApi
from weather_cli.application import WeatherService
from weather_cli.application.errors import WeatherCliError


def sync_open_kalshi_bets(
    *,
    db_path: Path = DEFAULT_DB_PATH,
    dry_run: bool = False,
    limit: int = 100,
    bet_ids: list[int] | None = None,
    client: KalshiPublicClient | None = None,
    weather_service: WeatherService | None = None,
) -> dict[str, Any]:
    client = client or KalshiPublicClient()
    weather_service = weather_service or _build_weather_service()
    open_bets = list_bet_selections(
        db_path=db_path,
        limit=limit,
        status="open",
        provider="kalshi",
        bet_ids=bet_ids,
    )["bets"]

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for bet in open_bets:
        grouped[bet["provider_event_ticker"]].append(bet)

    settled: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    dry_run_rows: list[dict[str, Any]] = []

    for event_ticker, bets in grouped.items():
        event_markets, provider_status = _fetch_settled_event_markets(client, event_ticker)
        if not event_markets:
            skipped.extend(
                {
                    "bet_id": bet["id"],
                    "provider_event_ticker": event_ticker,
                    "reason": "provider event is not settled yet",
                }
                for bet in bets
            )
            continue

        markets_by_ticker = {market["ticker"]: market for market in event_markets}
        observed_high = _fetch_observed_high(weather_service, bets[0], skipped)
        for bet in bets:
            market = markets_by_ticker.get(bet["provider_market_ticker"])
            if market is None:
                skipped.append(
                    {
                        "bet_id": bet["id"],
                        "provider_market_ticker": bet["provider_market_ticker"],
                        "reason": "provider market was not returned for the settled event",
                    }
                )
                continue

            outcome_status = _derive_outcome_status(bet["side"], market.get("result"))
            provider_settlement_value_cents = _dollars_to_cents(market.get("settlement_value_dollars"))
            if dry_run:
                dry_run_rows.append(
                    {
                        "bet_id": bet["id"],
                        "provider_market_ticker": bet["provider_market_ticker"],
                        "outcome_status": outcome_status,
                        "provider_status": market.get("status") or provider_status,
                        "provider_result": market.get("result"),
                        "provider_settlement_value_cents": provider_settlement_value_cents,
                        "provider_close_time": market.get("close_time"),
                        "observed_high_temperature_f": observed_high,
                        **simulate_pnl(
                            stake_cents=bet["stake_cents"],
                            entry_price_cents=bet["entry_price_cents"],
                            outcome_status=outcome_status,
                        ),
                    }
                )
                continue

            resolved = resolve_bet_selection(
                bet["id"],
                outcome_status=outcome_status,
                db_path=db_path,
                provider_status=market.get("status") or provider_status,
                provider_result=market.get("result"),
                provider_settlement_value_cents=provider_settlement_value_cents,
                provider_close_time=market.get("close_time"),
                observed_high_temperature_f=observed_high,
                notes="Synced from Kalshi public market data.",
            )
            settled.append(resolved["bet"])

    return {
        "db_path": str(db_path),
        "provider": "kalshi",
        "dry_run": dry_run,
        "requested_bet_ids": bet_ids or [],
        "open_bet_count": len(open_bets),
        "settled_count": len(settled),
        "settled": settled,
        "dry_run_rows": dry_run_rows,
        "skipped": skipped,
    }


def _fetch_settled_event_markets(
    client: KalshiPublicClient,
    event_ticker: str,
) -> tuple[list[dict[str, Any]], str | None]:
    for status in ("settled", "determined"):
        markets = client.get_markets(event_ticker=event_ticker, status=status, limit=200)
        if markets:
            return markets, status
    return [], None


def _fetch_observed_high(
    weather_service: WeatherService,
    bet: dict[str, Any],
    skipped: list[dict[str, Any]],
) -> float | None:
    place = f"{bet['city']},{bet['state']}"
    try:
        observed = weather_service.fetch_observed_high_for_date(place, bet["event_date"])
    except WeatherCliError as exc:
        skipped.append(
            {
                "bet_id": bet["id"],
                "provider_market_ticker": bet["provider_market_ticker"],
                "reason": f"observed high unavailable: {exc}",
            }
        )
        return None
    return observed["observed_high_temperature_f"]


def _build_weather_service() -> WeatherService:
    http_client = JsonHttpClient(user_agent="weather-bets-sync/0.1")
    return WeatherService(
        geocoder=OpenMeteoGeocoder(http_client),
        noaa_api=NoaaApi(http_client),
    )


def _derive_outcome_status(side: str, provider_result: str | None) -> str:
    if provider_result not in {"yes", "no"}:
        return "void"
    if side == provider_result:
        return "won"
    return "lost"


def _dollars_to_cents(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(round(float(value) * 100))
