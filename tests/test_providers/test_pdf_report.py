"""Tests for PDF report parser."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fin_toolkit.providers.pdf_report import (
    _classify_tables,
    _extract_last_number,
    _match_field,
    _parse_table,
    parse_financial_report,
)


class TestMatchField:
    def test_exact_match_en(self) -> None:
        assert _match_field("revenue") == "revenue"

    def test_exact_match_ru(self) -> None:
        assert _match_field("выручка") == "revenue"

    def test_substring_match(self) -> None:
        assert _match_field("total revenue from operations") == "revenue"

    def test_no_match(self) -> None:
        assert _match_field("some random text") is None


class TestExtractLastNumber:
    def test_simple_number(self) -> None:
        assert _extract_last_number(["100.5"]) == pytest.approx(100.5)

    def test_accounting_negative(self) -> None:
        assert _extract_last_number(["(50.0)"]) == pytest.approx(-50.0)

    def test_spaces_in_number(self) -> None:
        assert _extract_last_number(["1 000 000"]) == pytest.approx(1000000.0)

    def test_last_value_taken(self) -> None:
        assert _extract_last_number(["100", "200", "300"]) == pytest.approx(300.0)

    def test_none_cells(self) -> None:
        assert _extract_last_number([None, None]) is None


class TestParseTable:
    def test_simple_table(self) -> None:
        table = [
            ["Revenue", "100000", "90000"],
            ["Net Income", "20000", "15000"],
            ["Other Item", "5000", "4000"],
        ]
        result = _parse_table(table)
        assert result["revenue"] == pytest.approx(90000.0)
        assert result["net_income"] == pytest.approx(15000.0)

    def test_russian_labels(self) -> None:
        table = [
            ["Выручка", "500000"],
            ["Чистая прибыль", "100000"],
        ]
        result = _parse_table(table)
        assert result["revenue"] == pytest.approx(500000.0)
        assert result["net_income"] == pytest.approx(100000.0)


class TestClassifyTables:
    def test_income_statement_classified(self) -> None:
        tables = [
            [
                ["Revenue", "100000"],
                ["Net Income", "20000"],
                ["Gross Profit", "60000"],
            ],
        ]
        income, balance, cash_flow = _classify_tables(tables)
        assert income is not None
        assert "revenue" in income

    def test_balance_sheet_classified(self) -> None:
        tables = [
            [
                ["Total Assets", "500000"],
                ["Total Equity", "200000"],
                ["Total Debt", "150000"],
            ],
        ]
        income, balance, cash_flow = _classify_tables(tables)
        assert balance is not None
        assert "total_assets" in balance

    def test_empty_tables(self) -> None:
        income, balance, cash_flow = _classify_tables([])
        assert income is None
        assert balance is None
        assert cash_flow is None


class TestParseFinancialReport:
    async def test_from_file(self, tmp_path: object) -> None:
        """Test parsing with mocked pdfplumber."""
        mock_table = [
            ["Revenue", "100000"],
            ["Net Income", "20000"],
        ]

        mock_page = MagicMock()
        mock_page.extract_tables.return_value = [mock_table]

        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = lambda s: s
        mock_pdf.__exit__ = lambda s, *a: None

        with patch("fin_toolkit.providers.pdf_report.pdfplumber.open", return_value=mock_pdf):
            with patch("fin_toolkit.providers.pdf_report._load_pdf", return_value=b"fake"):
                result = await parse_financial_report("/fake/path.pdf", ticker="TEST")

        assert result.ticker == "TEST"
        assert result.income_statement is not None
