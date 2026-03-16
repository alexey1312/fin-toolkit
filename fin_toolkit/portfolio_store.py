"""SQLite-backed portfolio store."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from fin_toolkit.exceptions import PortfolioError
from fin_toolkit.models.portfolio import Position, Transaction

_DEFAULT_PATH = Path.home() / ".config" / "fin-toolkit" / "fin-toolkit.db"

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS portfolios (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('buy', 'sell')),
    shares REAL NOT NULL CHECK (shares > 0),
    price REAL NOT NULL CHECK (price > 0),
    fee REAL NOT NULL DEFAULT 0,
    executed_at TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_txn_portfolio ON transactions(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_txn_ticker ON transactions(portfolio_id, ticker);
"""


class PortfolioStore:
    """Persistent portfolio storage backed by SQLite."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or _DEFAULT_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------
    # Portfolios
    # ------------------------------------------------------------------

    def create_portfolio(
        self,
        name: str,
        currency: str = "USD",
        notes: str | None = None,
    ) -> int:
        """Create a new portfolio. Returns portfolio id."""
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    "INSERT INTO portfolios (name, currency, created_at, notes) "
                    "VALUES (?, ?, ?, ?)",
                    (name, currency, now, notes),
                )
                return cur.lastrowid  # type: ignore[return-value]
        except sqlite3.IntegrityError:
            raise PortfolioError(f"Portfolio '{name}' already exists") from None

    def list_portfolios(self) -> list[dict[str, str]]:
        """Return list of portfolios with name, currency, created_at."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT name, currency, created_at, notes FROM portfolios ORDER BY name",
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_portfolio(self, name: str) -> None:
        """Delete a portfolio and all its transactions."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM portfolios WHERE name = ?", (name,))
            if cur.rowcount == 0:
                raise PortfolioError(f"Portfolio '{name}' not found")

    def _get_portfolio_id(self, conn: sqlite3.Connection, name: str) -> int:
        row = conn.execute(
            "SELECT id FROM portfolios WHERE name = ?", (name,),
        ).fetchone()
        if row is None:
            raise PortfolioError(f"Portfolio '{name}' not found")
        return int(row["id"])

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def add_transaction(
        self,
        portfolio: str,
        ticker: str,
        action: str,
        shares: float,
        price: float,
        fee: float = 0,
        executed_at: str | None = None,
        notes: str | None = None,
    ) -> int:
        """Record a buy/sell transaction. Returns transaction id."""
        if action not in ("buy", "sell"):
            raise PortfolioError(f"Invalid action: '{action}'. Use 'buy' or 'sell'.")
        if shares <= 0:
            raise PortfolioError("Shares must be positive")
        if price <= 0:
            raise PortfolioError("Price must be positive")

        ts = executed_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        with self._connect() as conn:
            pid = self._get_portfolio_id(conn, portfolio)

            # Validate sell: cannot sell more than held
            if action == "sell":
                row = conn.execute(
                    "SELECT "
                    "  COALESCE(SUM(CASE WHEN action='buy' THEN shares ELSE 0 END), 0) "
                    "  - COALESCE(SUM(CASE WHEN action='sell' THEN shares ELSE 0 END), 0) "
                    "  AS held "
                    "FROM transactions WHERE portfolio_id = ? AND ticker = ?",
                    (pid, ticker),
                ).fetchone()
                held = row["held"] if row else 0.0
                if shares > held + 1e-9:  # float tolerance
                    raise PortfolioError(
                        f"Cannot sell {shares} shares of {ticker}: "
                        f"only {held:.4f} held"
                    )

            cur = conn.execute(
                "INSERT INTO transactions "
                "(portfolio_id, ticker, action, shares, price, fee, executed_at, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, ticker, action, shares, price, fee, ts, notes),
            )
            return cur.lastrowid  # type: ignore[return-value]

    def get_transactions(
        self,
        portfolio: str,
        ticker: str | None = None,
    ) -> list[Transaction]:
        """Get transactions for a portfolio, optionally filtered by ticker."""
        with self._connect() as conn:
            pid = self._get_portfolio_id(conn, portfolio)
            if ticker:
                rows = conn.execute(
                    "SELECT id, ticker, action, shares, price, fee, executed_at, notes "
                    "FROM transactions WHERE portfolio_id = ? AND ticker = ? "
                    "ORDER BY executed_at",
                    (pid, ticker),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, ticker, action, shares, price, fee, executed_at, notes "
                    "FROM transactions WHERE portfolio_id = ? "
                    "ORDER BY executed_at",
                    (pid,),
                ).fetchall()
        return [Transaction(**dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Computed positions
    # ------------------------------------------------------------------

    def get_positions(self, portfolio: str) -> list[Position]:
        """Compute current positions from transactions (no live prices)."""
        with self._connect() as conn:
            pid = self._get_portfolio_id(conn, portfolio)
            rows = conn.execute(
                "SELECT "
                "  ticker, "
                "  SUM(CASE WHEN action='buy' THEN shares ELSE 0 END) "
                "    - SUM(CASE WHEN action='sell' THEN shares ELSE 0 END) AS shares, "
                "  SUM(CASE WHEN action='buy' THEN shares * price ELSE 0 END) AS buy_cost, "
                "  SUM(CASE WHEN action='buy' THEN shares ELSE 0 END) AS buy_shares, "
                "  SUM(CASE WHEN action='buy' THEN shares * price ELSE 0 END) "
                "    - SUM(CASE WHEN action='sell' THEN shares * price ELSE 0 END) "
                "    AS total_invested "
                "FROM transactions WHERE portfolio_id = ? "
                "GROUP BY ticker "
                "HAVING (SUM(CASE WHEN action='buy' THEN shares ELSE 0 END) "
                "  - SUM(CASE WHEN action='sell' THEN shares ELSE 0 END)) > 1e-9",
                (pid,),
            ).fetchall()

        positions: list[Position] = []
        for r in rows:
            buy_shares = r["buy_shares"]
            buy_cost = r["buy_cost"]
            avg_cost = buy_cost / buy_shares if buy_shares > 0 else 0
            positions.append(Position(
                ticker=r["ticker"],
                shares=r["shares"],
                avg_cost=avg_cost,
                total_invested=r["total_invested"],
            ))
        return positions
