from __future__ import annotations

import json
from typing import Any


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Daily High Accuracy Study</title>
    <link rel="icon" href="data:,">
    <style>
      :root {{
        --paper: #f4efe4;
        --paper-deep: #e8dcc4;
        --panel: rgba(255, 251, 245, 0.86);
        --ink: #13242b;
        --muted: #5b6a6b;
        --grid: rgba(19, 36, 43, 0.12);
        --line: #1c6e7d;
        --line-price: #6b4c9a;
        --line-glow: rgba(28, 110, 125, 0.18);
        --accent: #c76632;
        --accent-soft: rgba(199, 102, 50, 0.14);
        --thin: #d7a75a;
        --shadow: 0 26px 60px rgba(35, 47, 53, 0.14);
      }}

      * {{ box-sizing: border-box; }}

      body {{
        margin: 0;
        color: var(--ink);
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at 10% 10%, rgba(199, 102, 50, 0.18), transparent 24rem),
          radial-gradient(circle at 88% 12%, rgba(28, 110, 125, 0.18), transparent 22rem),
          linear-gradient(180deg, #efe5d4, var(--paper));
      }}

      body::before {{
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        opacity: 0.6;
        background:
          linear-gradient(rgba(255,255,255,0.28), rgba(255,255,255,0.12)),
          repeating-linear-gradient(
            90deg,
            rgba(19, 36, 43, 0.025) 0,
            rgba(19, 36, 43, 0.025) 1px,
            transparent 1px,
            transparent 26px
          );
      }}

      main {{
        width: min(1380px, calc(100vw - 1.8rem));
        margin: 0 auto;
        padding: 2rem 0 3rem;
      }}

      .hero {{
        display: grid;
        gap: 0.8rem;
        margin-bottom: 1.4rem;
      }}

      .eyebrow {{
        font-size: 0.74rem;
        letter-spacing: 0.22em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      h1 {{
        margin: 0;
        font-family: "Iowan Old Style", "Baskerville", serif;
        font-size: clamp(2.5rem, 4vw, 4.6rem);
        line-height: 0.94;
        max-width: 12ch;
      }}

      .hero p {{
        margin: 0;
        max-width: 54rem;
        color: var(--muted);
        line-height: 1.6;
      }}

      .report {{
        display: grid;
        gap: 1rem;
      }}

      .city-card {{
        background: var(--panel);
        border: 1px solid rgba(255, 255, 255, 0.72);
        border-radius: 1.6rem;
        box-shadow: var(--shadow);
        overflow: hidden;
        backdrop-filter: blur(14px);
      }}

      .city-head {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 1rem;
        padding: 1.2rem 1.25rem 1rem;
        border-bottom: 1px solid var(--grid);
        background:
          linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.38)),
          linear-gradient(90deg, rgba(199, 102, 50, 0.08), rgba(28, 110, 125, 0.08));
      }}

      .city-name {{
        margin: 0;
        font-family: "Iowan Old Style", "Baskerville", serif;
        font-size: clamp(1.8rem, 3vw, 2.5rem);
        line-height: 0.96;
      }}

      .city-subtitle {{
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.96rem;
      }}

      .stat-strip {{
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 0.7rem;
        align-items: end;
      }}

      .stat {{
        min-width: 9rem;
        padding: 0.72rem 0.82rem;
        border-radius: 1rem;
        background: rgba(255,255,255,0.68);
        border: 1px solid rgba(19, 36, 43, 0.08);
      }}

      .stat-label {{
        font-size: 0.68rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--muted);
      }}

      .stat-value {{
        margin-top: 0.24rem;
        font-family: "Iowan Old Style", "Baskerville", serif;
        font-size: 1.22rem;
      }}

      .chart-copy {{
        padding: 0.9rem 1.25rem 0;
        color: var(--muted);
        line-height: 1.5;
      }}

      .chart-wrap {{
        padding: 0.8rem 0.9rem 1rem;
      }}

      .chart-scroll {{
        overflow-x: auto;
        padding-bottom: 0.25rem;
      }}

      .chart-scroll::-webkit-scrollbar {{
        height: 10px;
      }}

      .chart-scroll::-webkit-scrollbar-thumb {{
        background: rgba(19, 36, 43, 0.18);
        border-radius: 999px;
      }}

      .chart-shell {{
        min-width: 860px;
      }}

      svg {{
        display: block;
        width: 100%;
        height: auto;
      }}

      .chart-note {{
        display: flex;
        gap: 0.9rem;
        flex-wrap: wrap;
        padding: 0 1.25rem 1.2rem;
        color: var(--muted);
        font-size: 0.86rem;
      }}

      .legend-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.46rem 0.62rem;
        border-radius: 999px;
        background: rgba(255,255,255,0.68);
        border: 1px solid rgba(19, 36, 43, 0.08);
      }}

      .legend-dot {{
        width: 0.72rem;
        height: 0.72rem;
        border-radius: 999px;
      }}

      .empty {{
        padding: 1rem 1.25rem 1.35rem;
        color: var(--muted);
      }}

      @media (max-width: 900px) {{
        .city-head {{
          grid-template-columns: 1fr;
        }}

        .stat-strip {{
          justify-content: flex-start;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <div class="eyebrow">Local Study Export</div>
        <h1>When Each City Finally Gets It Right</h1>
        <p>
          Each chart follows the forecast-accuracy chart spec: hours before the daily high is observed in
          station data, predicted high is max(observed-so-far, forecast remainder); left axis is exact-match
          accuracy, right axis is average last price of the eventual winning Kalshi contract (same days).
        </p>
      </section>
      <div id="app" class="report"></div>
    </main>
    <script id="report-data" type="application/json">{report_json}</script>
    <script>
      const report = JSON.parse(document.getElementById("report-data").textContent);

      function escapeHtml(value) {{
        return String(value ?? "")
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }}

      function formatPercent(value) {{
        return `${{Math.round((Number(value) || 0) * 100)}}%`;
      }}

      function formatHour(hour) {{
        const normalized = Number(hour);
        const suffix = normalized >= 12 ? "p" : "a";
        const clock = normalized % 12 === 0 ? 12 : normalized % 12;
        return `${{clock}}${{suffix}}`;
      }}

      function formatWindow(city) {{
        if (!city.capture_window_start_date && !city.capture_window_end_date) {{
          return "n/a";
        }}
        if (city.capture_window_start_date === city.capture_window_end_date) {{
          return city.capture_window_start_date;
        }}
        return `${{city.capture_window_start_date}} -> ${{city.capture_window_end_date}}`;
      }}

      function buildPath(points, xForIndex, yForRatio) {{
        return points
          .map((point, index) => `${{index === 0 ? "M" : "L"}}${{xForIndex(index)}},${{yForRatio(point.accuracy_ratio)}}`)
          .join(" ");
      }}

      function buildPricePath(points, xForIndex, yForCents) {{
        let d = "";
        let started = false;
        for (let i = 0; i < points.length; i++) {{
          const v = points[i].avg_winning_bucket_last_price_cents;
          if (v === null || v === undefined) {{
            started = false;
            continue;
          }}
          const x = xForIndex(i);
          const y = yForCents(Number(v));
          if (!started) {{
            d += `M${{x}},${{y}}`;
            started = true;
          }} else {{
            d += `L${{x}},${{y}}`;
          }}
        }}
        return d;
      }}

      function renderCityChart(city) {{
        const points = Array.isArray(city.points) ? city.points : [];
        if (!points.length) {{
          return `<div class="empty">No hourly accuracy points are available for this city yet.</div>`;
        }}

        const columnWidth = 52;
        const margin = {{ top: 26, right: 56, bottom: 92, left: 68 }};
        const plotWidth = Math.max(780, (points.length - 1) * columnWidth);
        const plotHeight = 190;
        const width = margin.left + plotWidth + margin.right;
        const height = margin.top + plotHeight + margin.bottom;
        const xForIndex = (index) =>
          points.length === 1
            ? margin.left + (plotWidth / 2)
            : margin.left + ((plotWidth / (points.length - 1)) * index);
        const yForRatio = (ratio) => margin.top + ((1 - Number(ratio || 0)) * plotHeight);
        const yForCents = (cents) => margin.top + ((1 - Math.min(100, Math.max(0, cents)) / 100) * plotHeight);
        const gridRatios = [0, 0.25, 0.5, 0.75, 1];
        const centTicks = [0, 25, 50, 75, 100];
        const linePath = buildPath(points, xForIndex, yForRatio);
        const pricePath = buildPricePath(points, xForIndex, yForCents);
        const areaPath = `${{linePath}} L${{xForIndex(points.length - 1)}},${{margin.top + plotHeight}} L${{xForIndex(0)}},${{margin.top + plotHeight}} Z`;

        return `
          <div class="chart-scroll">
            <div class="chart-shell" style="width:${{width}}px">
              <svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="${{escapeHtml(city.place)}} hourly accuracy chart" data-dual-axis="true">
                <defs>
                  <linearGradient id="area-${{escapeHtml(city.place).replace(/[^a-zA-Z0-9]/g, "")}}" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stop-color="rgba(28, 110, 125, 0.28)"></stop>
                    <stop offset="100%" stop-color="rgba(28, 110, 125, 0.02)"></stop>
                  </linearGradient>
                </defs>
                ${{gridRatios.map((ratio) => `
                  <g>
                    <line
                      x1="${{margin.left}}"
                      y1="${{yForRatio(ratio)}}"
                      x2="${{margin.left + plotWidth}}"
                      y2="${{yForRatio(ratio)}}"
                      stroke="rgba(19, 36, 43, 0.12)"
                      stroke-dasharray="${{ratio === 0 ? "" : "4 6"}}"
                    />
                    <text
                      x="${{margin.left - 14}}"
                      y="${{yForRatio(ratio) + 4}}"
                      text-anchor="end"
                      fill="rgba(19, 36, 43, 0.62)"
                      font-size="12"
                      font-family="Avenir Next, sans-serif"
                    >${{Math.round(ratio * 100)}}%</text>
                  </g>
                `).join("")}}
                ${{centTicks.map((c) => `
                  <g>
                    <line
                      x1="${{margin.left + plotWidth}}"
                      y1="${{yForCents(c)}}"
                      x2="${{margin.left + plotWidth + 6}}"
                      y2="${{yForCents(c)}}"
                      stroke="rgba(107, 76, 154, 0.35)"
                    />
                    <text
                      x="${{margin.left + plotWidth + 12}}"
                      y="${{yForCents(c) + 4}}"
                      text-anchor="start"
                      fill="rgba(107, 76, 154, 0.85)"
                      font-size="11"
                      font-family="Avenir Next, sans-serif"
                    >${{c}}c</text>
                  </g>
                `).join("")}}
                <path d="${{areaPath}}" fill="url(#area-${{escapeHtml(city.place).replace(/[^a-zA-Z0-9]/g, "")}})"></path>
                <path
                  d="${{linePath}}"
                  fill="none"
                  stroke="var(--line)"
                  stroke-width="4"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                ></path>
                ${{pricePath ? `<path d="${{pricePath}}" fill="none" stroke="var(--line-price)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>` : ""}}
                ${{points.map((point, index) => `
                  <g>
                    <line
                      x1="${{xForIndex(index)}}"
                      y1="${{margin.top}}"
                      x2="${{xForIndex(index)}}"
                      y2="${{margin.top + plotHeight}}"
                      stroke="rgba(19, 36, 43, 0.06)"
                    />
                    <circle
                      cx="${{xForIndex(index)}}"
                      cy="${{yForRatio(point.accuracy_ratio)}}"
                      r="${{point.thin_sample ? 5 : 6}}"
                      fill="${{point.thin_sample ? "var(--thin)" : "var(--accent)"}}"
                      stroke="rgba(255,255,255,0.95)"
                      stroke-width="2.5"
                    ></circle>
                    ${{point.avg_winning_bucket_last_price_cents != null ? `
                    <circle
                      cx="${{xForIndex(index)}}"
                      cy="${{yForCents(Number(point.avg_winning_bucket_last_price_cents))}}"
                      r="4"
                      fill="var(--line-price)"
                      stroke="rgba(255,255,255,0.9)"
                      stroke-width="1.5"
                    ></circle>` : ""}}
                    <text
                      x="${{xForIndex(index)}}"
                      y="${{margin.top + plotHeight + 22}}"
                      text-anchor="middle"
                      fill="var(--ink)"
                      font-size="12"
                      font-weight="700"
                      font-family="Avenir Next, sans-serif"
                    >${{escapeHtml(formatHour(point.local_hour))}} (${{point.valid_day_count}})</text>
                    <text
                      x="${{xForIndex(index)}}"
                      y="${{margin.top + plotHeight + 42}}"
                      text-anchor="middle"
                      fill="rgba(19, 36, 43, 0.55)"
                      font-size="10"
                      font-family="Avenir Next, sans-serif"
                    >${{point.correct_day_count}}/${{point.valid_day_count}}</text>
                  </g>
                `).join("")}}
              </svg>
            </div>
          </div>
        `;
      }}

      function renderCityCard(city) {{
        return `
          <section class="city-card">
            <div class="city-head">
              <div>
                <h2 class="city-name">${{escapeHtml(city.place)}}</h2>
                <div class="city-subtitle">
                  ${{escapeHtml(formatWindow(city))}} · Peak accuracy ${{escapeHtml(formatPercent(city.best_accuracy_ratio))}} at
                  ${{escapeHtml(formatHour(city.best_hour))}}
                </div>
              </div>
              <div class="stat-strip">
                <div class="stat">
                  <div class="stat-label">Resolved Days</div>
                  <div class="stat-value">${{city.resolved_actual_day_count}}/${{city.capture_day_count}}</div>
                </div>
                <div class="stat">
                  <div class="stat-label">Timezone</div>
                  <div class="stat-value">${{escapeHtml(city.timezone)}}</div>
                </div>
                <div class="stat">
                  <div class="stat-label">Coverage</div>
                  <div class="stat-value">${{Array.isArray(city.points) ? city.points.length : 0}} hours</div>
                </div>
              </div>
            </div>
            <div class="chart-copy">
              Left axis: exact-match accuracy (spec denominator after censoring). Right axis: average last price (cents)
              of the winning market for the same days. Tick: hour and sample size (n), then correct/total.
            </div>
            <div class="chart-wrap">${{renderCityChart(city)}}</div>
            <div class="chart-note">
              <span class="legend-pill"><span class="legend-dot" style="background:var(--accent)"></span>Accuracy</span>
              <span class="legend-pill"><span class="legend-dot" style="background:var(--line-price)"></span>Avg winner price</span>
              <span class="legend-pill"><span class="legend-dot" style="background:var(--thin)"></span>Thin sample hour</span>
            </div>
          </section>
        `;
      }}

      function renderReport() {{
        const app = document.getElementById("app");
        const cities = Array.isArray(report.cities) ? report.cities : [];
        if (!cities.length) {{
          app.innerHTML = `<section class="city-card"><div class="empty">No study cities are available in this report.</div></section>`;
          return;
        }}
        app.innerHTML = cities.map(renderCityCard).join("");
      }}

      renderReport();
    </script>
  </body>
</html>
"""


def render_accuracy_dashboard_html(report: dict[str, Any]) -> str:
    return HTML_TEMPLATE.format(report_json=json.dumps(report))
