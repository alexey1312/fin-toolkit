"""Internationalization helpers for bilingual EN/RU reports."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class LangPair:
    """A bilingual text pair."""

    en: str
    ru: str


# ---------------------------------------------------------------------------
# Section headers
# ---------------------------------------------------------------------------

HEADERS: dict[str, LangPair] = {
    "investment_thesis": LangPair(en="Investment Thesis", ru="Инвестиционный тезис"),
    "target_price": LangPair(en="Target Price", ru="Целевая цена"),
    "price_chart": LangPair(en="Price Chart", ru="График цены"),
    "agent_consensus": LangPair(en="Agent Consensus", ru="Консенсус аналитиков"),
    "fundamental_snapshot": LangPair(en="Fundamental Snapshot", ru="Фундаментальный обзор"),
    "fcf_waterfall": LangPair(en="FCF Waterfall", ru="Водопад FCF"),
    "historical_trends": LangPair(en="Historical Trends", ru="Историческая динамика"),
    "scenario_valuation": LangPair(en="Scenario Valuation", ru="Сценарная оценка"),
    "catalysts": LangPair(en="Catalysts", ru="Катализаторы"),
    "risk_catalog": LangPair(en="Risk Catalog", ru="Каталог рисков"),
    "technical_signals": LangPair(en="Technical Signals", ru="Технические сигналы"),
    "disclaimer": LangPair(en="Disclaimer", ru="Дисклеймер"),
    "analyst_estimates": LangPair(
        en="Wall Street Analyst Estimates", ru="Оценки аналитиков Wall Street",
    ),
}

# ---------------------------------------------------------------------------
# Signal translations
# ---------------------------------------------------------------------------

SIGNALS: dict[str, LangPair] = {
    "Bullish": LangPair(en="Bullish", ru="Покупать"),
    "Bearish": LangPair(en="Bearish", ru="Продавать"),
    "Neutral": LangPair(en="Neutral", ru="Держать"),
}

# ---------------------------------------------------------------------------
# Metric labels
# ---------------------------------------------------------------------------

METRIC_LABELS: dict[str, LangPair] = {
    "pe_ratio": LangPair(en="P/E Ratio", ru="P/E"),
    "pb_ratio": LangPair(en="P/B Ratio", ru="P/B"),
    "ev_ebitda": LangPair(en="EV/EBITDA", ru="EV/EBITDA"),
    "fcf_yield": LangPair(en="FCF Yield", ru="Доходность FCF"),
    "dividend_yield": LangPair(en="Dividend Yield", ru="Дивидендная доходность"),
    "roe": LangPair(en="ROE", ru="ROE"),
    "roa": LangPair(en="ROA", ru="ROA"),
    "roic": LangPair(en="ROIC", ru="ROIC"),
    "net_margin": LangPair(en="Net Margin", ru="Чистая маржа"),
    "gross_margin": LangPair(en="Gross Margin", ru="Валовая маржа"),
    "debt_to_equity": LangPair(en="Debt/Equity", ru="Долг/Капитал"),
    "current_ratio": LangPair(en="Current Ratio", ru="Текущая ликвидность"),
    "interest_coverage": LangPair(en="Interest Coverage", ru="Покрытие процентов"),
    "market_cap": LangPair(en="Market Cap", ru="Капитализация"),
    "current_price": LangPair(en="Current Price", ru="Текущая цена"),
    "volatility_30d": LangPair(en="Volatility (30d)", ru="Волатильность (30д)"),
    "consensus_score": LangPair(en="Consensus Score", ru="Консенсус-оценка"),
    "consensus_signal": LangPair(en="Consensus Signal", ru="Консенсус-сигнал"),
}

# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

DISCLAIMER = LangPair(
    en=(
        "This report is for informational purposes only and does not constitute "
        "investment advice. Past performance is not indicative of future results. "
        "Always conduct your own research before making investment decisions."
    ),
    ru=(
        "Данный отчёт носит исключительно информационный характер и не является "
        "инвестиционной рекомендацией. Прошлые результаты не гарантируют будущую доходность. "
        "Всегда проводите собственный анализ перед принятием инвестиционных решений."
    ),
)

# ---------------------------------------------------------------------------
# Known Russian tickers (MOEX equities)
# ---------------------------------------------------------------------------

_RU_TICKERS: frozenset[str] = frozenset({
    "SBER", "GAZP", "LKOH", "VTBR", "MGNT", "ROSN", "NVTK", "TATN",
    "POLY", "RASP", "YNDX", "OZON", "FIVE", "PIKK", "ALRS", "CHMF",
    "MOEX", "NLMK", "MAGN", "GMKN", "PLZL", "SNGS", "TRNFP", "RUAL",
    "AFLT", "MTSS", "RTKM", "IRAO", "FEES", "HYDR", "PHOR", "SGZH",
    "AFKS", "TCSG",
})

# ---------------------------------------------------------------------------
# Known Kazakhstan tickers (KASE equities)
# ---------------------------------------------------------------------------

_KZ_TICKERS: frozenset[str] = frozenset({
    "KCEL", "AIRA", "HSBK", "KZTO", "KEGC", "CCBN", "KZAP",
    "BTAS", "KZTK", "GB_KZMS",
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def i18n_span(key: str, translations: dict[str, LangPair]) -> str:
    """Render a bilingual span element.

    Returns ``<span class="i18n" data-en="..." data-ru="...">EN text</span>``.
    Falls back to the key itself if not found.
    """
    pair = translations.get(key)
    if pair is None:
        return f'<span class="i18n">{escape(key)}</span>'
    return (
        f'<span class="i18n" data-en="{escape(pair.en)}" '
        f'data-ru="{escape(pair.ru)}">{escape(pair.en)}</span>'
    )


def currency_symbol(ticker: str) -> str:
    """Return the currency symbol for a ticker.

    Suffix-based overrides take priority (GDR on foreign exchange = USD),
    then bare tickers are checked against known RU/KZ sets.
    """
    upper = ticker.upper()
    if upper.endswith(".ME"):
        return "₽"
    base = upper.split(".")[0]
    # Suffixed tickers (.IL, .L, etc.) are foreign-listed GDRs → USD
    if "." in upper:
        if base in _RU_TICKERS:
            return "₽"
        return "$"
    if base in _RU_TICKERS:
        return "₽"
    if base in _KZ_TICKERS:
        return "₸"
    return "$"


def fmt_price(value: float | None, ticker: str) -> str:
    """Format a price value with the appropriate currency symbol."""
    if value is None:
        return "N/A"
    sym = currency_symbol(ticker)
    return f"{sym}{value:,.2f}"
