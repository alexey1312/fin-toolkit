"""Tests for FinancialStatements and KeyMetrics models."""

from fin_toolkit.models.financial import FinancialStatements, KeyMetrics


class TestFinancialStatements:
    def test_create_full(self) -> None:
        fs = FinancialStatements(
            ticker="AAPL",
            income_statement={"revenue": 383_285_000_000, "net_income": 96_995_000_000},
            balance_sheet={"total_assets": 352_583_000_000},
            cash_flow={"operating_cash_flow": 110_543_000_000},
        )
        assert fs.ticker == "AAPL"
        assert fs.income_statement is not None
        assert fs.income_statement["revenue"] == 383_285_000_000

    def test_none_fields(self) -> None:
        fs = FinancialStatements(
            ticker="KCEL",
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )
        assert fs.income_statement is None
        assert fs.balance_sheet is None
        assert fs.cash_flow is None

    def test_model_dump(self) -> None:
        fs = FinancialStatements(
            ticker="AAPL",
            income_statement={"revenue": 100},
            balance_sheet=None,
            cash_flow=None,
        )
        d = fs.model_dump()
        assert d["ticker"] == "AAPL"
        assert d["balance_sheet"] is None


class TestKeyMetrics:
    def test_create_full(self) -> None:
        km = KeyMetrics(
            ticker="AAPL",
            pe_ratio=29.5,
            pb_ratio=46.7,
            market_cap=2_900_000_000_000,
            dividend_yield=0.005,
            roe=1.56,
            roa=0.275,
            debt_to_equity=4.67,
        )
        assert km.ticker == "AAPL"
        assert km.pe_ratio == 29.5

    def test_none_fields(self) -> None:
        km = KeyMetrics(
            ticker="KCEL",
            pe_ratio=None,
            pb_ratio=None,
            market_cap=None,
            dividend_yield=None,
            roe=None,
            roa=None,
            debt_to_equity=None,
        )
        assert km.pe_ratio is None
        assert km.roe is None

    def test_model_dump(self) -> None:
        km = KeyMetrics(
            ticker="AAPL",
            pe_ratio=29.5,
            pb_ratio=None,
            market_cap=2_900_000_000_000,
            dividend_yield=None,
            roe=None,
            roa=None,
            debt_to_equity=None,
        )
        d = km.model_dump()
        assert d["pe_ratio"] == 29.5
        assert d["pb_ratio"] is None
