"""SmartLab (smart-lab.ru) data provider — fundamental metrics and IFRS financials."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup, Tag

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData

_BASE_URL = "https://smart-lab.ru"
_HEADERS = {"User-Agent": "Mozilla/5.0 (fin-toolkit)"}

# Column indices in the fundamental table (0-based, after skipping №, name, ticker, 2 chart cols)
_FUND_COLUMNS = [
    "market_cap", "ev", "revenue", "net_income",
    "dividend_yield", "dividend_yield_pref", "div_payout_ratio",
    "pe_ratio", "ps_ratio", "pb_ratio", "ev_ebitda",
    "ebitda_margin", "debt_ebitda", "report_type",
]

# SmartLab field → our normalized field name mapping (for financials page)
_INCOME_FIELDS = {
    "revenue": "revenue",
    "operating_income": "operating_income",
    "ebitda": "ebitda",
    "net_income": "net_income",
    "net_operating_income": "revenue",  # banks
    "interest_expenses": "interest_expense",
    "amortization": "amortization",
    "cost_of_production": "cost_of_goods_sold",
}

_BALANCE_FIELDS = {
    "assets": "total_assets",
    "bank_assets": "total_assets",  # banks
    "net_assets": "total_equity",
    "capital": "total_equity",  # banks
    "debt": "total_debt",
    "cash": "cash_and_equivalents",
    "net_debt": "net_debt",
}

_CASHFLOW_FIELDS = {
    "ocf": "operating_cash_flow",
    "capex": "capital_expenditures",
    "fcf": "free_cash_flow",
}

_META_FIELDS = {
    "number_of_shares": "shares_outstanding",
    "common_share": "current_price",
}

# Billion rubles multiplier (SmartLab shows values in млрд руб)
_BLN = 1_000_000_000


def _parse_number(text: str) -> float | None:
    """Parse a SmartLab number: '5 311' → 5311.0, '18.2%' → 18.2, '' → None."""
    text = text.strip().replace("\xa0", " ").replace(" ", "").replace(",", ".")
    if text.endswith("%"):
        text = text[:-1]
    if not text or text in ("—", "-", "н/д"):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_fundamental_table(html: str) -> dict[str, dict[str, float | None]]:
    """Parse the /q/shares_fundamental/ table into {ticker: {metric: value}}."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="simple-little-table")
    if not table:
        return {}

    result: dict[str, dict[str, float | None]] = {}
    rows = table.find_all("tr")  # type: ignore[union-attr]

    for row in rows[1:]:  # skip header
        cells = row.find_all("td")
        if len(cells) < 10:
            continue

        # Extract ticker (3rd cell)
        ticker_text = cells[2].get_text(strip=True)
        if not ticker_text or not ticker_text.isalpha():
            continue

        # Data cells start at index 5 (after №, name, ticker, 2 chart icons)
        data_cells = cells[5:]
        metrics: dict[str, float | None] = {}
        for i, col_name in enumerate(_FUND_COLUMNS):
            if i < len(data_cells):
                val = _parse_number(data_cells[i].get_text(strip=True))
                metrics[col_name] = val
            else:
                metrics[col_name] = None

        result[ticker_text] = metrics

    return result


_FinancialsResult = tuple[
    dict[str, object], dict[str, object], dict[str, object],
    list[dict[str, object]], dict[str, float | None],
]


def _parse_financials_page(html: str) -> _FinancialsResult:
    """Parse per-ticker financials page (/q/TICKER/f/y/MSFO/).

    Returns (income, balance, cashflow, income_history, meta).
    Values in the table are in млрд руб — multiply by 1e9.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="simple-little-table")
    if not table:
        return {}, {}, {}, [], {}

    # Extract years from header row
    assert isinstance(table, Tag)
    header_row = table.find("tr", class_="header_row")
    years: list[str] = []
    if header_row:
        for td in header_row.find_all("td"):  # type: ignore[union-attr]
            cls = td.get("class", [])
            if "chartrow" in cls or "ltm_spc" in cls:
                continue
            strong = td.find("strong")
            if strong:
                text = strong.get_text(strip=True)
                if text != "LTM":
                    years.append(text)

    income: dict[str, object] = {}
    balance: dict[str, object] = {}
    cashflow: dict[str, object] = {}
    meta: dict[str, float | None] = {}

    # History: {year: {field: value}}
    history_by_year: dict[str, dict[str, float]] = {y: {} for y in years}

    for tr in table.find_all("tr", attrs={"field": True}):
        field = tr.get("field", "")
        values = _extract_row_values(tr)

        if not values:
            continue

        # Most recent value (last non-LTM)
        latest = values[-1] if values else None

        # Map to our fields
        if field in _INCOME_FIELDS:
            key = _INCOME_FIELDS[field]
            if key not in income and latest is not None:
                income[key] = latest * _BLN
            # Fill history
            for i, year in enumerate(years):
                val = values[i] if i < len(values) else None
                if val is not None:
                    history_by_year[year][key] = val * _BLN
        elif field in _BALANCE_FIELDS:
            key = _BALANCE_FIELDS[field]
            if key not in balance and latest is not None:
                balance[key] = latest * _BLN
        elif field in _CASHFLOW_FIELDS:
            key = _CASHFLOW_FIELDS[field]
            if key not in cashflow and latest is not None:
                cashflow[key] = latest * _BLN
        elif field in _META_FIELDS:
            key = _META_FIELDS[field]
            if field == "number_of_shares" and latest is not None:
                meta[key] = latest * 1_000_000  # млн → шт
            elif field == "common_share" and latest is not None:
                meta[key] = latest  # руб, без множителя

    # Build income_history list (ordered oldest → newest)
    income_history: list[dict[str, object]] = []
    for year in years:
        period_data = history_by_year.get(year, {})
        if period_data:
            entry: dict[str, object] = {"period": year}
            entry.update(period_data)
            income_history.append(entry)

    return income, balance, cashflow, income_history, meta


def _extract_row_values(tr: Tag) -> list[float | None]:
    """Extract numeric values from a financials table row, skipping chart/LTM cells."""
    values: list[float | None] = []
    seen_ltm = False
    for td in tr.find_all("td"):
        cls = td.get("class", [])
        if "chartrow" in cls:
            continue
        if "ltm_spc" in cls:
            seen_ltm = True
            continue
        if seen_ltm:
            break  # skip LTM column
        text = td.get_text(strip=True)
        # Skip empty editrow cells and non-data cells
        if not text:
            continue
        val = _parse_number(text)
        values.append(val)
    return values


class SmartLabProvider:
    """Data provider using SmartLab (smart-lab.ru) for Russian market fundamentals.

    Provides:
    - get_metrics: P/E, P/B, EV/EBITDA, ROE, market cap from fundamental table
    - get_financials: income/balance/cashflow from per-ticker IFRS pages
    - get_prices: not supported (use MOEXProvider for prices)
    """

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """SmartLab doesn't provide historical prices — use MOEX provider."""
        raise ProviderUnavailableError("smartlab", "No price data; use moex provider")

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch key metrics from SmartLab fundamental table."""
        html = await self._fetch("/q/shares_fundamental/")
        all_data = _parse_fundamental_table(html)

        if ticker not in all_data:
            raise TickerNotFoundError(ticker, provider="smartlab")

        m = all_data[ticker]
        mcap = m.get("market_cap")
        div_yield = m.get("dividend_yield")

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=m.get("pe_ratio"),
            pb_ratio=m.get("pb_ratio"),
            market_cap=mcap * _BLN if mcap is not None else None,
            dividend_yield=div_yield / 100 if div_yield is not None else None,
            roe=None,  # not in fundamental table; available on financials page
            roa=None,
            debt_to_equity=None,
            enterprise_value=ev * _BLN if (ev := m.get("ev")) is not None else None,
            ev_ebitda=m.get("ev_ebitda"),
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch IFRS financial statements from per-ticker SmartLab page."""
        html = await self._fetch(f"/q/{ticker}/f/y/MSFO/")
        income, balance, cashflow, income_history, meta = _parse_financials_page(html)

        if not income and not balance and not cashflow:
            raise TickerNotFoundError(ticker, provider="smartlab")

        return FinancialStatements(
            ticker=ticker,
            income_statement=income or None,
            balance_sheet=balance or None,
            cash_flow=cashflow or None,
            income_history=income_history or None,
        )

    async def _fetch(self, path: str) -> str:
        """Fetch a SmartLab page."""
        try:
            async with httpx.AsyncClient(
                follow_redirects=True, timeout=15.0,
            ) as client:
                resp = await client.get(f"{_BASE_URL}{path}", headers=_HEADERS)
                resp.raise_for_status()
                return resp.text
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise TickerNotFoundError(path, provider="smartlab") from exc
            raise ProviderUnavailableError("smartlab", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("smartlab", str(exc)) from exc
