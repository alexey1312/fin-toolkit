"""PDF financial report parser."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx
import pdfplumber

from fin_toolkit.models.financial import FinancialStatements

# ---------------------------------------------------------------------------
# Field mapping (EN + RU IFRS/МСФО)
# ---------------------------------------------------------------------------

_FIELD_MAP: dict[str, str] = {
    # EN
    "revenue": "revenue",
    "total revenue": "revenue",
    "net income": "net_income",
    "net profit": "net_income",
    "gross profit": "gross_profit",
    "operating income": "operating_income",
    "operating profit": "operating_income",
    "ebitda": "ebitda",
    "interest expense": "interest_expense",
    "total assets": "total_assets",
    "total liabilities": "total_liabilities",
    "stockholders equity": "total_equity",
    "shareholders equity": "total_equity",
    "total equity": "total_equity",
    "total debt": "total_debt",
    "long-term debt": "total_debt",
    "current assets": "current_assets",
    "current liabilities": "current_liabilities",
    "operating cash flow": "operating_cash_flow",
    "cash from operations": "operating_cash_flow",
    "capital expenditures": "capital_expenditures",
    "capex": "capital_expenditures",
    "free cash flow": "free_cash_flow",
    # RU
    "выручка": "revenue",
    "чистая прибыль": "net_income",
    "валовая прибыль": "gross_profit",
    "операционная прибыль": "operating_income",
    "прибыль от продаж": "operating_income",
    "процентные расходы": "interest_expense",
    "итого активы": "total_assets",
    "всего активы": "total_assets",
    "итого активов": "total_assets",
    "собственный капитал": "total_equity",
    "итого капитал": "total_equity",
    "общий долг": "total_debt",
    "долгосрочные обязательства": "total_debt",
    "оборотные активы": "current_assets",
    "краткосрочные обязательства": "current_liabilities",
    "операционный денежный поток": "operating_cash_flow",
    "денежные средства от операционной деятельности": "operating_cash_flow",
    "капитальные затраты": "capital_expenditures",
    "капитальные вложения": "capital_expenditures",
    "свободный денежный поток": "free_cash_flow",
}


async def parse_financial_report(
    source: str,
    ticker: str = "UNKNOWN",
) -> FinancialStatements:
    """Extract financial tables from PDF report.

    Args:
        source: File path or URL to PDF.
        ticker: Ticker to associate with the result.
    """
    pdf_bytes = await _load_pdf(source)
    tables = await asyncio.to_thread(_extract_tables, pdf_bytes)
    income, balance, cash_flow = _classify_tables(tables)

    return FinancialStatements(
        ticker=ticker,
        income_statement=income or None,
        balance_sheet=balance or None,
        cash_flow=cash_flow or None,
    )


async def _load_pdf(source: str) -> bytes:
    """Download PDF if URL, otherwise read from disk."""
    if source.startswith(("http://", "https://")):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(source, timeout=30.0)
            resp.raise_for_status()
            return resp.content
    else:
        with open(source, "rb") as f:
            return f.read()


def _extract_tables(pdf_bytes: bytes) -> list[list[list[str | None]]]:
    """Extract all tables from PDF bytes using pdfplumber."""
    import io

    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
    return tables


def _classify_tables(
    tables: list[list[list[str | None]]],
) -> tuple[dict[str, object] | None, dict[str, object] | None, dict[str, object] | None]:
    """Classify extracted tables into income/balance/cashflow."""
    income: dict[str, object] = {}
    balance: dict[str, object] = {}
    cash_flow: dict[str, object] = {}

    for table in tables:
        parsed = _parse_table(table)
        if not parsed:
            continue

        # Classify by which fields were found
        income_keys = {"revenue", "net_income", "gross_profit", "operating_income", "ebitda"}
        balance_keys = {"total_assets", "total_equity", "total_debt", "current_assets"}
        cashflow_keys = {"operating_cash_flow", "capital_expenditures", "free_cash_flow"}

        found = set(parsed.keys())
        income_overlap = len(found & income_keys)
        balance_overlap = len(found & balance_keys)
        cashflow_overlap = len(found & cashflow_keys)

        best = max(income_overlap, balance_overlap, cashflow_overlap)
        if best == 0:
            continue

        if income_overlap == best:
            income.update(parsed)
        elif balance_overlap == best:
            balance.update(parsed)
        else:
            cash_flow.update(parsed)

    return income or None, balance or None, cash_flow or None


def _parse_table(table: list[list[str | None]]) -> dict[str, object]:
    """Parse a single table, matching row labels to known fields."""
    result: dict[str, object] = {}
    for row in table:
        if not row or len(row) < 2:
            continue
        label = (row[0] or "").strip().lower()
        # Try matching against field map
        matched_key = _match_field(label)
        if matched_key is None:
            continue
        # Take the last numeric value in the row (most recent period)
        value = _extract_last_number(row[1:])
        if value is not None:
            result[matched_key] = value
    return result


def _match_field(label: str) -> str | None:
    """Match a label to a normalized field name."""
    # Direct match
    if label in _FIELD_MAP:
        return _FIELD_MAP[label]
    # Substring match
    for pattern, field in _FIELD_MAP.items():
        if pattern in label:
            return field
    return None


def _extract_last_number(cells: list[Any]) -> float | None:
    """Extract the last parseable number from a row of cells."""
    last_num: float | None = None
    for cell in reversed(cells):
        if cell is None:
            continue
        text = str(cell).strip().replace(" ", "").replace("\xa0", "")
        text = text.replace(",", ".")
        # Remove parentheses (negative numbers in accounting format)
        if text.startswith("(") and text.endswith(")"):
            text = "-" + text[1:-1]
        try:
            val = float(re.sub(r"[^\d.\-]", "", text))
            return val
        except (ValueError, TypeError):
            continue
    return last_num
