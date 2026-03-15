"""HTML report generator with Plotly charts for investment ideas."""

from __future__ import annotations

from datetime import datetime

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from fin_toolkit.models.results import InvestmentIdeaResult


def render_investment_idea_html(result: InvestmentIdeaResult) -> str:
    """Render InvestmentIdeaResult as self-contained HTML with Plotly charts."""
    sections: list[str] = [
        _header_section(result),
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
<div class="container">
{body}
</div>
</body>
</html>"""


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
</style>"""


def _header_section(r: InvestmentIdeaResult) -> str:
    signal = r.consensus.consensus_signal
    badge_class = f"badge-{signal.lower()}"
    price_str = f"${r.current_price:,.2f}" if r.current_price else "N/A"
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"""<div class="section header">
<h1>{r.ticker}</h1>
<p style="font-size:1.4em">{price_str}</p>
<p><span class="badge {badge_class}">{signal}</span>
   Score: {r.consensus.consensus_score:.0f}/100 |
   Confidence: {r.consensus.consensus_confidence:.0%} |
   Agreement: {r.consensus.agreement:.0%}</p>
<p style="color:#888; margin-top:8px">{date_str}</p>
</div>"""


def _price_chart_section(r: InvestmentIdeaResult) -> str:
    if not r.price_history:
        return '<div class="section"><h2>Price Chart</h2><p>No price data</p></div>'

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
    return f'<div class="section"><h2>Price Chart</h2>{chart_html}</div>'


def _consensus_section(r: InvestmentIdeaResult) -> str:
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

    return f'<div class="section"><h2>Agent Consensus</h2>{bars}{errors}</div>'


def _fundamental_section(r: InvestmentIdeaResult) -> str:
    rows = ""
    for category, metrics in [
        ("Profitability", r.fundamentals.profitability),
        ("Valuation", r.fundamentals.valuation),
        ("Stability", r.fundamentals.stability),
    ]:
        for key, val in metrics.items():
            formatted = _format_metric(key, val)
            rows += f"<tr><td>{category}</td><td>{key}</td><td>{formatted}</td></tr>"

    return f"""<div class="section"><h2>Fundamental Snapshot</h2>
<table><tr><th>Category</th><th>Metric</th><th>Value</th></tr>{rows}</table></div>"""


def _fcf_waterfall_section(r: InvestmentIdeaResult) -> str:
    w = r.fcf_waterfall
    if w.ebitda is None:
        return '<div class="section"><h2>FCF Waterfall</h2><p>No data</p></div>'

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
    fcf_ps = f"<p>FCF/Share: ${w.fcf_per_share:,.2f}</p>" if w.fcf_per_share else ""
    return f'<div class="section"><h2>FCF Waterfall</h2>{chart_html}{fcf_ps}</div>'


def _historical_trends_section(r: InvestmentIdeaResult) -> str:
    parts: list[str] = []
    cagr_text = ""
    if r.revenue_cagr_3y is not None:
        cagr_text += f"Revenue CAGR (3Y): {r.revenue_cagr_3y:.1%} | "
    if r.ebitda_cagr_3y is not None:
        cagr_text += f"EBITDA CAGR (3Y): {r.ebitda_cagr_3y:.1%}"
    if cagr_text:
        parts.append(f"<p>{cagr_text}</p>")
    content = "".join(parts) or "<p>No history</p>"
    return f'<div class="section"><h2>Historical Trends</h2>{content}</div>'


def _scenario_section(r: InvestmentIdeaResult) -> str:
    if not r.scenarios:
        return '<div class="section"><h2>Scenario Valuation</h2><p>No data</p></div>'

    rows = ""
    for s in r.scenarios:
        label_map = {"bull": "bullish", "bear": "bearish"}
        badge = f'badge-{label_map.get(s.label, "neutral")}'
        tp = f"${s.target_price:,.2f}" if s.target_price is not None else "N/A"
        up = f"{s.upside_pct:+.1f}%" if s.upside_pct is not None else "N/A"
        febitda = _fmt_large(s.forward_ebitda) if s.forward_ebitda else "N/A"
        rows += f"""<tr><td><span class="badge {badge}">{s.label.upper()}</span></td>
<td>{febitda}</td><td>{tp}</td><td>{up}</td></tr>"""

    return f"""<div class="section"><h2>Scenario Valuation</h2>
<table><tr><th>Scenario</th><th>Fwd EBITDA</th><th>Target Price</th><th>Upside</th></tr>
{rows}</table></div>"""


def _catalysts_section(r: InvestmentIdeaResult) -> str:
    if not r.catalysts:
        return '<div class="section"><h2>Catalysts</h2><p>No catalysts detected</p></div>'

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

    return f'<div class="section"><h2>Catalysts</h2><div class="card-grid">{cards}</div></div>'


def _risks_section(r: InvestmentIdeaResult) -> str:
    if not r.risks:
        return '<div class="section"><h2>Risk Catalog</h2><p>No significant risks</p></div>'

    rows = ""
    for risk in r.risks:
        badge = f'badge-{risk.severity}'
        rows += f"""<tr><td>{risk.category.replace("_"," ").title()}</td>
<td>{risk.description}</td>
<td><span class="badge {badge}">{risk.severity.upper()}</span></td></tr>"""

    return f"""<div class="section"><h2>Risk Catalog</h2>
<table><tr><th>Category</th><th>Description</th><th>Severity</th></tr>{rows}</table></div>"""


def _technical_section(r: InvestmentIdeaResult) -> str:
    t = r.technical
    signals_html = ""
    for name, sig in t.signals.items():
        signals_html += f"<tr><td>{name}</td><td>{sig}</td></tr>"

    rsi_str = f"{t.rsi:.1f}" if t.rsi else "N/A"
    bias_badge = f'badge-{t.overall_bias.lower()}'

    return f"""<div class="section"><h2>Technical Signals</h2>
<p>RSI: {rsi_str} | Bias: <span class="badge {bias_badge}">{t.overall_bias}</span></p>
<table><tr><th>Signal</th><th>Value</th></tr>{signals_html}</table></div>"""


def _disclaimer_section() -> str:
    return """<div class="disclaimer">
<p>This report is for informational purposes only and does not constitute
investment advice. Past performance is not indicative of future results.
Always conduct your own research before making investment decisions.</p>
<p>Generated by fin-toolkit</p>
</div>"""


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
