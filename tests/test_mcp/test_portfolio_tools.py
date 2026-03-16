"""Tests for portfolio MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from fin_toolkit.models.price_data import PriceData, PricePoint
from fin_toolkit.portfolio_store import PortfolioStore


def _make_price_data(ticker: str = "AAPL", n: int = 30) -> PriceData:
    prices = [
        PricePoint(
            date=f"2024-01-{i + 1:02d}",
            open=150.0 + i,
            high=155.0 + i,
            low=148.0 + i,
            close=152.0 + i,
            volume=1_000_000,
        )
        for i in range(n)
    ]
    return PriceData(ticker=ticker, period="1m", prices=prices)


@pytest.fixture
def portfolio_store(tmp_path: Path) -> PortfolioStore:
    return PortfolioStore(db_path=tmp_path / "test.db")


@pytest.fixture(autouse=True)
def _patch_store(portfolio_store: PortfolioStore) -> None:  # type: ignore[misc]
    with patch(
        "fin_toolkit.mcp_server.server._portfolio_store", portfolio_store,
    ):
        yield


class TestManagePortfolioCreate:
    async def test_create(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(await manage_portfolio(action="create", portfolio="tech", format="json"))
        assert result["status"] == "ok"
        assert result["portfolio"] == "tech"
        assert "id" in result

    async def test_create_with_currency(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(
            await manage_portfolio(
                action="create", portfolio="ru", currency="RUB", format="json",
            ),
        )
        assert result["status"] == "ok"

    async def test_create_no_name(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(await manage_portfolio(action="create", format="json"))
        assert result["is_error"] is True

    async def test_create_duplicate(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="tech", format="json")
        result = json.loads(
            await manage_portfolio(action="create", portfolio="tech", format="json"),
        )
        assert result["is_error"] is True
        assert "already exists" in result["error"]


class TestManagePortfolioList:
    async def test_list_empty(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(await manage_portfolio(action="list", format="json"))
        assert result["portfolios"] == []

    async def test_list_after_create(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="a", format="json")
        await manage_portfolio(action="create", portfolio="b", format="json")
        result = json.loads(await manage_portfolio(action="list", format="json"))
        names = [p["name"] for p in result["portfolios"]]
        assert "a" in names
        assert "b" in names


class TestManagePortfolioDelete:
    async def test_delete(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="temp", format="json")
        result = json.loads(
            await manage_portfolio(action="delete", portfolio="temp", format="json"),
        )
        assert result["status"] == "ok"

    async def test_delete_nonexistent(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(
            await manage_portfolio(action="delete", portfolio="ghost", format="json"),
        )
        assert result["is_error"] is True


class TestManagePortfolioBuySell:
    async def test_buy(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        result = json.loads(
            await manage_portfolio(
                action="buy", portfolio="p1", ticker="AAPL",
                shares=10, price=150.0, format="json",
            ),
        )
        assert result["status"] == "ok"
        assert result["action"] == "buy"
        assert result["transaction_id"] > 0

    async def test_sell(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="AAPL",
            shares=10, price=150.0, format="json",
        )
        result = json.loads(
            await manage_portfolio(
                action="sell", portfolio="p1", ticker="AAPL",
                shares=3, price=170.0, format="json",
            ),
        )
        assert result["status"] == "ok"
        assert result["action"] == "sell"

    async def test_buy_no_ticker(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        result = json.loads(
            await manage_portfolio(
                action="buy", portfolio="p1", shares=10, price=150.0, format="json",
            ),
        )
        assert result["is_error"] is True

    async def test_buy_no_shares(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        result = json.loads(
            await manage_portfolio(
                action="buy", portfolio="p1", ticker="AAPL", price=150.0, format="json",
            ),
        )
        assert result["is_error"] is True


class TestManagePortfolioShow:
    async def test_show_with_prices(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="AAPL",
            shares=10, price=150.0, format="json",
        )

        mock_router = AsyncMock()
        mock_router.get_prices = AsyncMock(return_value=_make_price_data("AAPL"))

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = json.loads(
                await manage_portfolio(action="show", portfolio="p1", format="json"),
            )

        assert len(result["positions"]) == 1
        pos = result["positions"][0]
        assert pos["ticker"] == "AAPL"
        assert pos["shares"] == 10.0
        assert pos["current_price"] is not None
        assert pos["market_value"] is not None
        assert pos["pnl"] is not None
        assert pos["weight"] is not None
        assert result["total_value"] is not None

    async def test_show_empty(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        mock_router = AsyncMock()
        await manage_portfolio(action="create", portfolio="p1", format="json")
        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = json.loads(
                await manage_portfolio(action="show", portfolio="p1", format="json"),
            )
        assert result["positions"] == []


class TestManagePortfolioHistory:
    async def test_history(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="AAPL",
            shares=10, price=150.0, format="json",
        )
        await manage_portfolio(
            action="sell", portfolio="p1", ticker="AAPL",
            shares=3, price=170.0, format="json",
        )
        result = json.loads(
            await manage_portfolio(
                action="history", portfolio="p1", ticker="AAPL", format="json",
            ),
        )
        assert len(result["transactions"]) == 2

    async def test_history_all_tickers(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        await manage_portfolio(action="create", portfolio="p1", format="json")
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="AAPL",
            shares=10, price=150.0, format="json",
        )
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="MSFT",
            shares=5, price=400.0, format="json",
        )
        result = json.loads(
            await manage_portfolio(action="history", portfolio="p1", format="json"),
        )
        assert len(result["transactions"]) == 2


class TestPortfolioPerformance:
    async def test_performance(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio, portfolio_performance

        await manage_portfolio(action="create", portfolio="p1", format="json")
        await manage_portfolio(
            action="buy", portfolio="p1", ticker="AAPL",
            shares=10, price=150.0,
            date="2024-01-01T00:00:00Z", format="json",
        )

        mock_router = AsyncMock()
        mock_router.get_prices = AsyncMock(return_value=_make_price_data("AAPL"))

        with patch("fin_toolkit.mcp_server.server._provider_router", mock_router):
            result = json.loads(
                await portfolio_performance(portfolio="p1", period="1y", format="json"),
            )

        assert result["name"] == "p1"
        assert result["period"] == "1y"
        assert "pnl" in result
        assert "pnl_pct" in result
        assert "ticker_returns" in result
        assert result["transactions_count"] >= 0

    async def test_performance_store_not_initialized(self) -> None:
        from fin_toolkit.mcp_server.server import portfolio_performance

        with patch("fin_toolkit.mcp_server.server._portfolio_store", None):
            result = json.loads(
                await portfolio_performance(portfolio="p1", format="json"),
            )
        assert result["is_error"] is True

    async def test_manage_unknown_action(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        result = json.loads(
            await manage_portfolio(action="unknown", format="json"),
        )
        assert result["is_error"] is True
        assert "Unknown action" in result["error"]


class TestStoreNotInitialized:
    async def test_manage_no_store(self) -> None:
        from fin_toolkit.mcp_server.server import manage_portfolio

        with patch("fin_toolkit.mcp_server.server._portfolio_store", None):
            result = json.loads(
                await manage_portfolio(action="list", format="json"),
            )
        assert result["is_error"] is True
