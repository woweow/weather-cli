from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CitySeriesCandidate:
    city: str
    series_ticker: str
    title: str
    last_updated_ts: str


@dataclass(frozen=True)
class MarketRange:
    ticker: str
    title: str
    label: str
    yes_bid_cents: int | None
    yes_ask_cents: int | None
    no_bid_cents: int | None
    no_ask_cents: int | None
    last_price_cents: int | None
    sort_key: float


@dataclass(frozen=True)
class LadderSnapshot:
    provider: str
    city: str
    series_ticker: str
    series_title: str
    event_ticker: str
    event_date: str
    event_date_label: str
    markets: list[MarketRange]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
