"""Fundamental analysis: profitability, valuation, stability ratios with sector comparison."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.results import FundamentalResult

_SECTOR_MEDIANS_PATH = Path(__file__).resolve().parent.parent / "references" / "sector_medians.json"

_INVERTED_METRICS = frozenset({"debt_to_equity"})


def _safe_get(d: dict[str, Any] | None, key: str) -> float | None:
    """Safely extract a float from a dict, returning None if missing or non-numeric."""
    if d is None:
        return None
    val = d.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    """Safe division returning None when inputs are missing or denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


class FundamentalAnalyzer:
    """Computes fundamental ratios and optional sector comparison."""

    def __init__(self) -> None:
        self._sector_medians: dict[str, dict[str, float]] = {}
        if _SECTOR_MEDIANS_PATH.exists():
            with open(_SECTOR_MEDIANS_PATH) as f:
                self._sector_medians = json.load(f)

    def analyze(
        self,
        financials: FinancialStatements,
        metrics: KeyMetrics,
        sector: str | None = None,
    ) -> FundamentalResult:
        """Run fundamental analysis on the given financial data."""
        warnings: list[str] = []

        profitability = self._compute_profitability(financials, metrics, warnings)
        valuation = self._compute_valuation(financials, metrics, warnings)
        stability = self._compute_stability(financials, metrics, warnings)
        sector_comparison = self._compare_sector(profitability, valuation, stability, sector)

        return FundamentalResult(
            profitability=profitability,
            valuation=valuation,
            stability=stability,
            sector_comparison=sector_comparison,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Profitability
    # ------------------------------------------------------------------

    def _compute_profitability(
        self,
        fs: FinancialStatements,
        km: KeyMetrics,
        warnings: list[str],
    ) -> dict[str, float | None]:
        roe = km.roe
        roa = km.roa

        revenue = _safe_get(fs.income_statement, "revenue")
        net_income = _safe_get(fs.income_statement, "net_income")
        gross_profit = _safe_get(fs.income_statement, "gross_profit")
        operating_income = _safe_get(fs.income_statement, "operating_income")
        interest_expense = _safe_get(fs.income_statement, "interest_expense")
        invested_capital = _safe_get(fs.balance_sheet, "invested_capital")

        net_margin = _safe_div(net_income, revenue)
        gross_margin = _safe_div(gross_profit, revenue)

        # ROIC = NOPAT / invested_capital
        roic = self._compute_roic(
            operating_income, net_income, interest_expense, invested_capital, warnings,
        )

        return {
            "roe": roe,
            "roa": roa,
            "roic": roic,
            "net_margin": net_margin,
            "gross_margin": gross_margin,
        }

    @staticmethod
    def _compute_roic(
        operating_income: float | None,
        net_income: float | None,
        interest_expense: float | None,
        invested_capital: float | None,
        warnings: list[str],
    ) -> float | None:
        if operating_income is None or invested_capital is None:
            return None
        # Estimate effective tax rate from pre-tax income
        if interest_expense is not None and net_income is not None:
            pre_tax = operating_income - interest_expense
            if pre_tax > 0:
                tax_rate = 1.0 - (net_income / pre_tax)
            else:
                tax_rate = 0.21  # fallback to statutory US rate
                warnings.append("Could not estimate tax rate; using 21% default")
        else:
            tax_rate = 0.21
            warnings.append("Could not estimate tax rate; using 21% default")
        nopat = operating_income * (1.0 - tax_rate)
        return _safe_div(nopat, invested_capital)

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    def _compute_valuation(
        self,
        fs: FinancialStatements,
        km: KeyMetrics,
        warnings: list[str],
    ) -> dict[str, float | None]:
        pe_ratio = km.pe_ratio
        pb_ratio = km.pb_ratio
        dividend_yield = km.dividend_yield

        enterprise_value = _safe_get(fs.balance_sheet, "enterprise_value")
        ebitda = _safe_get(fs.income_statement, "ebitda")
        ev_ebitda = _safe_div(enterprise_value, ebitda)

        operating_cf = _safe_get(fs.cash_flow, "operating_cash_flow")
        capex = _safe_get(fs.cash_flow, "capital_expenditures")
        market_cap = km.market_cap

        if operating_cf is not None and capex is not None:
            fcf = operating_cf - capex
            fcf_yield = _safe_div(fcf, market_cap)
        else:
            fcf_yield = None

        if pe_ratio is None and pb_ratio is None and ev_ebitda is None:
            warnings.append("No valuation ratios available")

        return {
            "pe_ratio": pe_ratio,
            "pb_ratio": pb_ratio,
            "ev_ebitda": ev_ebitda,
            "fcf_yield": fcf_yield,
            "dividend_yield": dividend_yield,
        }

    # ------------------------------------------------------------------
    # Stability
    # ------------------------------------------------------------------

    def _compute_stability(
        self,
        fs: FinancialStatements,
        km: KeyMetrics,
        warnings: list[str],
    ) -> dict[str, float | None]:
        debt_to_equity = km.debt_to_equity

        current_assets = _safe_get(fs.balance_sheet, "current_assets")
        current_liabilities = _safe_get(fs.balance_sheet, "current_liabilities")
        current_ratio = _safe_div(current_assets, current_liabilities)

        operating_income = _safe_get(fs.income_statement, "operating_income")
        interest_expense = _safe_get(fs.income_statement, "interest_expense")
        interest_coverage = _safe_div(operating_income, interest_expense)

        return {
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "interest_coverage": interest_coverage,
        }

    # ------------------------------------------------------------------
    # Sector comparison
    # ------------------------------------------------------------------

    def _compare_sector(
        self,
        profitability: dict[str, float | None],
        valuation: dict[str, float | None],
        stability: dict[str, float | None],
        sector: str | None,
    ) -> dict[str, str | None]:
        if sector is None or sector not in self._sector_medians:
            return {}

        medians = self._sector_medians[sector]
        all_ratios: dict[str, float | None] = {**profitability, **valuation, **stability}
        comparison: dict[str, str | None] = {}

        for key, median in medians.items():
            value = all_ratios.get(key)
            if value is None:
                comparison[key] = None
                continue
            comparison[key] = self._classify(key, value, median)

        return comparison

    @staticmethod
    def _classify(metric: str, value: float, median: float) -> str:
        if median == 0:
            return "near_median"
        ratio = value / median
        if metric in _INVERTED_METRICS:
            if ratio > 1.2:
                return "above_median (higher risk)"
            elif ratio < 0.8:
                return "below_median"
            else:
                return "near_median"
        else:
            if ratio > 1.2:
                return "above_median"
            elif ratio < 0.8:
                return "below_median"
            else:
                return "near_median"
