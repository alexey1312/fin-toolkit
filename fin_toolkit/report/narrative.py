"""Template-based narrative generation for investment reports."""

from __future__ import annotations

from fin_toolkit.models.results import InvestmentIdeaResult
from fin_toolkit.report.i18n import SIGNALS, LangPair


def _fmt_large(val: float) -> str:
    """Format large numbers as B/M."""
    if abs(val) >= 1e9:
        return f"{val / 1e9:,.1f}B"
    if abs(val) >= 1e6:
        return f"{val / 1e6:,.1f}M"
    return f"{val:,.0f}"


def generate_thesis(result: InvestmentIdeaResult) -> LangPair:
    """Generate an investment thesis from analysis results.

    Assembles a narrative from: consensus signal/score, top agent rationale,
    strongest catalyst, key valuation metrics, CAGR, and target upside.
    """
    signal = result.consensus.consensus_signal
    score = result.consensus.consensus_score
    signal_pair = SIGNALS.get(signal, LangPair(en=signal, ru=signal))

    # Top agent rationale (highest confidence)
    top_rationale = ""
    if result.consensus.agent_results:
        top_agent = max(
            result.consensus.agent_results.values(),
            key=lambda a: a.confidence,
        )
        top_rationale = top_agent.rationale

    # Strongest catalyst
    catalyst_text_en = ""
    catalyst_text_ru = ""
    if result.catalysts:
        cat = result.catalysts[0]
        catalyst_text_en = f" Key catalyst: {cat.description}."
        catalyst_text_ru = f" Ключевой катализатор: {cat.description}."

    # Growth
    growth_en = ""
    growth_ru = ""
    if result.revenue_cagr_3y is not None:
        growth_en += f" Revenue CAGR {result.revenue_cagr_3y:.1%}."
        growth_ru += f" CAGR выручки {result.revenue_cagr_3y:.1%}."
    if result.ebitda_cagr_3y is not None:
        growth_en += f" EBITDA CAGR {result.ebitda_cagr_3y:.1%}."
        growth_ru += f" CAGR EBITDA {result.ebitda_cagr_3y:.1%}."

    # Target upside from base scenario
    upside_en = ""
    upside_ru = ""
    base = next((s for s in result.scenarios if s.label == "base"), None)
    if base and base.upside_pct is not None:
        upside_en = f" Base-case upside: {base.upside_pct:+.1f}%."
        upside_ru = f" Потенциал роста (базовый): {base.upside_pct:+.1f}%."

    en = (
        f"Consensus: {signal_pair.en} ({score:.0f}/100). "
        f"{top_rationale}{catalyst_text_en}{growth_en}{upside_en}"
    ).strip()

    ru = (
        f"Консенсус: {signal_pair.ru} ({score:.0f}/100). "
        f"{top_rationale}{catalyst_text_ru}{growth_ru}{upside_ru}"
    ).strip()

    return LangPair(en=en, ru=ru)


def generate_fcf_narrative(result: InvestmentIdeaResult) -> LangPair:
    """Generate a narrative for the FCF waterfall.

    Describes the path: EBITDA -> minus CAPEX -> minus Interest -> minus Taxes -> FCF.
    """
    w = result.fcf_waterfall
    if w.ebitda is None:
        return LangPair(
            en="Free cash flow data is not available.",
            ru="Данные по свободному денежному потоку недоступны.",
        )

    parts_en: list[str] = [f"EBITDA of {_fmt_large(w.ebitda)}"]
    parts_ru: list[str] = [f"EBITDA {_fmt_large(w.ebitda)}"]

    if w.capex is not None:
        parts_en.append(f"minus CAPEX {_fmt_large(w.capex)}")
        parts_ru.append(f"минус CAPEX {_fmt_large(w.capex)}")
    if w.interest_expense is not None:
        parts_en.append(f"minus interest {_fmt_large(w.interest_expense)}")
        parts_ru.append(f"минус проценты {_fmt_large(w.interest_expense)}")
    if w.taxes is not None:
        parts_en.append(f"minus taxes {_fmt_large(w.taxes)}")
        parts_ru.append(f"минус налоги {_fmt_large(w.taxes)}")

    fcf_str = ""
    fcf_str_ru = ""
    if w.fcf is not None:
        fcf_str = f" → FCF of {_fmt_large(w.fcf)}"
        fcf_str_ru = f" → FCF {_fmt_large(w.fcf)}"
        if w.fcf_per_share is not None:
            fcf_str += f" ({w.fcf_per_share:.2f}/share)"
            fcf_str_ru += f" ({w.fcf_per_share:.2f}/акцию)"

    en = ", ".join(parts_en) + fcf_str + "."
    ru = ", ".join(parts_ru) + fcf_str_ru + "."
    return LangPair(en=en, ru=ru)


def generate_target_summary(result: InvestmentIdeaResult) -> LangPair:
    """Generate a target price summary from scenarios."""
    if not result.scenarios:
        return LangPair(
            en="No scenario valuation available.",
            ru="Сценарная оценка недоступна.",
        )

    base = next((s for s in result.scenarios if s.label == "base"), None)
    bull = next((s for s in result.scenarios if s.label == "bull"), None)
    bear = next((s for s in result.scenarios if s.label == "bear"), None)

    parts_en: list[str] = []
    parts_ru: list[str] = []

    if base and base.target_price is not None:
        up = f" ({base.upside_pct:+.1f}%)" if base.upside_pct is not None else ""
        parts_en.append(f"Base target: ${base.target_price:,.2f}{up}")
        parts_ru.append(f"Базовая цель: ${base.target_price:,.2f}{up}")

    if bull and bull.target_price is not None:
        parts_en.append(f"Bull: ${bull.target_price:,.2f}")
        parts_ru.append(f"Бычий: ${bull.target_price:,.2f}")

    if bear and bear.target_price is not None:
        parts_en.append(f"Bear: ${bear.target_price:,.2f}")
        parts_ru.append(f"Медвежий: ${bear.target_price:,.2f}")

    if not parts_en:
        return LangPair(
            en="No target price available.",
            ru="Целевая цена недоступна.",
        )

    en = " | ".join(parts_en) + "."
    ru = " | ".join(parts_ru) + "."
    return LangPair(en=en, ru=ru)
