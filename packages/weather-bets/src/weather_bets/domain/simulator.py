from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from weather_bets.domain.errors import SnapshotValidationError


USD_CENTS = Decimal("100")
CONTRACT_PRECISION = Decimal("0.0001")


def normalize_optional_usd_string(value: object, *, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    cents = parse_usd_to_cents(value, field_name=field_name)
    dollars = (Decimal(cents) / USD_CENTS).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{dollars:.2f}"


def parse_usd_to_cents(value: object, *, field_name: str) -> int:
    decimal_value = _coerce_decimal(value, field_name=field_name)
    if decimal_value <= 0:
        raise SnapshotValidationError(f"{field_name} must be greater than zero when present.")
    cents = (decimal_value * USD_CENTS).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if cents != decimal_value * USD_CENTS:
        raise SnapshotValidationError(f"{field_name} must use at most two decimal places.")
    return int(cents)


def simulate_pnl(
    *,
    stake_cents: int | None,
    entry_price_cents: int | None,
    outcome_status: str,
    payout_override_cents: int | None = None,
) -> dict[str, int | str | None]:
    if stake_cents is None or entry_price_cents is None or entry_price_cents <= 0:
        return {
            "simulated_contract_count": None,
            "simulated_gross_payout_cents": payout_override_cents,
            "simulated_net_pnl_cents": _net_from_override(stake_cents, payout_override_cents),
        }

    contracts = (Decimal(stake_cents) / Decimal(entry_price_cents)).quantize(
        CONTRACT_PRECISION,
        rounding=ROUND_HALF_UP,
    )

    if payout_override_cents is not None:
        gross_cents = payout_override_cents
    elif outcome_status == "won":
        gross_cents = int(
            (contracts * USD_CENTS).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        )
    elif outcome_status == "lost":
        gross_cents = 0
    elif outcome_status == "void":
        gross_cents = stake_cents
    else:
        raise ValueError(f"Unsupported outcome status: {outcome_status}")

    return {
        "simulated_contract_count": f"{contracts:.4f}",
        "simulated_gross_payout_cents": gross_cents,
        "simulated_net_pnl_cents": gross_cents - stake_cents,
    }


def _coerce_decimal(value: object, *, field_name: str) -> Decimal:
    try:
        text = str(value).strip()
        if not text:
            raise SnapshotValidationError(f"{field_name} must be a decimal USD amount when present.")
        return Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise SnapshotValidationError(f"{field_name} must be a decimal USD amount when present.") from exc


def _net_from_override(stake_cents: int | None, payout_override_cents: int | None) -> int | None:
    if stake_cents is None or payout_override_cents is None:
        return None
    return payout_override_cents - stake_cents
