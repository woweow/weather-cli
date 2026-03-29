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
        width: min(1400px, calc(100vw - 2rem));
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
        grid-template-columns: repeat(2, 1fr);
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

      .card-body {
        display: grid;
        grid-template-columns: auto 1fr;
      }

      .section {
        padding: 1rem 1.2rem 1.2rem;
        display: grid;
        gap: 0.8rem;
        align-content: start;
      }

      .section-market {
        border-left: 1px solid var(--line);
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
        gap: 0.15rem;
      }

      .market-row {
        display: grid;
        gap: 0.6rem;
        padding: 0.8rem 0.85rem;
        border-radius: 1rem;
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid rgba(24, 35, 45, 0.08);
      }

      .weather-row {
        display: grid;
        grid-template-columns: 3.2rem 1fr;
        align-items: center;
        padding: 0.35rem 0.6rem;
        border-radius: 0.5rem;
      }

      .weather-time {
        font-size: 0.82rem;
        color: var(--muted);
        font-weight: 600;
      }

      .weather-temp {
        font-family: "Georgia", serif;
        font-size: 1.1rem;
        font-weight: 700;
        text-align: right;
      }

      .market-list {
        display: grid;
        gap: 0.45rem;
      }

      .market-row {
        grid-template-columns: 1fr;
        align-items: stretch;
      }

      .market-top {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 0.75rem;
        align-items: center;
      }

      .market-main {
        display: flex;
        align-items: baseline;
        gap: 0.5rem;
      }

      .market-label {
        font-size: 0.88rem;
        font-weight: 700;
        white-space: nowrap;
      }

      .market-prices {
        display: none;
      }

      .market-meta {
        color: var(--muted);
        font-size: 0.74rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
      }

      .headline {
        min-width: 4rem;
        text-align: center;
        border-radius: 999px;
        padding: 0.35rem 0.6rem;
        font-weight: 700;
        font-size: 0.82rem;
        background: rgba(77, 126, 168, 0.14);
        color: var(--sky);
      }

      .headline.unavailable {
        background: #ece7df;
        color: #8b857d;
      }

      .market-controls {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 0.75rem;
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
        padding: 0.4rem 0.6rem;
        cursor: pointer;
        font-weight: 700;
        font-size: 0.78rem;
        min-width: 2.8rem;
      }

      .toggle.active-yes {
        background: var(--yes-bg);
        color: var(--yes);
      }

      .toggle.active-no {
        background: var(--no-bg);
        color: var(--no);
      }

      .stake-panels {
        display: grid;
        gap: 0.5rem;
      }

      .stake-panel {
        display: grid;
        gap: 0.35rem;
        padding: 0.6rem 0.7rem;
        border-radius: 0.8rem;
        border: 1px solid rgba(24, 35, 45, 0.08);
        background: rgba(245, 239, 226, 0.7);
      }

      .stake-panel.yes {
        background: rgba(223, 246, 238, 0.75);
      }

      .stake-panel.no {
        background: rgba(253, 228, 234, 0.75);
      }

      .stake-row {
        display: flex;
        align-items: center;
        gap: 0.55rem;
      }

      .stake-label {
        min-width: 4rem;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
      }

      .stake-input {
        width: 7rem;
        padding: 0.42rem 0.55rem;
        border-radius: 0.55rem;
        border: 1px solid rgba(24, 35, 45, 0.14);
        background: rgba(255, 255, 255, 0.88);
        color: var(--ink);
        font: inherit;
      }

      .stake-help {
        color: var(--muted);
        font-size: 0.76rem;
        line-height: 1.35;
      }

      .footer {
        display: grid;
        gap: 0.85rem;
        justify-items: center;
        margin-top: 2rem;
      }

      .record-button {
        border: 1px solid var(--line);
        border-radius: 0.6rem;
        padding: 0.75rem 1.8rem;
        font-size: 0.92rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        color: var(--ink);
        cursor: pointer;
        background: var(--card);
        box-shadow: 0 2px 8px rgba(27, 37, 42, 0.08);
        transition: background 0.15s, box-shadow 0.15s;
      }

      .record-button:hover {
        background: rgba(255, 255, 255, 1);
        box-shadow: 0 4px 14px rgba(27, 37, 42, 0.12);
      }

      .record-button:disabled {
        cursor: wait;
        opacity: 0.6;
      }

      .status {
        min-height: 1.2rem;
        color: var(--muted);
        font-size: 0.88rem;
      }

      @media (max-width: 900px) {
        .cards {
          grid-template-columns: 1fr;
        }
      }

      @media (max-width: 600px) {
        main {
          width: min(100vw - 1rem, 40rem);
          padding-top: 1.5rem;
        }

        .card-body {
          grid-template-columns: 1fr;
        }

        .section-market {
          border-left: none;
          border-top: 1px solid var(--line);
        }

        .market-row {
          grid-template-columns: 1fr;
        }

        .market-top,
        .market-controls {
          grid-template-columns: 1fr;
          justify-items: start;
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
          Market rows show the exact provider values included in the input payload. When you
          select a side, enter a simulated USD stake and the dashboard will save that side,
          the displayed quote, and the provider market id for later settlement.
        </p>
      </section>

      <section id="cards" class="cards"></section>

      <section class="footer">
        <button id="record-bets" class="record-button" type="button">Record predictions</button>
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

      function tempColors(temp, minT, maxT) {
        if (maxT === minT) return { bg: "transparent", fg: "inherit" };
        const ratio = (temp - minT) / (maxT - minT);
        // Exponential curve so hot temps really pop
        const r = ratio * ratio;
        // cool: steel blue -> mid: amber -> hot: deep red-orange
        const hue = 220 - r * 210;      // 220 (blue) -> 10 (red)
        const sat = 15 + r * 75;         // 15% -> 90%
        const bgLight = 94 - r * 30;     // 94% (barely tinted) -> 64% (vivid)
        const fgLight = 40 - r * 14;     // 40% -> 26% (dark on bright bg)
        return {
          bg: `hsl(${hue}, ${sat}%, ${bgLight}%)`,
          fg: `hsl(${hue}, ${Math.min(sat + 20, 95)}%, ${fgLight}%)`
        };
      }

      function formatClock12Short(isoValue) {
        const match = /T(\\d{2}):(\\d{2})/.exec(isoValue);
        if (!match) return isoValue;
        const hours = Number(match[1]);
        const suffix = hours >= 12 ? "P" : "A";
        const normalizedHour = hours % 12 || 12;
        return `${normalizedHour}${suffix}`;
      }

      function formatCents(value) {
        if (value === null || value === undefined) {
          return "n/a";
        }
        return `${value}¢`;
      }

      function formatUsd(value) {
        if (value === null || value === undefined || value === "") {
          return "n/a";
        }
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) {
          return "n/a";
        }
        return `$${numeric.toFixed(2)}`;
      }

      function formatHeadline(row) {
        if (row.last_price_cents === null || row.last_price_cents === undefined) {
          return null;
        }
        return `Last ${formatCents(row.last_price_cents)}`;
      }

      function buildWeatherRows(card) {
        if (!card.weather_hours.length) {
          return `<div class="weather-row"><div class="weather-time">—</div><div class="weather-temp">No data</div></div>`;
        }
        const temps = card.weather_hours.map(h => h.temperature_f);
        const minT = Math.min(...temps);
        const maxT = Math.max(...temps);
        return card.weather_hours.map((hour) => {
          const t = Math.round(hour.temperature_f);
          const { bg, fg } = tempColors(hour.temperature_f, minT, maxT);
          return `
            <div class="weather-row" style="background: ${bg}">
              <div class="weather-time" style="color: ${fg}">${formatClock12Short(hour.start)}</div>
              <div class="weather-temp" style="color: ${fg}">${t}°</div>
            </div>
          `;
        }).join("");
      }

      function buildStakePanel(side, row, cardIndex, rowIndex) {
        const isYes = side === "yes";
        const sideLabel = isYes ? "Yes" : "No";
        const stakeKey = isYes ? "yes_stake_usd" : "no_stake_usd";
        const quote = isYes ? row.yes_ask_cents : row.no_ask_cents;
        const stakeValue = row[stakeKey] || "";
        const preview = buildPreview(side, row);
        return `
          <div class="stake-panel ${side}">
            <div class="stake-row">
              <div class="stake-label">${sideLabel} stake</div>
              <input
                class="stake-input"
                type="number"
                min="0"
                step="0.01"
                inputmode="decimal"
                placeholder="0.00"
                value="${stakeValue}"
                data-stake-input="true"
                data-card-index="${cardIndex}"
                data-row-index="${rowIndex}"
                data-side="${side}"
              />
              <div class="market-meta">Ask ${formatCents(quote)}</div>
            </div>
            <div class="stake-help">${preview}</div>
          </div>
        `;
      }

      function buildPreview(side, row) {
        const isYes = side === "yes";
        const stakeText = isYes ? row.yes_stake_usd : row.no_stake_usd;
        const quote = isYes ? row.yes_ask_cents : row.no_ask_cents;
        if (!stakeText) {
          return "Enter a USD stake to estimate contracts and simulated payout.";
        }
        const stake = Number(stakeText);
        if (!Number.isFinite(stake) || stake <= 0) {
          return "Enter a valid positive USD amount.";
        }
        if (quote === null || quote === undefined || quote <= 0) {
          return `Stake ${formatUsd(stake)} recorded. No ask quote is available for simulator math.`;
        }
        const contracts = stake / (quote / 100);
        const gross = contracts;
        const net = gross - stake;
        return `Stake ${formatUsd(stake)} • ~${contracts.toFixed(4)} contracts • Gross ${formatUsd(gross)} • Net ${formatUsd(net)}`;
      }

      function buildMarketRows(cardIndex, card) {
        return card.market.rows.map((row, rowIndex) => {
          const headline = formatHeadline(row);
          const yesClass = row.selected_yes ? "toggle active-yes" : "toggle";
          const noClass = row.selected_no ? "toggle active-no" : "toggle";
          const stakePanels = [
            row.selected_yes ? buildStakePanel("yes", row, cardIndex, rowIndex) : "",
            row.selected_no ? buildStakePanel("no", row, cardIndex, rowIndex) : ""
          ].join("");
          return `
            <div class="market-row">
              <div class="market-top">
                <div class="market-main">
                  <div class="market-label">${row.label}</div>
                  <div class="market-prices">
                    <span>Yes bid ${formatCents(row.yes_bid_cents)}</span>
                    <span>Yes ask ${formatCents(row.yes_ask_cents)}</span>
                    <span>No bid ${formatCents(row.no_bid_cents)}</span>
                    <span>No ask ${formatCents(row.no_ask_cents)}</span>
                  </div>
                </div>
                <div class="market-meta">${row.provider_market_ticker}</div>
              </div>
              <div class="market-controls">
                <div class="headline ${headline ? "" : "unavailable"}">${headline || "No last price"}</div>
                <div class="toggles" role="group" aria-label="${row.label}">
                  <button type="button" class="${yesClass}" data-card-index="${cardIndex}" data-row-index="${rowIndex}" data-side="yes">Yes</button>
                  <button type="button" class="${noClass}" data-card-index="${cardIndex}" data-row-index="${rowIndex}" data-side="no">No</button>
                </div>
              </div>
              <div class="stake-panels">${stakePanels}</div>
            </div>
          `;
        }).join("");
      }

      function render() {
        cardsEl.innerHTML = state.cards.map((card, cardIndex) => {
          const temps = card.weather_hours.map(h => h.temperature_f);
          const peak = temps.length ? Math.round(Math.max(...temps)) : "—";
          return `
          <article class="card">
            <header class="card-head">
              <div class="city-line">
                <h2 class="city">${card.city}, ${card.state}</h2>
                <div class="tz">Peak ${peak}°</div>
              </div>
            </header>
            <div class="card-body">
              <section class="section">
                <div class="section-title">
                  <h2>°F</h2>
                </div>
                <div class="weather-list">${buildWeatherRows(card)}</div>
              </section>
              <section class="section section-market">
                <div class="section-title">
                  <h2>Market</h2>
                  <div class="section-subtitle">${card.market.event_date_label}</div>
                </div>
                <div class="market-list">${buildMarketRows(cardIndex, card)}</div>
              </section>
            </div>
          </article>
        `}).join("");
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
          statusEl.textContent = `Saved session ${payload.session_id} at ${payload.saved_at} with ${payload.selection_count} selections.`;
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

      document.addEventListener("input", (event) => {
        const target = event.target.closest("input[data-stake-input]");
        if (!target) {
          return;
        }
        const cardIndex = Number(target.dataset.cardIndex);
        const rowIndex = Number(target.dataset.rowIndex);
        const side = target.dataset.side;
        const row = state.cards[cardIndex].market.rows[rowIndex];
        const key = side === "yes" ? "yes_stake_usd" : "no_stake_usd";
        row[key] = target.value.trim() || null;
      });

      document.addEventListener("change", (event) => {
        const target = event.target.closest("input[data-stake-input]");
        if (!target) {
          return;
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
