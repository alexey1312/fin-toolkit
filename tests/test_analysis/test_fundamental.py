"""Tests for FundamentalAnalyzer."""

from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics


def _make_financials(
    ticker: str = "AAPL",
    revenue: float = 383_285_000_000,
    net_income: float = 96_995_000_000,
    gross_profit: float = 169_148_000_000,
    operating_income: float = 114_301_000_000,
    interest_expense: float = 3_933_000_000,
    total_assets: float = 352_583_000_000,
    total_equity: float = 62_146_000_000,
    total_debt: float = 111_088_000_000,
    current_assets: float = 143_566_000_000,
    current_liabilities: float = 145_308_000_000,
    operating_cash_flow: float = 110_543_000_000,
    capital_expenditures: float = 10_959_000_000,
    invested_capital: float = 173_234_000_000,
    ebitda: float = 130_541_000_000,
) -> FinancialStatements:
    return FinancialStatements(
        ticker=ticker,
        income_statement={
            "revenue": revenue,
            "net_income": net_income,
            "gross_profit": gross_profit,
            "operating_income": operating_income,
            "interest_expense": interest_expense,
            "ebitda": ebitda,
        },
        balance_sheet={
            "total_assets": total_assets,
            "total_equity": total_equity,
            "total_debt": total_debt,
            "current_assets": current_assets,
            "current_liabilities": current_liabilities,
            "invested_capital": invested_capital,
        },
        cash_flow={
            "operating_cash_flow": operating_cash_flow,
            "capital_expenditures": capital_expenditures,
        },
    )


def _make_metrics(
    ticker: str = "AAPL",
    pe_ratio: float | None = 29.5,
    pb_ratio: float | None = 46.7,
    market_cap: float | None = 2_900_000_000_000,
    dividend_yield: float | None = 0.005,
    roe: float | None = 1.56,
    roa: float | None = 0.275,
    debt_to_equity: float | None = 1.787,
    enterprise_value: float | None = 3_100_000_000_000,
) -> KeyMetrics:
    return KeyMetrics(
        ticker=ticker,
        pe_ratio=pe_ratio,
        pb_ratio=pb_ratio,
        market_cap=market_cap,
        dividend_yield=dividend_yield,
        roe=roe,
        roa=roa,
        debt_to_equity=debt_to_equity,
        enterprise_value=enterprise_value,
    )


class TestProfitabilityRatios:
    def test_roe_from_metrics(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.profitability["roe"] == 1.56

    def test_roa_from_metrics(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.profitability["roa"] == 0.275

    def test_roic_computed(self) -> None:
        """ROIC = NOPAT / invested_capital. NOPAT ~ operating_income * (1 - tax_rate)."""
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        # operating_income=114_301_000_000, net_income=96_995_000_000, revenue=383_285_000_000
        # tax_rate ~ 1 - (net_income / (operating_income - interest_expense))
        # nopat = operating_income * (1 - tax_rate)
        # roic = nopat / invested_capital
        roic = result.profitability["roic"]
        assert roic is not None
        assert 0.3 < roic < 1.0  # rough sanity check for AAPL

    def test_net_margin(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        expected = 96_995_000_000 / 383_285_000_000
        assert result.profitability["net_margin"] is not None
        assert abs(result.profitability["net_margin"] - expected) < 0.001  # type: ignore[operator]

    def test_gross_margin(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        expected = 169_148_000_000 / 383_285_000_000
        assert result.profitability["gross_margin"] is not None
        assert abs(result.profitability["gross_margin"] - expected) < 0.001  # type: ignore[operator]


class TestValuationRatios:
    def test_pe_ratio(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.valuation["pe_ratio"] == 29.5

    def test_pb_ratio(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.valuation["pb_ratio"] == 46.7

    def test_ev_ebitda(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        expected = 3_100_000_000_000 / 130_541_000_000
        assert result.valuation["ev_ebitda"] is not None
        assert abs(result.valuation["ev_ebitda"] - expected) < 0.01  # type: ignore[operator]

    def test_fcf_yield(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        fcf = 110_543_000_000 - 10_959_000_000
        expected = fcf / 2_900_000_000_000
        assert result.valuation["fcf_yield"] is not None
        assert abs(result.valuation["fcf_yield"] - expected) < 0.001  # type: ignore[operator]

    def test_dividend_yield(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.valuation["dividend_yield"] == 0.005


class TestStabilityRatios:
    def test_debt_to_equity(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.stability["debt_to_equity"] == 1.787

    def test_current_ratio(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        expected = 143_566_000_000 / 145_308_000_000
        assert result.stability["current_ratio"] is not None
        assert abs(result.stability["current_ratio"] - expected) < 0.001  # type: ignore[operator]

    def test_interest_coverage(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        expected = 114_301_000_000 / 3_933_000_000
        assert result.stability["interest_coverage"] is not None
        assert abs(result.stability["interest_coverage"] - expected) < 0.01  # type: ignore[operator]


class TestMissingData:
    def test_missing_income_statement(self) -> None:
        fs = FinancialStatements(
            ticker="KCEL",
            income_statement=None,
            balance_sheet={"total_assets": 100, "total_equity": 50, "total_debt": 30,
                           "current_assets": 40, "current_liabilities": 20},
            cash_flow=None,
        )
        km = KeyMetrics(
            ticker="KCEL", pe_ratio=None, pb_ratio=None, market_cap=None,
            dividend_yield=None, roe=None, roa=None, debt_to_equity=0.6,
        )
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(fs, km)
        assert result.profitability["net_margin"] is None
        assert result.profitability["gross_margin"] is None
        assert result.profitability["roic"] is None
        assert result.stability["interest_coverage"] is None

    def test_missing_all_metrics(self) -> None:
        fs = FinancialStatements(
            ticker="KCEL",
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )
        km = KeyMetrics(
            ticker="KCEL", pe_ratio=None, pb_ratio=None, market_cap=None,
            dividend_yield=None, roe=None, roa=None, debt_to_equity=None,
        )
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(fs, km)
        assert result.profitability["roe"] is None
        assert result.profitability["roa"] is None
        assert result.valuation["pe_ratio"] is None
        assert result.stability["debt_to_equity"] is None
        assert result.stability["current_ratio"] is None

    def test_missing_cash_flow_yields_none_fcf(self) -> None:
        fs = _make_financials()
        fs = FinancialStatements(
            ticker="TEST",
            income_statement=fs.income_statement,
            balance_sheet=fs.balance_sheet,
            cash_flow=None,
        )
        km = _make_metrics(ticker="TEST")
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(fs, km)
        assert result.valuation["fcf_yield"] is None


class TestFallbackFromFinancials:
    """ROE/ROA/D/E fallback: computed from financial statements when KeyMetrics values are None."""

    def test_roe_fallback_from_financials(self) -> None:
        fs = _make_financials(net_income=100, total_equity=500)
        km = _make_metrics(roe=None)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.profitability["roe"] is not None
        assert abs(result.profitability["roe"] - 0.2) < 0.001  # type: ignore[operator]

    def test_roa_fallback_from_financials(self) -> None:
        fs = _make_financials(net_income=100, total_assets=1000)
        km = _make_metrics(roa=None)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.profitability["roa"] is not None
        assert abs(result.profitability["roa"] - 0.1) < 0.001  # type: ignore[operator]

    def test_debt_to_equity_fallback_from_financials(self) -> None:
        fs = _make_financials(total_debt=300, total_equity=200)
        km = _make_metrics(debt_to_equity=None)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.stability["debt_to_equity"] is not None
        assert abs(result.stability["debt_to_equity"] - 1.5) < 0.001  # type: ignore[operator]

    def test_metrics_preferred_over_fallback(self) -> None:
        fs = _make_financials(net_income=100, total_equity=500)  # would give 0.2
        km = _make_metrics(roe=0.25)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.profitability["roe"] == 0.25

    def test_fallback_with_missing_financials(self) -> None:
        fs = FinancialStatements(
            ticker="TEST",
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )
        km = _make_metrics(roe=None, roa=None, debt_to_equity=None)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.profitability["roe"] is None
        assert result.profitability["roa"] is None
        assert result.stability["debt_to_equity"] is None

    def test_kase_ticker_realistic(self) -> None:
        """AIRA-like data: all km metrics None except market_cap/price, financials present."""
        fs = FinancialStatements(
            ticker="AIRA",
            income_statement={
                "revenue": 350_000_000,
                "net_income": 52_700_000,
                "gross_profit": 150_000_000,
                "operating_income": 70_000_000,
                "interest_expense": 10_000_000,
            },
            balance_sheet={
                "total_assets": 1_800_000_000,
                "total_equity": 394_500_000,
                "total_debt": 889_000_000,
                "current_assets": 500_000_000,
                "current_liabilities": 300_000_000,
                "invested_capital": 1_283_500_000,
            },
            cash_flow={
                "operating_cash_flow": 80_000_000,
                "capital_expenditures": 20_000_000,
            },
        )
        km = KeyMetrics(
            ticker="AIRA",
            pe_ratio=None, pb_ratio=None,
            market_cap=1_000_000_000, dividend_yield=None,
            roe=None, roa=None, debt_to_equity=None,
            enterprise_value=None,
        )
        result = FundamentalAnalyzer().analyze(fs, km)
        # ROE = 52.7M / 394.5M ≈ 0.1335
        assert result.profitability["roe"] is not None
        assert abs(result.profitability["roe"] - 0.1335) < 0.01  # type: ignore[operator]
        # ROA = 52.7M / 1.8B ≈ 0.0293
        assert result.profitability["roa"] is not None
        assert abs(result.profitability["roa"] - 0.0293) < 0.01  # type: ignore[operator]
        # D/E = 889M / 394.5M ≈ 2.253
        assert result.stability["debt_to_equity"] is not None
        assert abs(result.stability["debt_to_equity"] - 2.253) < 0.01  # type: ignore[operator]

    def test_pe_fallback_from_financials(self) -> None:
        """P/E computed from market_cap / net_income when pe_ratio is None."""
        fs = _make_financials(net_income=100)
        km = _make_metrics(pe_ratio=None, market_cap=1000)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.valuation["pe_ratio"] is not None
        assert abs(result.valuation["pe_ratio"] - 10.0) < 0.001  # type: ignore[operator]

    def test_pb_fallback_from_financials(self) -> None:
        """P/B computed from market_cap / total_equity when pb_ratio is None."""
        fs = _make_financials(total_equity=500)
        km = _make_metrics(pb_ratio=None, market_cap=1000)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.valuation["pb_ratio"] is not None
        assert abs(result.valuation["pb_ratio"] - 2.0) < 0.001  # type: ignore[operator]

    def test_ev_ebitda_fallback(self) -> None:
        """EV/EBITDA computed when enterprise_value is None but market_cap exists."""
        fs = _make_financials(total_debt=300, ebitda=200)
        # Add cash_and_equivalents to balance_sheet
        fs.balance_sheet["cash_and_equivalents"] = 100  # type: ignore[index]
        km = _make_metrics(enterprise_value=None, market_cap=1000)
        result = FundamentalAnalyzer().analyze(fs, km)
        # EV = 1000 + 300 - 100 = 1200; EV/EBITDA = 1200 / 200 = 6.0
        assert result.valuation["ev_ebitda"] is not None
        assert abs(result.valuation["ev_ebitda"] - 6.0) < 0.001  # type: ignore[operator]

    def test_pe_preferred_over_fallback(self) -> None:
        """KeyMetrics pe_ratio takes priority over computed fallback."""
        fs = _make_financials(net_income=100)
        km = _make_metrics(pe_ratio=15.0, market_cap=1000)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.valuation["pe_ratio"] == 15.0

    def test_valuation_fallback_no_market_cap(self) -> None:
        """When market_cap is None, valuation fallbacks all return None."""
        fs = _make_financials(net_income=100, total_equity=500)
        km = _make_metrics(pe_ratio=None, pb_ratio=None, enterprise_value=None, market_cap=None)
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.valuation["pe_ratio"] is None
        assert result.valuation["pb_ratio"] is None
        assert result.valuation["ev_ebitda"] is None

    def test_ev_ebitda_from_key_metrics_preferred(self) -> None:
        """km.ev_ebitda takes priority over computed EV/EBITDA."""
        fs = _make_financials(ebitda=200)
        km = _make_metrics(enterprise_value=3000)
        # Computed would be 3000/200=15.0, but km.ev_ebitda=8.5 wins
        km_with_ev_ebitda = KeyMetrics(
            ticker="TEST", pe_ratio=29.5, pb_ratio=46.7,
            market_cap=2_900_000_000_000, dividend_yield=0.005,
            roe=1.56, roa=0.275, debt_to_equity=1.787,
            enterprise_value=3000, ev_ebitda=8.5,
        )
        result = FundamentalAnalyzer().analyze(fs, km_with_ev_ebitda)
        assert result.valuation["ev_ebitda"] == 8.5

    def test_fcf_yield_from_key_metrics_preferred(self) -> None:
        """km.fcf_yield takes priority over computed FCF yield."""
        fs = _make_financials()
        km_with_fcf = KeyMetrics(
            ticker="TEST", pe_ratio=29.5, pb_ratio=46.7,
            market_cap=2_900_000_000_000, dividend_yield=0.005,
            roe=1.56, roa=0.275, debt_to_equity=1.787,
            enterprise_value=3_100_000_000_000, fcf_yield=0.123,
        )
        result = FundamentalAnalyzer().analyze(fs, km_with_fcf)
        assert result.valuation["fcf_yield"] == 0.123

    def test_dividend_yield_sanity_capped(self) -> None:
        """dividend_yield > 1.0 is garbage data — should be None."""
        fs = _make_financials()
        km = _make_metrics(dividend_yield=17.72)  # Yahoo garbage
        result = FundamentalAnalyzer().analyze(fs, km)
        assert result.valuation["dividend_yield"] is None


class TestSectorComparison:
    def test_technology_above_median(self) -> None:
        """High ROE should be above_median for Technology."""
        analyzer = FundamentalAnalyzer()
        km = _make_metrics(roe=0.50)  # Tech median ROE ~0.20
        result = analyzer.analyze(_make_financials(), km, sector="Technology")
        assert result.sector_comparison["roe"] == "above_median"

    def test_technology_below_median(self) -> None:
        analyzer = FundamentalAnalyzer()
        km = _make_metrics(roe=0.05)  # Well below tech median
        result = analyzer.analyze(_make_financials(), km, sector="Technology")
        assert result.sector_comparison["roe"] == "below_median"

    def test_technology_near_median(self) -> None:
        analyzer = FundamentalAnalyzer()
        km = _make_metrics(pe_ratio=28.0)  # Tech median PE ~30
        result = analyzer.analyze(_make_financials(), km, sector="Technology")
        assert result.sector_comparison["pe_ratio"] == "near_median"

    def test_debt_to_equity_inverted(self) -> None:
        """Higher debt_to_equity than median should be 'above_median (higher risk)'."""
        analyzer = FundamentalAnalyzer()
        km = _make_metrics(debt_to_equity=3.0)  # Way above tech median
        result = analyzer.analyze(_make_financials(), km, sector="Technology")
        assert result.sector_comparison["debt_to_equity"] == "above_median (higher risk)"

    def test_unknown_sector(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics(), sector="Martian Mining")
        assert result.sector_comparison == {}

    def test_no_sector(self) -> None:
        analyzer = FundamentalAnalyzer()
        result = analyzer.analyze(_make_financials(), _make_metrics())
        assert result.sector_comparison == {}

    def test_all_nine_sectors_loadable(self) -> None:
        """All 9 sectors should have medians and not crash."""
        analyzer = FundamentalAnalyzer()
        sectors = [
            "Technology", "Finance", "Healthcare", "Energy",
            "Consumer", "Telecom", "Materials", "Industrials", "Utilities",
        ]
        for sector in sectors:
            result = analyzer.analyze(_make_financials(), _make_metrics(), sector=sector)
            assert len(result.sector_comparison) > 0, f"No comparison for {sector}"
