from __future__ import annotations

import json
from typing import Any


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Forecast Confidence Atlas</title>
    <style>
      :root {{
        --paper: #f6f0e4;
        --paper-alt: #fffaf2;
        --ink: #1f2a2e;
        --muted: #6d7670;
        --storm: #356a7a;
        --storm-deep: #123d4d;
        --sun: #c66b2d;
        --gold: #e7b35e;
        --danger: #a64034;
        --line: rgba(31, 42, 46, 0.14);
        --shadow: 0 26px 70px rgba(26, 39, 45, 0.15);
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        min-height: 100vh;
        color: var(--ink);
        background:
          radial-gradient(circle at 15% 15%, rgba(198, 107, 45, 0.16), transparent 24rem),
          radial-gradient(circle at 85% 10%, rgba(53, 106, 122, 0.22), transparent 28rem),
          linear-gradient(180deg, #efe3cd, var(--paper));
        font-family: "Avenir Next", "Gill Sans", "Trebuchet MS", sans-serif;
      }}

      body::before {{
        content: "";
        position: fixed;
        inset: 0;
        background:
          radial-gradient(circle at center, rgba(255,255,255,0.18) 0, transparent 42%),
          repeating-linear-gradient(
            115deg,
            rgba(18, 61, 77, 0.04) 0,
            rgba(18, 61, 77, 0.04) 2px,
            transparent 2px,
            transparent 32px
          );
        pointer-events: none;
        mix-blend-mode: multiply;
      }}

      main {{
        width: min(1180px, calc(100vw - 2rem));
        margin: 0 auto;
        padding: 2.4rem 0 3.5rem;
      }}

      .hero {{
        display: grid;
        gap: 0.85rem;
        margin-bottom: 1.8rem;
      }}

      .eyebrow {{
        letter-spacing: 0.22em;
        text-transform: uppercase;
        font-size: 0.76rem;
        color: var(--muted);
      }}

      h1 {{
        margin: 0;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        font-size: clamp(2.8rem, 5vw, 5rem);
        line-height: 0.92;
        max-width: 12ch;
      }}

      .hero-copy {{
        margin: 0;
        max-width: 48rem;
        color: var(--muted);
        line-height: 1.55;
      }}

      .shell {{
        display: grid;
        gap: 1rem;
      }}

      .panel {{
        background: rgba(255, 250, 242, 0.86);
        border: 1px solid rgba(255, 255, 255, 0.7);
        border-radius: 1.8rem;
        box-shadow: var(--shadow);
        overflow: hidden;
        backdrop-filter: blur(14px);
      }}

      .topbar {{
        display: grid;
        grid-template-columns: minmax(16rem, 22rem) 1fr;
        gap: 1rem;
        padding: 1.1rem 1.2rem 1rem;
        border-bottom: 1px solid var(--line);
        background:
          linear-gradient(135deg, rgba(255,255,255,0.85), rgba(255,255,255,0.48)),
          linear-gradient(90deg, rgba(198, 107, 45, 0.08), rgba(53, 106, 122, 0.09));
      }}

      .selector-wrap {{
        display: grid;
        gap: 0.4rem;
      }}

      .selector-wrap label {{
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      select {{
        appearance: none;
        border: 1px solid rgba(18, 61, 77, 0.2);
        border-radius: 999px;
        padding: 0.85rem 1rem;
        background: linear-gradient(180deg, var(--paper-alt), #f5ecdd);
        color: var(--ink);
        font-size: 1rem;
      }}

      .summary-strip {{
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        align-items: end;
        justify-content: flex-end;
      }}

      .chip {{
        min-width: 8.5rem;
        padding: 0.8rem 0.9rem;
        border-radius: 1.2rem;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(18, 61, 77, 0.09);
      }}

      .chip-label {{
        font-size: 0.72rem;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      .chip-value {{
        margin-top: 0.3rem;
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        font-size: 1.35rem;
      }}

      .warning {{
        display: none;
        margin: 1rem 1.2rem 0;
        padding: 0.95rem 1rem;
        border-radius: 1rem;
        background: rgba(231, 179, 94, 0.18);
        border: 1px solid rgba(198, 107, 45, 0.25);
        color: var(--storm-deep);
      }}

      .warning[data-visible="true"] {{
        display: block;
      }}

      .grid {{
        display: grid;
        grid-template-columns: 1.7fr 1fr;
      }}

      .chart-pane, .coverage-pane {{
        padding: 1.2rem;
      }}

      .coverage-pane {{
        border-left: 1px solid var(--line);
        background:
          linear-gradient(180deg, rgba(255,255,255,0.3), rgba(255,255,255,0.55)),
          linear-gradient(180deg, rgba(198, 107, 45, 0.05), transparent 35%);
      }}

      .section-head {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
        margin-bottom: 0.9rem;
      }}

      .section-head h2 {{
        margin: 0;
        font-size: 0.88rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
      }}

      .section-note {{
        color: var(--muted);
        font-size: 0.82rem;
      }}

      .chart-frame {{
        padding: 1rem;
        border-radius: 1.3rem;
        background: linear-gradient(180deg, rgba(53, 106, 122, 0.1), rgba(255,255,255,0.55));
        border: 1px solid rgba(18, 61, 77, 0.08);
      }}

      #accuracy-chart {{
        width: 100%;
        height: auto;
        display: block;
      }}

      .coverage-list {{
        display: grid;
        gap: 0.55rem;
      }}

      .coverage-card {{
        padding: 0.85rem 0.9rem;
        border-radius: 1rem;
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(18, 61, 77, 0.08);
      }}

      .coverage-top {{
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 1rem;
      }}

      .coverage-hour {{
        font-family: "Iowan Old Style", "Palatino Linotype", serif;
        font-size: 1.1rem;
      }}

      .coverage-ratio {{
        color: var(--muted);
        font-size: 0.84rem;
      }}

      .stack {{
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 0.35rem;
        margin-top: 0.75rem;
      }}

      .stack-bar {{
        position: relative;
        height: 0.55rem;
        border-radius: 999px;
        overflow: hidden;
        background: rgba(18, 61, 77, 0.08);
      }}

      .stack-fill {{
        position: absolute;
        inset: 0 auto 0 0;
        border-radius: inherit;
      }}

      .stack-fill.valid {{ background: linear-gradient(90deg, var(--storm), #73a7ae); }}
      .stack-fill.missing {{ background: linear-gradient(90deg, var(--gold), #f2d59f); }}
      .stack-fill.excluded {{ background: linear-gradient(90deg, var(--danger), #d97a6d); }}

      .stack-meta {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.35rem;
        margin-top: 0.45rem;
        font-size: 0.79rem;
        color: var(--muted);
      }}

      .legend {{
        display: flex;
        gap: 0.85rem;
        flex-wrap: wrap;
        margin-top: 1rem;
        color: var(--muted);
        font-size: 0.8rem;
      }}

      .legend-dot {{
        display: inline-block;
        width: 0.7rem;
        height: 0.7rem;
        margin-right: 0.35rem;
        border-radius: 999px;
      }}

      .footer-note {{
        margin-top: 1rem;
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.55;
      }}

      @media (max-width: 920px) {{
        .topbar {{ grid-template-columns: 1fr; }}
        .summary-strip {{ justify-content: flex-start; }}
        .grid {{ grid-template-columns: 1fr; }}
        .coverage-pane {{ border-left: 0; border-top: 1px solid var(--line); }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">Local Study Export</div>
        <h1>Forecast Confidence Atlas</h1>
        <p class="hero-copy">
          A local-first weather lab view of when each city's remaining-day forecast becomes trustworthy enough to matter.
          Accuracy is shown alongside missing and excluded coverage so thin samples stay obvious.
        </p>
      </section>

      <section class="shell panel">
        <div class="topbar">
          <div class="selector-wrap">
            <label for="city-select">City Selector</label>
            <select id="city-select"></select>
          </div>
          <div class="summary-strip">
            <div class="chip">
              <div class="chip-label">Timezone</div>
              <div class="chip-value" id="city-timezone">-</div>
            </div>
            <div class="chip">
              <div class="chip-label">Study Days</div>
              <div class="chip-value" id="study-day-count">-</div>
            </div>
            <div class="chip">
              <div class="chip-label">Captured Hours</div>
              <div class="chip-value" id="hour-count">-</div>
            </div>
          </div>
        </div>

        <div class="warning" id="sample-warning" data-visible="false"></div>

        <div class="grid">
          <section class="chart-pane">
            <div class="section-head">
              <h2>Hourly Forecast Accuracy</h2>
              <div class="section-note">Remaining-day max forecast versus final observed high</div>
            </div>
            <div class="chart-frame">
              <svg id="accuracy-chart" viewBox="0 0 760 320" role="img" aria-label="Hourly forecast accuracy chart"></svg>
            </div>
            <div class="legend">
              <span><span class="legend-dot" style="background: var(--storm);"></span>Accuracy line</span>
              <span><span class="legend-dot" style="background: var(--gold);"></span>Coverage warnings appear when valid days stay under the sample threshold</span>
            </div>
          </section>

          <aside class="coverage-pane">
            <div class="section-head">
              <h2>Coverage Ledger</h2>
              <div class="section-note">Valid, missing, and excluded day counts by hour</div>
            </div>
            <div class="coverage-list" id="coverage-list"></div>
            <p class="footer-note">
              Missing means the city-day had no capture for that hour. Excluded means a capture existed,
              but the final observed high or the weather payload was unavailable for finalized accuracy.
            </p>
          </aside>
        </div>
      </section>
    </main>

    <script id="report-data" type="application/json">__REPORT_JSON__</script>
    <script>
      const report = JSON.parse(document.getElementById("report-data").textContent);
      const select = document.getElementById("city-select");
      const timezoneNode = document.getElementById("city-timezone");
      const studyDayNode = document.getElementById("study-day-count");
      const hourCountNode = document.getElementById("hour-count");
      const warningNode = document.getElementById("sample-warning");
      const coverageList = document.getElementById("coverage-list");
      const chart = document.getElementById("accuracy-chart");

      report.cities.forEach((city, index) => {{
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = city.place;
        select.appendChild(option);
      }});

      function renderCity(index) {{
        const city = report.cities[index];
        timezoneNode.textContent = city.timezone;
        studyDayNode.textContent = String(city.study_day_count);
        hourCountNode.textContent = String(city.points.length);

        if (city.thin_sample_hours.length > 0) {{
          warningNode.dataset.visible = "true";
          warningNode.textContent =
            `Thin sample: hours ${city.thin_sample_hours.map((hour) => hour.toString().padStart(2, "0")).join(", ")} ` +
            `have fewer than ${report.min_valid_sample} valid study days.`;
        }} else {{
          warningNode.dataset.visible = "false";
          warningNode.textContent = "";
        }}

        renderChart(city);
        renderCoverage(city);
      }}

      function renderChart(city) {{
        const points = city.points;
        const width = 760;
        const height = 320;
        const margin = {{ top: 18, right: 24, bottom: 44, left: 52 }};
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;
        const minHour = Math.min(...points.map((point) => point.local_hour));
        const maxHour = Math.max(...points.map((point) => point.local_hour));
        const xForHour = (hour) =>
          margin.left + ((hour - minHour) / Math.max(1, maxHour - minHour)) * plotWidth;
        const yForRatio = (ratio) => margin.top + (1 - ratio) * plotHeight;

        const gridLines = [0, 0.5, 1].map((ratio) => {{
          const y = yForRatio(ratio);
          return `
            <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}"
                  stroke="rgba(18, 61, 77, 0.12)" stroke-dasharray="4 6" />
            <text x="${margin.left - 12}" y="${y + 4}" text-anchor="end" fill="rgba(31,42,46,0.6)" font-size="12">
              ${Math.round(ratio * 100)}%
            </text>
          `;
        }}).join("");

        const xLabels = points.map((point) => {{
          const x = xForHour(point.local_hour);
          return `
            <text x="${x}" y="${height - 14}" text-anchor="middle" fill="rgba(31,42,46,0.65)" font-size="12">
              ${String(point.local_hour).padStart(2, "0")}
            </text>
          `;
        }}).join("");

        const path = points.map((point, index) => {{
          const x = xForHour(point.local_hour);
          const y = yForRatio(point.accuracy_ratio);
          return `${index === 0 ? "M" : "L"} ${x} ${y}`;
        }}).join(" ");

        const pointNodes = points.map((point) => {{
          const x = xForHour(point.local_hour);
          const y = yForRatio(point.accuracy_ratio);
          const thin = point.valid_day_count < report.min_valid_sample;
          return `
            <g>
              <circle cx="${x}" cy="${y}" r="8" fill="${thin ? "var(--gold)" : "var(--storm)"}" stroke="rgba(255,255,255,0.9)" stroke-width="3" />
              <text x="${x}" y="${y - 14}" text-anchor="middle" fill="var(--storm-deep)" font-size="12" font-weight="700">
                ${Math.round(point.accuracy_ratio * 100)}%
              </text>
            </g>
          `;
        }}).join("");

        chart.innerHTML = `
          <rect x="0" y="0" width="${width}" height="${height}" rx="26" fill="rgba(255,255,255,0.16)"></rect>
          ${gridLines}
          <path d="${path}" fill="none" stroke="var(--storm)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"></path>
          ${pointNodes}
          ${xLabels}
          <text x="${width - margin.right}" y="${margin.top + 4}" text-anchor="end" fill="rgba(31,42,46,0.55)" font-size="12">
            Higher is better
          </text>
        `;
      }}

      function renderCoverage(city) {{
        coverageList.innerHTML = "";
        city.points.forEach((point) => {{
          const total = point.valid_day_count + point.missing_day_count + point.excluded_day_count;
          const safeTotal = Math.max(1, total);
          const card = document.createElement("article");
          card.className = "coverage-card";
          card.innerHTML = `
            <div class="coverage-top">
              <div class="coverage-hour">${String(point.local_hour).padStart(2, "0")}:00</div>
              <div class="coverage-ratio">${point.correct_day_count}/${Math.max(1, point.valid_day_count)} correct</div>
            </div>
            <div class="stack">
              <div>
                <div class="stack-bar"><div class="stack-fill valid" style="width:${(point.valid_day_count / safeTotal) * 100}%"></div></div>
              </div>
              <div>
                <div class="stack-bar"><div class="stack-fill missing" style="width:${(point.missing_day_count / safeTotal) * 100}%"></div></div>
              </div>
              <div>
                <div class="stack-bar"><div class="stack-fill excluded" style="width:${(point.excluded_day_count / safeTotal) * 100}%"></div></div>
              </div>
            </div>
            <div class="stack-meta">
              <div>Valid ${point.valid_day_count}</div>
              <div>Missing ${point.missing_day_count}</div>
              <div>Excluded ${point.excluded_day_count}</div>
            </div>
          `;
          coverageList.appendChild(card);
        }});
      }}

      select.addEventListener("change", () => renderCity(Number(select.value)));
      renderCity(0);
    </script>
  </body>
</html>
"""


def render_accuracy_dashboard_html(report: dict[str, Any]) -> str:
    report_json = json.dumps(report).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__REPORT_JSON__", report_json)
    return html.replace("{{", "{").replace("}}", "}")
