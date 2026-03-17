"""HTML report generator with Plotly charts for investment ideas."""

from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from fin_toolkit.models.results import InvestmentIdeaResult
from fin_toolkit.report.i18n import (
    DISCLAIMER,
    HEADERS,
    METRIC_LABELS,
    SIGNALS,
    fmt_price,
    i18n_span,
)
from fin_toolkit.report.narrative import (
    generate_fcf_narrative,
    generate_target_summary,
    generate_thesis,
)


def render_investment_idea_html(result: InvestmentIdeaResult) -> str:
    """Render InvestmentIdeaResult as self-contained HTML with Plotly charts."""
    sections: list[str] = [
        _header_section(result),
        _thesis_section(result),
        _analyst_estimates_section(result),
        _target_price_section(result),
        _price_chart_section(result),
        _consensus_section(result),
        _fundamental_section(result),
        _fcf_waterfall_section(result),
        _historical_trends_section(result),
        _scenario_section(result),
        _catalysts_section(result),
        _risks_section(result),
        _technical_section(result),
        _disclaimer_section(),
    ]

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Investment Idea: {result.ticker}</title>
<script src="https://cdn.plot.ly/plotly-3.0.1.min.js"></script>
{_css()}
</head>
<body>
<button id="lang-btn" class="lang-toggle" onclick="toggleLang()">RU</button>
<div class="container">
{body}
</div>
{_toggle_js()}
</body>
</html>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _css() -> str:
    return """<style>
:root { --bg: #1a1a2e; --card: #16213e; --accent: #0f3460; --text: #e4e4e4;
        --green: #00d68f; --red: #ff6b6b; --yellow: #ffd93d; --blue: #4fc3f7; }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: var(--bg); color: var(--text); line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.section { background: var(--card); border-radius: 12px; padding: 24px;
           margin-bottom: 20px; }
.section h2 { color: var(--blue); margin-bottom: 16px; font-size: 1.3em; }
.header { text-align: center; padding: 32px; }
.header h1 { font-size: 2.2em; margin-bottom: 8px; }
.badge { display: inline-block; padding: 4px 12px; border-radius: 20px;
         font-weight: 600; font-size: 0.85em; }
.badge-bullish { background: var(--green); color: #000; }
.badge-bearish { background: var(--red); color: #fff; }
.badge-neutral { background: var(--yellow); color: #000; }
.badge-high { background: var(--red); color: #fff; }
.badge-medium { background: var(--yellow); color: #000; }
.badge-low { background: var(--green); color: #000; }
.badge-positive { background: var(--green); color: #000; }
.badge-negative { background: var(--red); color: #fff; }
table { width: 100%; border-collapse: collapse; margin-top: 12px; }
th, td { padding: 10px 14px; text-align: left; border-bottom: 1px solid #2a3a5e; }
th { color: var(--blue); font-weight: 600; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
             gap: 12px; margin-top: 12px; }
.card { background: var(--accent); border-radius: 8px; padding: 16px; }
.card h3 { font-size: 0.95em; color: var(--blue); margin-bottom: 8px; }
.plotly-chart { width: 100%; min-height: 400px; }
.score-bar { display: flex; align-items: center; margin: 4px 0; }
.score-bar .label { width: 140px; font-size: 0.9em; }
.score-bar .bar-bg { flex: 1; height: 20px; background: var(--accent);
                     border-radius: 4px; overflow: hidden; }
.score-bar .bar-fill { height: 100%; border-radius: 4px; }
.score-bar .value { width: 50px; text-align: right; font-weight: 600; }
.disclaimer { font-size: 0.8em; color: #888; text-align: center;
              padding: 20px; margin-top: 20px; }
.warnings { background: #2a1a0e; border-left: 3px solid var(--yellow);
            padding: 12px; margin-top: 16px; border-radius: 0 8px 8px 0; }
.lang-toggle { position: fixed; top: 16px; right: 16px; z-index: 1000;
  background: var(--accent); color: var(--text); border: 1px solid var(--blue);
  padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 0.9em; font-weight: 600; }
.lang-toggle:hover { background: var(--blue); }
.target-banner { text-align: center; padding: 28px; }
.target-banner .target-text { font-size: 1.1em; color: var(--text); }
.thesis-text { font-size: 1.05em; line-height: 1.7; }
</style>"""


# ---------------------------------------------------------------------------
# Toggle JS
# ---------------------------------------------------------------------------


def _toggle_js() -> str:
    return """<script>
function toggleLang() {
  var html = document.documentElement;
  var btn = document.getElementById('lang-btn');
  if (html.lang === 'en') {
    html.lang = 'ru';
    btn.textContent = 'EN';
    document.querySelectorAll('.i18n').forEach(function(el) {
      if (el.dataset.ru) el.textContent = el.dataset.ru;
    });
  } else {
    html.lang = 'en';
    btn.textContent = 'RU';
    document.querySelectorAll('.i18n').forEach(function(el) {
      if (el.dataset.en) el.textContent = el.dataset.en;
    });
  }
}
</script>"""


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _header_section(r: InvestmentIdeaResult) -> str:
    signal = r.consensus.consensus_signal
    badge_class = f"badge-{signal.lower()}"
    price_str = fmt_price(r.current_price, r.ticker)
    date_str = datetime.now().strftime("%Y-%m-%d")
    signal_span = i18n_span(signal, SIGNALS)
    return f"""<div class="section header">
<h1>{r.ticker}</h1>
<p style="font-size:1.4em">{price_str}</p>
<p><span class="badge {badge_class}">{signal_span}</span>
   Score: {r.consensus.consensus_score:.0f}/100 |
   Confidence: {r.consensus.consensus_confidence:.0%} |
   Agreement: {r.consensus.agreement:.0%}</p>
<p style="color:#888; margin-top:8px">{date_str}</p>
</div>"""


def _thesis_section(r: InvestmentIdeaResult) -> str:
    thesis = generate_thesis(r)
    thesis_span = (
        f'<span class="i18n" data-en="{thesis.en}" data-ru="{thesis.ru}">'
        f"{thesis.en}</span>"
    )
    return (
        f'<div class="section">'
        f"<h2>{i18n_span('investment_thesis', HEADERS)}</h2>"
        f'<p class="thesis-text">{thesis_span}</p></div>'
    )


def _analyst_estimates_section(r: InvestmentIdeaResult) -> str:
    """Wall Street analyst estimates: targets, ratings, earnings history."""
    ae = r.analyst_estimates
    if ae is None:
        return ""

    header = i18n_span("analyst_estimates", HEADERS)

    # Ratings badge
    rating_html = ""
    if ae.recommendation:
        badge_color = {
            "strong_buy": "#00d68f", "buy": "#00d68f",
            "hold": "#ffd93d", "neutral": "#ffd93d",
            "sell": "#ff6b6b", "strong_sell": "#ff6b6b",
        }.get(ae.recommendation, "#aaa")
        analysts_text = f" ({ae.num_analysts} analysts)" if ae.num_analysts else ""
        rating_html = (
            f'<div style="text-align:center;margin:12px 0">'
            f'<span style="background:{badge_color};color:#111;padding:6px 18px;'
            f'border-radius:20px;font-weight:bold;font-size:1.2em">'
            f'{ae.recommendation.upper()}</span>'
            f'<span style="color:#aaa;margin-left:8px">{analysts_text}</span></div>'
        )

    # Target price gauge
    target_html = ""
    if ae.target_low and ae.target_high and ae.target_mean:
        current = r.current_price or 0
        upside = ((ae.target_mean / current) - 1) * 100 if current > 0 else 0
        upside_color = "#00d68f" if upside > 0 else "#ff6b6b"
        target_html = (
            f'<div class="metric-grid" style="margin:12px 0">'
            f'<div class="metric-card"><div class="metric-value">'
            f'${ae.target_low:,.0f}</div><div class="metric-label">Low</div></div>'
            f'<div class="metric-card"><div class="metric-value">'
            f'${ae.target_mean:,.0f}</div><div class="metric-label">Mean</div></div>'
            f'<div class="metric-card"><div class="metric-value">'
            f'${ae.target_high:,.0f}</div><div class="metric-label">High</div></div>'
            f'<div class="metric-card"><div class="metric-value" '
            f'style="color:{upside_color}">{upside:+.1f}%</div>'
            f'<div class="metric-label">Upside (Mean)</div></div></div>'
        )

    # Forward estimates
    fwd_html = ""
    fwd_parts = []
    if ae.forward_pe:
        fwd_parts.append(f"Forward P/E: {ae.forward_pe:.1f}")
    if ae.forward_eps:
        fwd_parts.append(f"Forward EPS: ${ae.forward_eps:.2f}")
    if fwd_parts:
        fwd_html = (
            f'<p style="text-align:center;color:#aaa;margin:8px 0">'
            f'{" &bull; ".join(fwd_parts)}</p>'
        )

    # Earnings history table
    earnings_html = ""
    if ae.earnings_history:
        rows = ""
        for e in ae.earnings_history[:8]:
            surprise_color = (
                "#00d68f" if e.surprise_pct and e.surprise_pct > 0
                else "#ff6b6b" if e.surprise_pct and e.surprise_pct < 0
                else "#aaa"
            )
            est = f"${e.eps_estimate:.2f}" if e.eps_estimate is not None else "—"
            act = f"${e.eps_actual:.2f}" if e.eps_actual is not None else "—"
            surp = (
                f'<span style="color:{surprise_color}">{e.surprise_pct:+.1f}%</span>'
                if e.surprise_pct is not None else "—"
            )
            rows += f"<tr><td>{e.period}</td><td>{est}</td><td>{act}</td><td>{surp}</td></tr>"
        earnings_html = (
            '<table class="metric-table" style="margin-top:12px">'
            "<thead><tr><th>Period</th><th>EPS Est.</th>"
            "<th>EPS Actual</th><th>Surprise</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    return (
        f'<div class="section">'
        f"<h2>{header}</h2>"
        f"{rating_html}{target_html}{fwd_html}{earnings_html}</div>"
    )


def _target_price_section(r: InvestmentIdeaResult) -> str:
    summary = generate_target_summary(r)
    summary_span = (
        f'<span class="i18n" data-en="{summary.en}" data-ru="{summary.ru}">'
        f"{summary.en}</span>"
    )
    return (
        f'<div class="section target-banner">'
        f"<h2>{i18n_span('target_price', HEADERS)}</h2>"
        f'<p class="target-text">{summary_span}</p></div>'
    )


def _price_chart_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("price_chart", HEADERS)
    if not r.price_history:
        return f'<div class="section"><h2>{header}</h2><p>No price data</p></div>'

    dates = [p.get("date", "") for p in r.price_history]
    closes = [p.get("close", 0) for p in r.price_history]
    volumes = [p.get("volume", 0) for p in r.price_history]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.7, 0.3])

    fig.add_trace(go.Scatter(x=dates, y=closes, mode="lines",  # type: ignore[attr-defined,no-untyped-call]
                             name="Close", line={"color": "#4fc3f7"}), row=1, col=1)
    fig.add_trace(go.Bar(x=dates, y=volumes, name="Volume",  # type: ignore[attr-defined,no-untyped-call]
                         marker_color="rgba(79,195,247,0.3)"), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e", plot_bgcolor="#16213e",
        showlegend=False, height=500,
        margin={"l": 50, "r": 20, "t": 20, "b": 20},
    )

    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
    return f'<div class="section"><h2>{header}</h2>{chart_html}</div>'


def _consensus_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("agent_consensus", HEADERS)
    bars = ""
    for name, ar in r.consensus.agent_results.items():
        color = "#00d68f" if ar.signal == "Bullish" else (
            "#ff6b6b" if ar.signal == "Bearish" else "#ffd93d"
        )
        bars += f"""<div class="score-bar">
<span class="label">{name}</span>
<div class="bar-bg"><div class="bar-fill" style="width:{ar.score}%;background:{color}"></div></div>
<span class="value">{ar.score:.0f}</span>
</div>"""

    errors = ""
    if r.consensus.agent_errors:
        errors = '<div class="warnings">'
        for name, err in r.consensus.agent_errors.items():
            errors += f"<p>{name}: {err}</p>"
        errors += "</div>"

    return f'<div class="section"><h2>{header}</h2>{bars}{errors}</div>'


def _fundamental_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("fundamental_snapshot", HEADERS)
    rows = ""
    for category, metrics in [
        ("Profitability", r.fundamentals.profitability),
        ("Valuation", r.fundamentals.valuation),
        ("Stability", r.fundamentals.stability),
    ]:
        for key, val in metrics.items():
            formatted = _format_metric(key, val)
            label = i18n_span(key, METRIC_LABELS)
            rows += f"<tr><td>{category}</td><td>{label}</td><td>{formatted}</td></tr>"

    return f"""<div class="section"><h2>{header}</h2>
<table><tr><th>Category</th><th>Metric</th><th>Value</th></tr>{rows}</table></div>"""


def _fcf_waterfall_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("fcf_waterfall", HEADERS)
    w = r.fcf_waterfall
    if w.ebitda is None:
        return f'<div class="section"><h2>{header}</h2><p>No data</p></div>'

    labels = ["EBITDA", "CAPEX", "Interest", "Taxes", "FCF"]
    values = [
        w.ebitda or 0,
        -(w.capex or 0),
        -(w.interest_expense or 0),
        -(w.taxes or 0),
        w.fcf or 0,
    ]
    measures = ["absolute", "relative", "relative", "relative", "total"]

    fig = go.Figure(go.Waterfall(  # type: ignore[attr-defined,no-untyped-call]
        x=labels, y=values, measure=measures,
        connector={"line": {"color": "#4fc3f7", "width": 1}},
        increasing={"marker": {"color": "#00d68f"}},
        decreasing={"marker": {"color": "#ff6b6b"}},
        totals={"marker": {"color": "#4fc3f7"}},
    ))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#16213e", plot_bgcolor="#16213e",
        height=350, margin={"l": 50, "r": 20, "t": 20, "b": 40},
    )

    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)  # type: ignore[no-untyped-call]
    fcf_ps = f"<p>FCF/Share: {fmt_price(w.fcf_per_share, r.ticker)}</p>" if w.fcf_per_share else ""

    narrative = generate_fcf_narrative(r)
    narrative_span = (
        f'<span class="i18n" data-en="{narrative.en}" data-ru="{narrative.ru}">'
        f"{narrative.en}</span>"
    )
    narrative_html = f"<p style=\"margin-top:12px\">{narrative_span}</p>"

    return (
        f'<div class="section"><h2>{header}</h2>'
        f"{chart_html}{fcf_ps}{narrative_html}</div>"
    )


def _historical_trends_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("historical_trends", HEADERS)
    parts: list[str] = []
    cagr_text = ""
    if r.revenue_cagr_3y is not None:
        cagr_text += f"Revenue CAGR (3Y): {r.revenue_cagr_3y:.1%} | "
    if r.ebitda_cagr_3y is not None:
        cagr_text += f"EBITDA CAGR (3Y): {r.ebitda_cagr_3y:.1%}"
    if cagr_text:
        parts.append(f"<p>{cagr_text}</p>")
    content = "".join(parts) or "<p>No history</p>"
    return f'<div class="section"><h2>{header}</h2>{content}</div>'


def _scenario_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("scenario_valuation", HEADERS)
    if not r.scenarios:
        return f'<div class="section"><h2>{header}</h2><p>No data</p></div>'

    rows = ""
    for s in r.scenarios:
        label_map = {"bull": "bullish", "bear": "bearish"}
        badge = f'badge-{label_map.get(s.label, "neutral")}'
        tp = fmt_price(s.target_price, r.ticker) if s.target_price is not None else "N/A"
        up = f"{s.upside_pct:+.1f}%" if s.upside_pct is not None else "N/A"
        febitda = _fmt_large(s.forward_ebitda) if s.forward_ebitda else "N/A"
        ev_ebitda = f"{s.target_ev_ebitda:.1f}x" if s.target_ev_ebitda is not None else "N/A"
        rows += f"""<tr><td><span class="badge {badge}">{s.label.upper()}</span></td>
<td>{febitda}</td><td>{ev_ebitda}</td><td>{tp}</td><td>{up}</td></tr>"""

    thead = (
        "<th>Scenario</th><th>Fwd EBITDA</th><th>EV/EBITDA</th>"
        "<th>Target Price</th><th>Upside</th>"
    )
    return f"""<div class="section"><h2>{header}</h2>
<table><tr>{thead}</tr>
{rows}</table></div>"""


def _catalysts_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("catalysts", HEADERS)
    no_data = (
        '<span class="i18n" data-en="No catalysts detected" '
        'data-ru="Катализаторы не обнаружены">No catalysts detected</span>'
    )
    if not r.catalysts:
        return f'<div class="section"><h2>{header}</h2><p>{no_data}</p></div>'

    cards = ""
    for c in r.catalysts:
        badge = f'badge-{c.sentiment}'
        link = (
            f'<a href="{c.source_url}" style="color:var(--blue)">source</a>'
            if c.source_url else ""
        )
        cards += f"""<div class="card">
<h3>{c.category.replace("_"," ").title()} <span class="badge {badge}">{c.sentiment}</span></h3>
<p>{c.description}</p>{link}</div>"""

    return f'<div class="section"><h2>{header}</h2><div class="card-grid">{cards}</div></div>'


def _risks_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("risk_catalog", HEADERS)
    no_data = (
        '<span class="i18n" data-en="No significant risks" '
        'data-ru="Значимых рисков не выявлено">No significant risks</span>'
    )
    if not r.risks:
        return f'<div class="section"><h2>{header}</h2><p>{no_data}</p></div>'

    th_cat = (
        '<span class="i18n" data-en="Category" '
        'data-ru="Категория">Category</span>'
    )
    th_desc = (
        '<span class="i18n" data-en="Description" '
        'data-ru="Описание">Description</span>'
    )
    th_sev = (
        '<span class="i18n" data-en="Severity" '
        'data-ru="Серьёзность">Severity</span>'
    )
    rows = ""
    for risk in r.risks:
        badge = f'badge-{risk.severity}'
        rows += f"""<tr><td>{risk.category.replace("_"," ").title()}</td>
<td>{risk.description}</td>
<td><span class="badge {badge}">{risk.severity.upper()}</span></td></tr>"""

    return f"""<div class="section"><h2>{header}</h2>
<table><tr><th>{th_cat}</th><th>{th_desc}</th><th>{th_sev}</th></tr>
{rows}</table></div>"""


def _technical_section(r: InvestmentIdeaResult) -> str:
    header = i18n_span("technical_signals", HEADERS)
    t = r.technical
    signals_html = ""
    for name, sig in t.signals.items():
        signals_html += f"<tr><td>{name}</td><td>{sig}</td></tr>"

    rsi_str = f"{t.rsi:.1f}" if t.rsi else "N/A"
    bias_badge = f'badge-{t.overall_bias.lower()}'
    bias_span = i18n_span(t.overall_bias, SIGNALS)

    th_sig = (
        '<span class="i18n" data-en="Signal" '
        'data-ru="Сигнал">Signal</span>'
    )
    th_val = (
        '<span class="i18n" data-en="Value" '
        'data-ru="Значение">Value</span>'
    )
    return f"""<div class="section"><h2>{header}</h2>
<p>RSI: {rsi_str} | Bias: <span class="badge {bias_badge}">{bias_span}</span></p>
<table><tr><th>{th_sig}</th><th>{th_val}</th></tr>{signals_html}</table></div>"""


def _disclaimer_section() -> str:
    disclaimer_span = (
        f'<span class="i18n" data-en="{DISCLAIMER.en}" '
        f'data-ru="{DISCLAIMER.ru}">{DISCLAIMER.en}</span>'
    )
    return f"""<div class="disclaimer">
<p>{disclaimer_span}</p>
<p>Generated by fin-toolkit</p>
</div>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_metric(key: str, val: float | None) -> str:
    if val is None:
        return "N/A"
    if "ratio" in key or key in ("roe", "roa", "roic"):
        return f"{val:.2f}"
    if "yield" in key or "margin" in key:
        return f"{val:.2%}"
    return f"{val:,.2f}"


def _fmt_large(val: float | None) -> str:
    if val is None:
        return "N/A"
    if abs(val) >= 1e9:
        return f"${val / 1e9:,.1f}B"
    if abs(val) >= 1e6:
        return f"${val / 1e6:,.1f}M"
    return f"${val:,.0f}"
