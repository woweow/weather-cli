# weather-cli

Small Python CLI for querying NOAA `api.weather.gov` data for:

- `yesterday`
- `today`
- `previous-24h`
- `next-24h`
- `rest-of-today`

Examples:

```bash
uv run --package weather-cli weather "Seattle,WA" --range yesterday
uv run --package weather-cli weather "Los Angeles,CA" --range today --format table
uv run --package weather-cli weather "Seattle,WA" --range previous-24h
uv run --package weather-cli weather "Los Angeles,CA" --range next-24h
uv run --package weather-cli weather "Seattle,WA" --range rest-of-today
uv run --package weather-cli weather "Los Angeles,CA" --range yesterday --nearest-station
```

Notes:

- Historical observations come from the nearest NOAA station with data for the requested window unless a city preset applies.
- These cities default to official airport climate-report stations for both observation queries and forecast ranges (`next-24h`, `rest-of-today`):
  `Denver,CO -> KDEN`, `Las Vegas,NV -> KLAS`, `Los Angeles,CA -> KLAX`,
  `Phoenix,AZ -> KPHX`, `San Francisco,CA -> KSFO`, `Seattle,WA -> KSEA`.
- Use `--nearest-station` to ignore presets. Observation queries then use the nearest station with data, while forecasts fall back to the resolved city point.
- Use `rest-of-today` when you want the remaining hourly forecast for the current local day. It includes the current overlapping hour and stops at local midnight.
- Use `--station <ID>` to force a specific NOAA station for either observations or forecast anchoring.
- City lookup uses Open-Meteo geocoding; weather data comes from NOAA.
- Override the NOAA contact email with `WEATHER_CLI_CONTACT_EMAIL` or `--contact-email`.
