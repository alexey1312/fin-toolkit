"""Tests for AgentRegistry."""

from __future__ import annotations

import pytest

from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.agents.registry import AgentRegistry
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.config.models import AgentsConfig, ToolkitConfig
from fin_toolkit.exceptions import AgentNotFoundError
from fin_toolkit.models.financial import FinancialStatements, KeyMetrics
from fin_toolkit.models.price_data import PriceData, PricePoint

# ---------------------------------------------------------------------------
# Mock data provider
# ---------------------------------------------------------------------------

class MockDataProvider:
    async def get_prices(self, ticker: str, start: str, end: str) -> PriceData:
        return PriceData(
            ticker=ticker,
            period="1y",
            prices=[
                PricePoint(
                    date="2024-01-01",
                    open=100.0, high=105.0, low=98.0, close=102.0, volume=1_000_000,
                )
            ],
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        return FinancialStatements(
            ticker=ticker, income_statement={}, balance_sheet={}, cash_flow={},
        )

    async def get_metrics(self, ticker: str) -> KeyMetrics:
        return KeyMetrics(
            ticker=ticker,
            pe_ratio=20.0, pb_ratio=3.0, market_cap=1_000_000_000,
            dividend_yield=0.01, roe=0.15, roa=0.08, debt_to_equity=1.0,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_agents_from_config() -> None:
    """Registry loads agents listed in config.agents.active."""
    all_agents = [
        "elvis_marlamov", "warren_buffett",
        "ben_graham", "charlie_munger", "cathie_wood", "peter_lynch",
    ]
    config = ToolkitConfig(agents=AgentsConfig(active=all_agents))
    registry = AgentRegistry(
        config=config,
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    agents = registry.get_active_agents()
    for name in all_agents:
        assert name in agents
    assert len(agents) == len(all_agents)


def test_get_agent_returns_instance() -> None:
    """get_agent returns an AnalysisAgent instance."""
    config = ToolkitConfig(agents=AgentsConfig(active=["elvis_marlamov"]))
    registry = AgentRegistry(
        config=config,
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    agent = registry.get_agent("elvis_marlamov")
    assert isinstance(agent, AnalysisAgent)


def test_unknown_agent_raises() -> None:
    """Requesting an unknown agent raises AgentNotFoundError."""
    config = ToolkitConfig(agents=AgentsConfig(active=["elvis_marlamov"]))
    registry = AgentRegistry(
        config=config,
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    with pytest.raises(AgentNotFoundError, match="nonexistent"):
        registry.get_agent("nonexistent")


def test_get_active_agents_returns_correct_instances() -> None:
    """get_active_agents returns dict mapping name → AnalysisAgent."""
    config = ToolkitConfig(agents=AgentsConfig(active=["warren_buffett"]))
    registry = AgentRegistry(
        config=config,
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    agents = registry.get_active_agents()
    assert len(agents) == 1
    assert "warren_buffett" in agents
    assert isinstance(agents["warren_buffett"], AnalysisAgent)


def test_empty_active_agents() -> None:
    """Empty active list → empty dict from get_active_agents."""
    config = ToolkitConfig(agents=AgentsConfig(active=[]))
    registry = AgentRegistry(
        config=config,
        data_provider=MockDataProvider(),
        technical=TechnicalAnalyzer(),
        fundamental=FundamentalAnalyzer(),
    )
    assert registry.get_active_agents() == {}
