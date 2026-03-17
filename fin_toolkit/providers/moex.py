"""MOEX ISS data provider via aiomoex."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import aiohttp
import aiomoex

from fin_toolkit.exceptions import ProviderUnavailableError, TickerNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint


class MOEXProvider:
    """Data provider using MOEX ISS REST API (via aiomoex)."""

    def __init__(self, board: str = "TQBR") -> None:
        self._board = board

    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        """Fetch historical OHLCV data from MOEX ISS."""
        try:
            async with aiohttp.ClientSession() as session:
                raw = await aiomoex.get_market_candles(
                    session,
                    ticker,
                    start=start,
                    end=end,
                    interval=24,  # daily candles
                )
        except Exception as exc:
            raise ProviderUnavailableError("moex", str(exc)) from exc

        if not raw:
            raise TickerNotFoundError(ticker, provider="moex")

        prices = [
            PricePoint(
                date=_parse_date(row["begin"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=int(row["volume"]),
            )
            for row in raw
            if row.get("close") is not None
        ]

        if not prices:
            raise TickerNotFoundError(ticker, provider="moex")

        return PriceData(
            ticker=ticker, period=f"{start}/{end}", prices=prices, currency="RUB",
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """MOEX ISS does not provide financial statements."""
        return FinancialStatements(
            ticker=ticker,
            income_statement=None,
            balance_sheet=None,
            cash_flow=None,
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        """Fetch basic metrics from MOEX ISS security description."""
        try:
            async with aiohttp.ClientSession() as session:
                data = await aiomoex.get_board_securities(
                    session,
                    board=self._board,
                    columns=(
                        "SECID", "PREVPRICE", "MARKETPRICEBOARD",
                        "ISSUESIZE", "LISTLEVEL",
                    ),
                )
        except Exception as exc:
            raise ProviderUnavailableError("moex", str(exc)) from exc

        # Find the ticker in the result
        sec_row: dict[str, Any] | None = None
        for row in data:
            if row.get("SECID") == ticker:
                sec_row = row
                break

        if sec_row is None:
            raise TickerNotFoundError(ticker, provider="moex")

        price = _safe_float(sec_row.get("PREVPRICE"))
        shares = _safe_float(sec_row.get("ISSUESIZE"))
        market_cap: float | None = None
        if price is not None and shares is not None:
            market_cap = price * shares

        return KeyMetrics(
            ticker=ticker,
            pe_ratio=None,
            pb_ratio=None,
            market_cap=market_cap,
            dividend_yield=None,
            roe=None,
            roa=None,
            debt_to_equity=None,
            current_price=price,
            shares_outstanding=shares,
        )

    async def list_tickers(self, board: str | None = None) -> list[str]:
        """Get all traded tickers from MOEX ISS board."""
        target_board = board or self._board
        try:
            async with aiohttp.ClientSession() as session:
                data = await aiomoex.get_board_securities(
                    session,
                    board=target_board,
                    columns=("SECID",),
                )
        except Exception as exc:
            raise ProviderUnavailableError("moex", str(exc)) from exc

        return [str(row["SECID"]) for row in data if row.get("SECID")]


def _parse_date(value: Any) -> str:
    """Parse MOEX ISS date string to YYYY-MM-DD."""
    if isinstance(value, str):
        # MOEX returns "2024-01-15 00:00:00" or "2024-01-15"
        return value[:10]
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _safe_float(val: Any) -> float | None:
    """Safely convert to float or return None."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
