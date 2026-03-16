"""YAML-backed watchlist store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fin_toolkit.analysis.alerts import AlertRule, WatchlistEntry
from fin_toolkit.exceptions import WatchlistError

_DEFAULT_PATH = Path.home() / ".config" / "fin-toolkit" / "watchlists.yaml"


class WatchlistStore:
    """Persistent watchlist storage backed by a YAML file."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or _DEFAULT_PATH

    def _load_raw(self) -> dict[str, list[dict[str, Any]]]:
        """Load raw YAML data."""
        if not self._path.exists():
            return {}
        text = self._path.read_text()
        if not text.strip():
            return {}
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}

    def _save_raw(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """Save raw data to YAML."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    def _entry_to_dict(self, entry: WatchlistEntry) -> dict[str, Any]:
        """Serialize WatchlistEntry to dict."""
        d: dict[str, Any] = {
            "ticker": entry.ticker,
            "added_at": entry.added_at,
        }
        if entry.notes:
            d["notes"] = entry.notes
        if entry.alerts:
            d["alerts"] = [
                {
                    "metric": a.metric,
                    "operator": a.operator,
                    "threshold": a.threshold,
                    **({"label": a.label} if a.label else {}),
                }
                for a in entry.alerts
            ]
        return d

    def _dict_to_entry(self, d: dict[str, Any]) -> WatchlistEntry:
        """Deserialize dict to WatchlistEntry."""
        alerts_raw = d.get("alerts", [])
        alerts = [
            AlertRule(
                metric=a["metric"],
                operator=a["operator"],
                threshold=float(a["threshold"]),
                label=a.get("label"),
            )
            for a in alerts_raw
        ]
        return WatchlistEntry(
            ticker=d["ticker"],
            added_at=d.get("added_at", ""),
            notes=d.get("notes"),
            alerts=alerts,
        )

    def load(self) -> dict[str, list[WatchlistEntry]]:
        """Load all watchlists."""
        raw = self._load_raw()
        result: dict[str, list[WatchlistEntry]] = {}
        for name, entries in raw.items():
            result[name] = [self._dict_to_entry(e) for e in entries]
        return result

    def save(self, watchlists: dict[str, list[WatchlistEntry]]) -> None:
        """Save all watchlists."""
        raw: dict[str, list[dict[str, Any]]] = {}
        for name, entries in watchlists.items():
            raw[name] = [self._entry_to_dict(e) for e in entries]
        self._save_raw(raw)

    def list_watchlists(self) -> list[str]:
        """Return names of all watchlists."""
        return list(self._load_raw().keys())

    def get_watchlist(self, name: str) -> list[WatchlistEntry]:
        """Get entries of a specific watchlist."""
        data = self.load()
        if name not in data:
            raise WatchlistError(f"Watchlist '{name}' not found")
        return data[name]

    def add_ticker(self, name: str, entry: WatchlistEntry) -> None:
        """Add a ticker to a watchlist. Creates watchlist if it doesn't exist."""
        data = self.load()
        entries = data.get(name, [])
        if any(e.ticker == entry.ticker for e in entries):
            raise WatchlistError(
                f"Ticker '{entry.ticker}' already in watchlist '{name}'"
            )
        entries.append(entry)
        data[name] = entries
        self.save(data)

    def remove_ticker(self, name: str, ticker: str) -> None:
        """Remove a ticker from a watchlist."""
        data = self.load()
        if name not in data:
            raise WatchlistError(f"Watchlist '{name}' not found")
        entries = data[name]
        new_entries = [e for e in entries if e.ticker != ticker]
        if len(new_entries) == len(entries):
            raise WatchlistError(
                f"Ticker '{ticker}' not found in watchlist '{name}'"
            )
        data[name] = new_entries
        self.save(data)

    def set_alert(self, name: str, ticker: str, alert: AlertRule) -> None:
        """Add an alert rule to a ticker in a watchlist."""
        data = self.load()
        if name not in data:
            raise WatchlistError(f"Watchlist '{name}' not found")
        found = False
        for entry in data[name]:
            if entry.ticker == ticker:
                entry.alerts.append(alert)
                found = True
                break
        if not found:
            raise WatchlistError(
                f"Ticker '{ticker}' not found in watchlist '{name}'"
            )
        self.save(data)
