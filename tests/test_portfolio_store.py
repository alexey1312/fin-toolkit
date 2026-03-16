"""Tests for SQLite portfolio store."""

from __future__ import annotations

from pathlib import Path

import pytest

from fin_toolkit.exceptions import PortfolioError
from fin_toolkit.portfolio_store import PortfolioStore


@pytest.fixture
def store(tmp_path: Path) -> PortfolioStore:
    """Create a PortfolioStore with a temp database."""
    return PortfolioStore(db_path=tmp_path / "test.db")


class TestCreatePortfolio:
    def test_create_returns_id(self, store: PortfolioStore) -> None:
        pid = store.create_portfolio("tech", currency="USD", notes="US tech")
        assert isinstance(pid, int)
        assert pid > 0

    def test_duplicate_name_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("tech")
        with pytest.raises(PortfolioError, match="already exists"):
            store.create_portfolio("tech")

    def test_list_portfolios(self, store: PortfolioStore) -> None:
        store.create_portfolio("us_tech", currency="USD")
        store.create_portfolio("ru_divs", currency="RUB")
        portfolios = store.list_portfolios()
        names = [p["name"] for p in portfolios]
        assert "us_tech" in names
        assert "ru_divs" in names
        assert portfolios[1]["currency"] == "USD"  # sorted: ru_divs, us_tech

    def test_delete_portfolio(self, store: PortfolioStore) -> None:
        store.create_portfolio("temp")
        store.delete_portfolio("temp")
        assert store.list_portfolios() == []

    def test_delete_nonexistent_raises(self, store: PortfolioStore) -> None:
        with pytest.raises(PortfolioError, match="not found"):
            store.delete_portfolio("ghost")


class TestTransactions:
    def test_buy(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        tid = store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        assert isinstance(tid, int)

    def test_sell_within_position(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        tid = store.add_transaction("p1", "AAPL", "sell", 3, 170.0)
        assert isinstance(tid, int)

    def test_sell_exceeds_position_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        with pytest.raises(PortfolioError, match="Cannot sell"):
            store.add_transaction("p1", "AAPL", "sell", 15, 170.0)

    def test_sell_without_position_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        with pytest.raises(PortfolioError, match="Cannot sell"):
            store.add_transaction("p1", "AAPL", "sell", 1, 100.0)

    def test_invalid_action_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        with pytest.raises(PortfolioError, match="Invalid action"):
            store.add_transaction("p1", "AAPL", "short", 10, 100.0)

    def test_negative_shares_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        with pytest.raises(PortfolioError, match="Shares must be positive"):
            store.add_transaction("p1", "AAPL", "buy", -5, 100.0)

    def test_zero_price_raises(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        with pytest.raises(PortfolioError, match="Price must be positive"):
            store.add_transaction("p1", "AAPL", "buy", 10, 0)

    def test_nonexistent_portfolio_raises(self, store: PortfolioStore) -> None:
        with pytest.raises(PortfolioError, match="not found"):
            store.add_transaction("ghost", "AAPL", "buy", 10, 100.0)

    def test_get_transactions(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0, notes="first buy")
        store.add_transaction("p1", "MSFT", "buy", 5, 400.0)
        store.add_transaction("p1", "AAPL", "sell", 3, 170.0)

        all_txns = store.get_transactions("p1")
        assert len(all_txns) == 3

        aapl_txns = store.get_transactions("p1", ticker="AAPL")
        assert len(aapl_txns) == 2
        assert aapl_txns[0].action == "buy"
        assert aapl_txns[1].action == "sell"
        assert aapl_txns[0].notes == "first buy"

    def test_fee_recorded(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0, fee=9.99)
        txns = store.get_transactions("p1")
        assert txns[0].fee == 9.99

    def test_custom_date(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction(
            "p1", "AAPL", "buy", 10, 150.0,
            executed_at="2024-06-15T10:00:00Z",
        )
        txns = store.get_transactions("p1")
        assert txns[0].executed_at == "2024-06-15T10:00:00Z"


class TestPositions:
    def test_single_buy(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        positions = store.get_positions("p1")
        assert len(positions) == 1
        pos = positions[0]
        assert pos.ticker == "AAPL"
        assert pos.shares == 10.0
        assert pos.avg_cost == 150.0
        assert pos.total_invested == 1500.0
        assert pos.current_price is None  # no live prices in store

    def test_multiple_buys_avg_cost(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 100.0)
        store.add_transaction("p1", "AAPL", "buy", 10, 200.0)
        positions = store.get_positions("p1")
        pos = positions[0]
        assert pos.shares == 20.0
        assert pos.avg_cost == 150.0  # (10*100 + 10*200) / 20

    def test_buy_and_sell(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        store.add_transaction("p1", "AAPL", "sell", 3, 170.0)
        positions = store.get_positions("p1")
        pos = positions[0]
        assert pos.shares == 7.0
        assert pos.avg_cost == 150.0  # avg cost based on all buys
        # total_invested = buy_cost - sell_cost = 1500 - 510 = 990
        assert pos.total_invested == pytest.approx(990.0)

    def test_fully_sold_excluded(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        store.add_transaction("p1", "AAPL", "sell", 10, 170.0)
        positions = store.get_positions("p1")
        assert len(positions) == 0

    def test_multiple_tickers(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        store.add_transaction("p1", "MSFT", "buy", 5, 400.0)
        positions = store.get_positions("p1")
        assert len(positions) == 2
        tickers = {p.ticker for p in positions}
        assert tickers == {"AAPL", "MSFT"}

    def test_empty_portfolio(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        positions = store.get_positions("p1")
        assert positions == []


class TestPersistence:
    def test_data_persists(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        store1 = PortfolioStore(db_path=db)
        store1.create_portfolio("p1")
        store1.add_transaction("p1", "AAPL", "buy", 10, 150.0)

        store2 = PortfolioStore(db_path=db)
        positions = store2.get_positions("p1")
        assert len(positions) == 1
        assert positions[0].ticker == "AAPL"

    def test_cascade_delete(self, store: PortfolioStore) -> None:
        store.create_portfolio("p1")
        store.add_transaction("p1", "AAPL", "buy", 10, 150.0)
        store.delete_portfolio("p1")
        # Re-create same name — should work, no orphan txns
        store.create_portfolio("p1")
        assert store.get_transactions("p1") == []
