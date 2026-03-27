Saved bet snapshots must remain compatible with the `weather-dashboard generate-html`
input schema so a future feature can reload prior-day data and pre-seed the UI.

Future replay is intentionally not implemented yet. The `.bets/` directory is the
long-term persistence layer for that work.
