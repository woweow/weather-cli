# weather-cli

Small Python CLI for querying NOAA `api.weather.gov` data for:

- `yesterday`
- `today`
- `previous-24h`
- `next-24h`

Examples:

```bash
uv run --with-editable . weather "Seattle,WA" --range yesterday
uv run --with-editable . weather "Los Angeles,CA" --range today --format table
uv run --with-editable . weather "Seattle,WA" --range previous-24h
uv run --with-editable . weather "Los Angeles,CA" --range next-24h
uv run --with-editable . weather "Los Angeles,CA" --range yesterday --nearest-station
```

Notes:

- Historical observations come from the nearest NOAA station with data for the requested window unless a city preset applies.
- These cities default to official airport climate-report stations for observation queries:
  `Denver,CO -> KDEN`, `Las Vegas,NV -> KLAS`, `Los Angeles,CA -> KLAX`,
  `Phoenix,AZ -> KPHX`, `San Francisco,CA -> KSFO`, `Seattle,WA -> KSEA`.
- Use `--nearest-station` to ignore presets, or `--station <ID>` to force a specific NOAA station.
- City lookup uses Open-Meteo geocoding; weather data comes from NOAA.
- Override the NOAA contact email with `WEATHER_CLI_CONTACT_EMAIL` or `--contact-email`.
