from __future__ import annotations

import json
from typing import Any


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weather Bet Dashboard</title>
    <style>
      :root {
        --bg: #f5efe2;
        --bg-accent: #dceaf0;
        --ink: #18232d;
        --muted: #5c6972;
        --card: rgba(255, 252, 247, 0.9);
        --line: rgba(24, 35, 45, 0.14);
        --shadow: 0 24px 60px rgba(27, 37, 42, 0.12);
        --sun: #d56c2b;
        --sky: #4d7ea8;
        --yes: #144d3f;
        --yes-bg: #dff6ee;
        --no: #6f2232;
        --no-bg: #fde4ea;
        --dim: #d7d4cf;
      }

      * { box-sizing: border-box; }

      body {
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(213, 108, 43, 0.18), transparent 28rem),
          radial-gradient(circle at top right, rgba(77, 126, 168, 0.18), transparent 24rem),
          linear-gradient(180deg, var(--bg), #ede6d5);
        font-family: "Avenir Next", "Segoe UI", sans-serif;
      }

      body::before {
        content: "";
        position: fixed;
        inset: 0;
        background-image:
          linear-gradient(rgba(24, 35, 45, 0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(24, 35, 45, 0.03) 1px, transparent 1px);
        background-size: 28px 28px;
        pointer-events: none;
      }

      main {
        width: min(1180px, calc(100vw - 2rem));
        margin: 0 auto;
        padding: 2.5rem 0 4rem;
      }

      .hero {
        display: grid;
        gap: 0.75rem;
        margin-bottom: 2rem;
      }

      .eyebrow {
        letter-spacing: 0.2em;
        text-transform: uppercase;
        color: var(--muted);
        font-size: 0.78rem;
      }

      h1 {
        margin: 0;
        font-size: clamp(2.6rem, 4vw, 4.5rem);
        line-height: 0.96;
        font-family: "Georgia", serif;
        font-weight: 700;
        max-width: 10ch;
      }

      .hero-copy {
        margin: 0;
        max-width: 50rem;
        color: var(--muted);
        font-size: 1rem;
        line-height: 1.55;
      }

      .cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 1.1rem;
      }

      .card {
        background: var(--card);
        border: 1px solid rgba(255, 255, 255, 0.7);
        box-shadow: var(--shadow);
        border-radius: 1.6rem;
        overflow: hidden;
        display: grid;
        backdrop-filter: blur(12px);
      }

      .card-head {
        padding: 1.1rem 1.2rem 1rem;
        border-bottom: 1px solid var(--line);
        background:
          linear-gradient(135deg, rgba(255, 255, 255, 0.76), rgba(255, 255, 255, 0.42)),
          linear-gradient(90deg, rgba(213, 108, 43, 0.06), rgba(77, 126, 168, 0.08));
      }

      .city-line {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 1rem;
      }

      .city {
        margin: 0;
        font-family: "Georgia", serif;
        font-size: 1.8rem;
        line-height: 1;
      }

      .tz {
        color: var(--muted);
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        text-align: right;
      }

      .section {
        padding: 1rem 1.2rem 1.2rem;
        display: grid;
        gap: 0.8rem;
      }

      .section + .section {
        border-top: 1px solid var(--line);
      }

      .section-title {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1rem;
      }

      .section-title h2 {
        margin: 0;
        font-size: 0.92rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }

      .section-subtitle {
        color: var(--muted);
        font-size: 0.78rem;
      }

      .weather-list {
        display: grid;
        gap: 0.5rem;
      }

      .weather-row,
      .market-row {
        display: grid;
        gap: 0.6rem;
        padding: 0.8rem 0.85rem;
        border-radius: 1rem;
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid rgba(24, 35, 45, 0.08);
      }

      .weather-row {
        grid-template-columns: 5.4rem 1fr auto;
        align-items: center;
      }

      .weather-time {
        font-weight: 700;
      }

      .weather-detail {
        display: grid;
        gap: 0.12rem;
      }

      .weather-summary {
        font-size: 0.92rem;
      }

      .weather-extra {
        color: var(--muted);
        font-size: 0.82rem;
      }

      .weather-temp {
        font-family: "Georgia", serif;
        font-size: 1.3rem;
      }

      .market-list {
        display: grid;
        gap: 0.7rem;
      }

      .market-row {
        grid-template-columns: 1.6fr auto auto;
        align-items: center;
      }

      .market-main {
        display: grid;
        gap: 0.28rem;
      }

      .market-label {
        font-size: 1rem;
        font-weight: 700;
      }

      .market-prices {
        color: var(--muted);
        font-size: 0.82rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem 0.75rem;
      }

      .chance {
        min-width: 6.4rem;
        text-align: center;
        border-radius: 999px;
        padding: 0.55rem 0.85rem;
        font-weight: 700;
        background: rgba(77, 126, 168, 0.14);
        color: var(--sky);
      }

      .chance.unavailable {
        background: #ece7df;
        color: #8b857d;
      }

      .toggles {
        display: inline-flex;
        border-radius: 999px;
        overflow: hidden;
        border: 1px solid rgba(24, 35, 45, 0.1);
        background: rgba(255, 255, 255, 0.6);
      }

      .toggle {
        border: 0;
        background: transparent;
        color: var(--muted);
        padding: 0.6rem 0.9rem;
        cursor: pointer;
        font-weight: 700;
        min-width: 4rem;
      }

      .toggle.active-yes {
        background: var(--yes-bg);
        color: var(--yes);
      }

      .toggle.active-no {
        background: var(--no-bg);
        color: var(--no);
      }

      .footer {
        display: grid;
        gap: 0.85rem;
        justify-items: center;
        margin-top: 2rem;
      }

      .record-button {
        border: 0;
        border-radius: 999px;
        padding: 1rem 1.6rem;
        font-size: 1rem;
        font-weight: 800;
        color: #fff7f0;
        cursor: pointer;
        background: linear-gradient(135deg, #1f3a57, #c25a21);
        box-shadow: 0 14px 26px rgba(36, 54, 73, 0.2);
      }

      .record-button:disabled {
        cursor: wait;
        opacity: 0.75;
      }

      .status {
        min-height: 1.2rem;
        color: var(--muted);
        font-size: 0.88rem;
      }

      @media (max-width: 760px) {
        main {
          width: min(100vw - 1rem, 40rem);
          padding-top: 1.5rem;
        }

        .weather-row,
        .market-row {
          grid-template-columns: 1fr;
        }

        .chance,
        .toggles {
          justify-self: start;
        }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">Daily Weather Desk</div>
        <h1>Weather and Kalshi bet board.</h1>
        <p class="hero-copy">
          Forecast hours run from local now through midnight. Market rows only show exact
          upstream values included in the input payload. If chance data is missing, the UI
          leaves that slot intentionally blank instead of inventing a proxy.
        </p>
      </section>

      <section id="cards" class="cards"></section>

      <section class="footer">
        <button id="record-bets" class="record-button" type="button">Record bets</button>
        <div id="status" class="status" aria-live="polite"></div>
      </section>
    </main>

    <script id="dashboard-data" type="application/json">__PAYLOAD_JSON__</script>
    <script>
      const SAVE_ENDPOINT = __SAVE_ENDPOINT__;
      const initialPayload = JSON.parse(document.getElementById("dashboard-data").textContent);
      const state = JSON.parse(JSON.stringify(initialPayload));

      const cardsEl = document.getElementById("cards");
      const statusEl = document.getElementById("status");
      const saveButtonEl = document.getElementById("record-bets");

      function formatClock(isoValue) {
        const match = /T(\\d{2}):(\\d{2})/.exec(isoValue);
        if (!match) return isoValue;
        const hours = Number(match[1]);
        const minutes = match[2];
        const suffix = hours >= 12 ? "PM" : "AM";
        const normalizedHour = hours % 12 || 12;
        return `${normalizedHour}:${minutes} ${suffix}`;
      }

      function formatTemp(value) {
        return `${Math.round(value)}°F`;
      }

      function formatPercent(value) {
        if (value === null || value === undefined) {
          return "precip n/a";
        }
        return `${Math.round(value)}% precip`;
      }

      function formatCents(value) {
        if (value === null || value === undefined) {
          return "n/a";
        }
        return `${value}¢`;
      }

      function formatChance(row) {
        if (row.chance_display === null || row.chance_display === undefined || row.chance_display === "") {
          return null;
        }
        if (typeof row.chance_display === "number") {
          return `${row.chance_display}%`;
        }
        return String(row.chance_display);
      }

      function buildWeatherRows(card) {
        if (!card.weather_hours.length) {
          return `<div class="weather-row"><div class="weather-detail"><div class="weather-summary">No upcoming hourly forecast in payload.</div></div></div>`;
        }
        return card.weather_hours.map((hour) => `
          <div class="weather-row">
            <div class="weather-time">${formatClock(hour.start)}</div>
            <div class="weather-detail">
              <div class="weather-summary">${hour.summary}</div>
              <div class="weather-extra">${formatPercent(hour.precipitation_probability_pct)}${hour.wind_speed ? ` • wind ${hour.wind_speed}` : ""}</div>
            </div>
            <div class="weather-temp">${formatTemp(hour.temperature_f)}</div>
          </div>
        `).join("");
      }

      function buildMarketRows(cardIndex, card) {
        return card.market.rows.map((row, rowIndex) => {
          const chance = formatChance(row);
          const yesClass = row.selected_yes ? "toggle active-yes" : "toggle";
          const noClass = row.selected_no ? "toggle active-no" : "toggle";
          return `
            <div class="market-row">
              <div class="market-main">
                <div class="market-label">${row.label}</div>
                <div class="market-prices">
                  <span>Yes bid ${formatCents(row.yes_bid_cents)}</span>
                  <span>Yes ask ${formatCents(row.yes_ask_cents)}</span>
                  <span>No bid ${formatCents(row.no_bid_cents)}</span>
                  <span>No ask ${formatCents(row.no_ask_cents)}</span>
                </div>
              </div>
              <div class="chance ${chance ? "" : "unavailable"}">${chance || "No chance data"}</div>
              <div class="toggles" role="group" aria-label="${row.label}">
                <button type="button" class="${yesClass}" data-card-index="${cardIndex}" data-row-index="${rowIndex}" data-side="yes">Yes</button>
                <button type="button" class="${noClass}" data-card-index="${cardIndex}" data-row-index="${rowIndex}" data-side="no">No</button>
              </div>
            </div>
          `;
        }).join("");
      }

      function render() {
        cardsEl.innerHTML = state.cards.map((card, cardIndex) => `
          <article class="card">
            <header class="card-head">
              <div class="city-line">
                <h2 class="city">${card.city}, ${card.state}</h2>
                <div class="tz">${card.timezone}</div>
              </div>
            </header>
            <section class="section">
              <div class="section-title">
                <h2>Upcoming Hours</h2>
                <div class="section-subtitle">Now through midnight</div>
              </div>
              <div class="weather-list">${buildWeatherRows(card)}</div>
            </section>
            <section class="section">
              <div class="section-title">
                <h2>Current Market</h2>
                <div class="section-subtitle">${card.market.event_date_label}</div>
              </div>
              <div class="market-list">${buildMarketRows(cardIndex, card)}</div>
            </section>
          </article>
        `).join("");
      }

      async function recordBets() {
        saveButtonEl.disabled = true;
        statusEl.textContent = "Recording bets…";
        try {
          const response = await fetch(SAVE_ENDPOINT, {
            method: "POST",
            headers: {
              "Content-Type": "application/json"
            },
            body: JSON.stringify(state)
          });
          const payload = await response.json();
          if (!response.ok) {
            throw new Error(payload.error || "Save failed");
          }
          statusEl.textContent = `Saved ${payload.file_name} at ${payload.saved_at}.`;
        } catch (error) {
          statusEl.textContent = error.message || "Unable to record bets.";
        } finally {
          saveButtonEl.disabled = false;
        }
      }

      document.addEventListener("click", (event) => {
        const target = event.target.closest("button[data-card-index]");
        if (!target) {
          return;
        }
        const cardIndex = Number(target.dataset.cardIndex);
        const rowIndex = Number(target.dataset.rowIndex);
        const side = target.dataset.side;
        const row = state.cards[cardIndex].market.rows[rowIndex];
        if (side === "yes") {
          row.selected_yes = !row.selected_yes;
        } else if (side === "no") {
          row.selected_no = !row.selected_no;
        }
        render();
      });

      saveButtonEl.addEventListener("click", recordBets);
      render();
    </script>
  </body>
</html>
"""


def render_dashboard_html(payload: dict[str, Any], *, save_endpoint: str) -> str:
    payload_json = json.dumps(payload, indent=2)
    save_endpoint_json = json.dumps(save_endpoint)
    return (
        HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)
        .replace("__SAVE_ENDPOINT__", save_endpoint_json)
    )
