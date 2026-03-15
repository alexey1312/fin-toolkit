"""KASE (Kazakhstan Stock Exchange) data provider via web scraping."""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint

BASE_URL = "https://kase.kz/en/shares"


class KASEProvider:
    """Data provider scraping kase.kz for Kazakh market data."""

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical prices by scraping KASE trading results page."""
        url = f"{BASE_URL}/{ticker}/"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"start": start, "end": end})
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ProviderUnavailableError("kase", str(exc)) from exc

        prices = self._parse_prices_html(response.text)
        if not prices:
            raise TickerNotFoundError(ticker, provider="kase")

        return PriceData(ticker=ticker, period=f"{start}/{end}", prices=prices)

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """KASE does not provide financial statements — returns None fields."""
        return FinancialStatements(
            ticker=ticker,
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """KASE does not provide key metrics — returns None fields."""
        return KeyMetrics(
            ticker=ticker,
            pe_ratio=None,
            pb_ratio=None,
            market_cap=None,
            dividend_yield=None,
            roe=None,
            roa=None,
            debt_to_equity=None,
        )

    @staticmethod
    def _parse_kase_number(text: str) -> float:
        """Parse KASE-formatted number: '4 500,00' -> 4500.0."""
        cleaned = re.sub(r"\s", "", text.strip())
        cleaned = cleaned.replace(",", ".")
        return float(cleaned)

    @staticmethod
    def _parse_kase_int(text: str) -> int:
        """Parse KASE-formatted integer: '125 000' -> 125000."""
        cleaned = re.sub(r"\s", "", text.strip())
        return int(cleaned)

    @staticmethod
    def _parse_kase_date(text: str) -> str:
        """Parse KASE date format: '02.01.2024' -> '2024-01-02'."""
        parts = text.strip().split(".")
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return text.strip()

    def _parse_prices_html(self, html: str) -> list[PricePoint]:
        """Parse price table from KASE HTML."""
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", {"id": "trading-results-table"})
        if not table:
            return []

        rows = table.find("tbody").find_all("tr")  # type: ignore[union-attr]
        prices: list[PricePoint] = []
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 6:
                continue
            prices.append(
                PricePoint(
                    date=self._parse_kase_date(cells[0].get_text()),
                    open=self._parse_kase_number(cells[1].get_text()),
                    high=self._parse_kase_number(cells[2].get_text()),
                    low=self._parse_kase_number(cells[3].get_text()),
                    close=self._parse_kase_number(cells[4].get_text()),
                    volume=self._parse_kase_int(cells[5].get_text()),
                )
            )
        return prices
