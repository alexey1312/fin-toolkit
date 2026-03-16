"""Investment idea pure functions — CAGR, FCF waterfall, scenarios, catalysts, risks."""

from __future__ import annotations

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.results import (
    CatalystItem,
    FCFWaterfall,
    RiskItem,
    RiskResult,
    ScenarioValuation,
    SearchResult,
)

# ---------------------------------------------------------------------------
# CAGR
# ---------------------------------------------------------------------------


def compute_cagr(values: list[float], years: int) -> float | None:
    """Compound Annual Growth Rate from a list of annual values.

    Returns None if data is insufficient or invalid.
    """
    if len(values) < 2 or years <= 0:
        return None
    first, last = values[0], values[-1]
    if first <= 0 or last <= 0:
        return None
    return float((last / first) ** (1.0 / years) - 1.0)


# ---------------------------------------------------------------------------
# FCF Waterfall
# ---------------------------------------------------------------------------


def compute_fcf_waterfall(
    financials: FinancialStatements,
    metrics: KeyMetrics,
) -> FCFWaterfall:
    """Compute FCF waterfall from financial statements and metrics."""
    inc = financials.income_statement or {}
    cf = financials.cash_flow or {}

    ebitda = _float_or_none(inc.get("ebitda"))
    capex = _float_or_none(cf.get("capital_expenditures"))
    interest = _float_or_none(inc.get("interest_expense"))
    shares = metrics.shares_outstanding

    # Effective tax rate: net_income / ebit, fallback 25%
    net_income = _float_or_none(inc.get("net_income"))
    ebit = _float_or_none(inc.get("ebit"))
    if net_income is not None and ebit is not None and ebit != 0:
        tax_rate = max(0.0, 1.0 - net_income / ebit)
    else:
        tax_rate = 0.25

    # Compute taxes and FCF
    taxes: float | None = None
    fcf: float | None = None
    if ebitda is not None:
        capex_val = abs(capex) if capex is not None else 0.0
        interest_val = abs(interest) if interest is not None else 0.0
        ebt = ebitda - capex_val - interest_val
        taxes = ebt * tax_rate if ebt > 0 else 0.0
        fcf = ebt - taxes

    fcf_per_share: float | None = None
    if fcf is not None and shares is not None and shares > 0:
        fcf_per_share = fcf / shares

    return FCFWaterfall(
        ebitda=ebitda,
        capex=abs(capex) if capex is not None else None,
        interest_expense=abs(interest) if interest is not None else None,
        taxes=taxes,
        fcf=fcf,
        shares_outstanding=shares,
        fcf_per_share=fcf_per_share,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def compute_scenarios(
    current_price: float,
    ebitda: float | None,
    ebitda_cagr: float | None,
    ev_ebitda_multiple: float | None,
    ev: float | None,
    net_debt: float | None,
    shares: float | None,
) -> list[ScenarioValuation]:
    """Compute bull/base/bear scenario valuations."""
    multipliers = {"bull": 1.3, "base": 1.0, "bear": 0.7}
    scenarios: list[ScenarioValuation] = []

    for label, mult in multipliers.items():
        if ebitda is None or ebitda_cagr is None or ev_ebitda_multiple is None:
            scenarios.append(ScenarioValuation(
                label=label,
                forward_ebitda=None,
                forward_eps=None,
                target_ev_ebitda=None,
                target_pe=None,
                target_price=None,
                upside_pct=None,
            ))
            continue

        cagr_adj = ebitda_cagr * mult
        forward_ebitda = ebitda * (1 + cagr_adj)
        target_ev = forward_ebitda * ev_ebitda_multiple

        target_price: float | None = None
        upside_pct: float | None = None
        if net_debt is not None and shares is not None and shares > 0:
            equity_value = target_ev - net_debt
            target_price = equity_value / shares
            if current_price > 0:
                upside_pct = (target_price - current_price) / current_price * 100

        scenarios.append(ScenarioValuation(
            label=label,
            forward_ebitda=forward_ebitda,
            forward_eps=None,
            target_ev_ebitda=ev_ebitda_multiple,
            target_pe=None,
            target_price=target_price,
            upside_pct=upside_pct,
        ))

    return scenarios


# ---------------------------------------------------------------------------
# Catalyst classification
# ---------------------------------------------------------------------------

_CATALYST_KEYWORDS: dict[str, tuple[list[str], str]] = {
    "m_and_a": (
        [
            "merger", "acquisition", "acquire", "takeover", "m&a",
            "слияние", "поглощение", "покупка актив",
        ],
        "positive",
    ),
    "buyback": (
        [
            "buyback", "repurchase", "share buyback",
            "обратный выкуп", "байбэк",
        ],
        "positive",
    ),
    "restructuring": (
        [
            "restructuring", "spin-off", "spinoff", "divestiture",
            "layoff", "job cut", "workforce reduction",
            "реструктуризация", "выделение", "разделение",
            "сокращение", "увольнение",
        ],
        "neutral",
    ),
    "index": (
        [
            "index inclusion", "index addition", "s&p 500", "msci",
            "включение в индекс", "добавление в индекс",
        ],
        "positive",
    ),
    "strategic": (
        [
            "partnership", "joint venture", "strategic alliance",
            "contract", "deal", "supply deal", "chip deal",
            "infrastructure", "capex", "capital expenditure",
            "партнёрство", "совместное предприятие", "контракт",
            "инвестиции", "инфраструктура",
        ],
        "positive",
    ),
    "growth": (
        [
            "revenue growth", "earnings beat", "revenue beat",
            "record revenue", "profit surge", "raised guidance",
            "рост выручки", "рекордная прибыль",
        ],
        "positive",
    ),
    "innovation": (
        [
            "ai chip", "new product", "launch", "patent",
            "artificial intelligence", "ai model", "ai infrastructure",
            "новый продукт", "запуск", "патент", "нейросеть",
        ],
        "positive",
    ),
    "dividend": (
        [
            "dividend increase", "special dividend",
            "dividend initiat", "first dividend",
            "повышение дивиденд", "специальный дивиденд",
        ],
        "positive",
    ),
}


def classify_catalysts(search_results: list[SearchResult]) -> list[CatalystItem]:
    """Classify search results into catalyst categories using keyword matching."""
    catalysts: list[CatalystItem] = []
    for result in search_results:
        text = f"{result.title} {result.snippet}".lower()
        for category, (keywords, default_sentiment) in _CATALYST_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                catalysts.append(CatalystItem(
                    category=category,
                    description=result.title,
                    sentiment=default_sentiment,
                    source_url=result.url,
                ))
                break  # one category per result
    return catalysts


# ---------------------------------------------------------------------------
# Risk detection
# ---------------------------------------------------------------------------

_RISK_KEYWORDS: dict[str, tuple[list[str], str]] = {
    "regulatory": (
        [
            "sanctions", "investigation", "lawsuit", "penalty", "fine", "ban",
            "санкции", "расследование", "штраф", "запрет",
        ],
        "high",
    ),
    "esg": (
        [
            "esg", "environmental", "pollution", "carbon", "climate",
            "экология", "загрязнение", "углеродный",
        ],
        "medium",
    ),
    "operational": (
        [
            "supply chain", "shortage", "recall", "outage",
            "перебои", "дефицит", "отзыв продукции",
        ],
        "medium",
    ),
}


def detect_risks(
    fundamental_data: dict[str, object],
    risk: RiskResult,
    search_results: list[SearchResult],
) -> list[RiskItem]:
    """Detect risk factors from metrics, volatility, and news."""
    risks: list[RiskItem] = []

    stability = fundamental_data.get("stability", {})
    if isinstance(stability, dict):
        # Leverage risk
        de = stability.get("debt_to_equity")
        if isinstance(de, (int, float)) and de > 2.0:
            severity = "high" if de > 3.0 else "medium"
            risks.append(RiskItem(
                category="leverage",
                description=f"High debt-to-equity ratio: {de:.1f}",
                severity=severity,
            ))

        # Liquidity risk
        cr = stability.get("current_ratio")
        if isinstance(cr, (int, float)) and cr < 1.0:
            severity = "high" if cr < 0.5 else "medium"
            risks.append(RiskItem(
                category="liquidity",
                description=f"Low current ratio: {cr:.2f}",
                severity=severity,
            ))

        # Interest coverage risk
        ic = stability.get("interest_coverage")
        if isinstance(ic, (int, float)) and ic < 2.0:
            risks.append(RiskItem(
                category="leverage",
                description=f"Weak interest coverage: {ic:.1f}x",
                severity="high",
            ))

    # Volatility/macro risk
    if risk.volatility_252d is not None and risk.volatility_252d > 0.50:
        risks.append(RiskItem(
            category="macro",
            description=f"High annualized volatility: {risk.volatility_252d:.0%}",
            severity="high" if risk.volatility_252d > 0.70 else "medium",
        ))

    # Keyword-based risks from search results
    for result in search_results:
        text = f"{result.title} {result.snippet}".lower()
        for category, (keywords, default_severity) in _RISK_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                risks.append(RiskItem(
                    category=category,
                    description=result.title,
                    severity=default_severity,
                ))
                break

    return risks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _float_or_none(val: object) -> float | None:
    """Safely cast to float or return None."""
    if val is None:
        return None
    try:
        return float(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
