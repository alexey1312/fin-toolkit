"""Tests for AnalysisAgent protocol compliance."""

from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.models.results import AgentResult


class _MockAgent:
    """A mock class that satisfies the AnalysisAgent protocol."""

    async def analyze(self, ticker: str) -> AgentResult:
        return AgentResult(
            signal="Bullish",
            score=80.0,
            confidence=1.0,
            rationale="Mock analysis",
            breakdown={"quality": 40.0},
            warnings=[],
        )


class _BadAgent:
    """A class that does NOT satisfy the AnalysisAgent protocol."""

    def not_analyze(self, ticker: str) -> str:
        return "nope"


def test_mock_agent_satisfies_protocol() -> None:
    """A class with async analyze(ticker) -> AgentResult is a valid AnalysisAgent."""
    agent = _MockAgent()
    assert isinstance(agent, AnalysisAgent)


def test_bad_agent_does_not_satisfy_protocol() -> None:
    """A class without analyze() does not satisfy the AnalysisAgent protocol."""
    bad = _BadAgent()
    assert not isinstance(bad, AnalysisAgent)


async def test_mock_agent_returns_agent_result() -> None:
    """Calling analyze returns a proper AgentResult."""
    agent = _MockAgent()
    result = await agent.analyze("AAPL")
    assert isinstance(result, AgentResult)
    assert result.signal == "Bullish"
    assert result.score == 80.0
    assert result.confidence == 1.0
