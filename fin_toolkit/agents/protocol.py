"""AnalysisAgent protocol definition."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fin_toolkit.models.results import AgentResult


@runtime_checkable
class AnalysisAgent(Protocol):
    """Async protocol for analysis agents."""

    async def analyze(self, ticker: str) -> AgentResult:
        """Analyze a ticker and return an AgentResult."""
        ...
