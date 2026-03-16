"""Tests for watchlist store."""

from __future__ import annotations

from pathlib import Path

import pytest

from fin_toolkit.analysis.alerts import AlertRule, WatchlistEntry
from fin_toolkit.exceptions import WatchlistError
from fin_toolkit.watchlist import WatchlistStore


@pytest.fixture
def tmp_store(tmp_path: Path) -> WatchlistStore:
    """Create a WatchlistStore with a temp directory."""
    return WatchlistStore(path=tmp_path / "watchlists.yaml")


class TestWatchlistStore:
    def test_initial_empty(self, tmp_store: WatchlistStore) -> None:
        assert tmp_store.list_watchlists() == []

    def test_add_ticker(self, tmp_store: WatchlistStore) -> None:
        entry = WatchlistEntry(ticker="AAPL", added_at="2024-01-01", notes="test")
        tmp_store.add_ticker("default", entry)
        names = tmp_store.list_watchlists()
        assert "default" in names

    def test_get_watchlist(self, tmp_store: WatchlistStore) -> None:
        entry = WatchlistEntry(ticker="AAPL", added_at="2024-01-01")
        tmp_store.add_ticker("default", entry)
        items = tmp_store.get_watchlist("default")
        assert len(items) == 1
        assert items[0].ticker == "AAPL"

    def test_add_multiple_tickers(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        tmp_store.add_ticker("default", WatchlistEntry(ticker="MSFT", added_at="2024-01-02"))
        items = tmp_store.get_watchlist("default")
        assert len(items) == 2

    def test_duplicate_ticker_raises(self, tmp_store: WatchlistStore) -> None:
        entry = WatchlistEntry(ticker="AAPL", added_at="2024-01-01")
        tmp_store.add_ticker("default", entry)
        with pytest.raises(WatchlistError, match="already in"):
            tmp_store.add_ticker("default", entry)

    def test_remove_ticker(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        tmp_store.add_ticker("default", WatchlistEntry(ticker="MSFT", added_at="2024-01-02"))
        tmp_store.remove_ticker("default", "AAPL")
        items = tmp_store.get_watchlist("default")
        assert len(items) == 1
        assert items[0].ticker == "MSFT"

    def test_remove_nonexistent_raises(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        with pytest.raises(WatchlistError, match="not found"):
            tmp_store.remove_ticker("default", "MSFT")

    def test_get_nonexistent_watchlist_raises(self, tmp_store: WatchlistStore) -> None:
        with pytest.raises(WatchlistError, match="not found"):
            tmp_store.get_watchlist("nonexistent")

    def test_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "watchlists.yaml"
        store1 = WatchlistStore(path=path)
        store1.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))

        store2 = WatchlistStore(path=path)
        items = store2.get_watchlist("default")
        assert len(items) == 1
        assert items[0].ticker == "AAPL"

    def test_set_alert(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        alert = AlertRule(metric="pe_ratio", operator=">", threshold=25.0, label="High P/E")
        tmp_store.set_alert("default", "AAPL", alert)
        items = tmp_store.get_watchlist("default")
        assert len(items[0].alerts) == 1
        assert items[0].alerts[0].metric == "pe_ratio"

    def test_set_alert_nonexistent_ticker_raises(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        alert = AlertRule(metric="pe_ratio", operator=">", threshold=25.0)
        with pytest.raises(WatchlistError, match="not found"):
            tmp_store.set_alert("default", "MSFT", alert)

    def test_multiple_watchlists(self, tmp_store: WatchlistStore) -> None:
        tmp_store.add_ticker("tech", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        tmp_store.add_ticker("energy", WatchlistEntry(ticker="XOM", added_at="2024-01-01"))
        names = tmp_store.list_watchlists()
        assert set(names) == {"tech", "energy"}

    def test_alert_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "watchlists.yaml"
        store1 = WatchlistStore(path=path)
        store1.add_ticker("default", WatchlistEntry(ticker="AAPL", added_at="2024-01-01"))
        store1.set_alert("default", "AAPL", AlertRule(metric="rsi", operator="<", threshold=30.0))

        store2 = WatchlistStore(path=path)
        items = store2.get_watchlist("default")
        assert len(items[0].alerts) == 1
        assert items[0].alerts[0].metric == "rsi"
