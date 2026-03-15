"""Analysis agents for fin-toolkit."""

from fin_toolkit.agents.buffett import WarrenBuffettAgent
from fin_toolkit.agents.elvis import ElvisMarlamovAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.agents.registry import AgentRegistry

__all__ = [
    "AgentRegistry",
    "AnalysisAgent",
    "ElvisMarlamovAgent",
    "WarrenBuffettAgent",
]
