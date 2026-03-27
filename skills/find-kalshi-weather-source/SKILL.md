---
name: find-kalshi-weather-source
description: Find the exact NOAA/NWS `.gov` source Kalshi uses for a city's weather market. Use when asked which official weather report Kalshi uses for a city such as Seattle, Los Angeles, NYC, or Miami, and when you need the exact market-rule verification link rather than a guessed station code.
---

# Find Kalshi Weather Source

Use this skill when the user wants the exact government source behind a Kalshi weather market.

For daily temperature markets, the authoritative answer is the link shown in the market's `Market Rules` under `Outcome verified from`. Do not infer the URL from the city name alone.

## Workflow

1. Find any Kalshi market page for the target city and weather contract.
2. Open the market page and inspect `Market Rules`.
3. Read the `Outcome verified from` link.
4. Return that exact URL as the source Kalshi uses.
5. Open the NOAA/NWS link and confirm the product identifier and station name so you can explain what it is.

## Practical Steps

### 1. Find a market page

Search Kalshi for the city and contract type. For a daily high temperature market, search terms like these usually work:

- `site:kalshi.com/markets "highest temperature in Seattle" Kalshi`
- `site:kalshi.com/markets "Seattle maximum temperature daily" Kalshi`
- `site:kalshi.com/markets "highest temperature in Los Angeles" Kalshi`

Any settled or live market for that city is fine. The rule link is typically stable across the series.

### 2. Inspect the rules on the market page

Kalshi renders market details client-side, so plain `curl` may miss the rule text. Prefer a browser tool if available.

On the page:

- open `Market Rules`
- find the sentence starting with `Outcome verified from`
- copy the linked `.gov` URL exactly

That link is the answer.

### 3. Confirm the NOAA/NWS page

Open the linked URL and verify:

- it is a `forecast.weather.gov/product.php?...product=CLI...` page for daily climate reports
- the product code shown on the page, such as `CLILAX` or `CLISEA`
- the station name in the page body, such as `LOS ANGELES AIRPORT` or `SEATTLE-TACOMA WA AIRPORT`

This confirmation catches metro-area edge cases where multiple nearby CLI products exist.

## Important Cautions

- Do not guess from the city name, airport code, or forecast office code.
- Do not assume `issuedby` matches the NWS `site` parameter.
- Do not assume the broad city office summary is the same as the station used by Kalshi.

Seattle is the canonical example:

- `issuedby=SEA` is Kalshi's linked source for Seattle daily high temperature markets
- `issuedby=SEW` is a different Seattle-area CLI product
- the exact Kalshi-linked page is the one to trust

## Fallbacks

If search results are weak:

1. Search Kalshi's market pages for the city.
2. Open a likely city weather market with a browser tool.
3. Read the rule link directly from `Outcome verified from`.

If the contract is not a daily temperature market:

- still inspect `Market Rules`
- do not assume the source is `CLI`
- return whatever official NWS source Kalshi actually links

## Output Format

Give the user:

- the exact URL
- the product identifier if visible, like `CLISEA`
- a short note describing the station or report name

Example:

- `Seattle: https://forecast.weather.gov/product.php?site=SEW&product=CLI&issuedby=SEA`
- `This is CLISEA, the Seattle-Tacoma Airport climate summary.`
