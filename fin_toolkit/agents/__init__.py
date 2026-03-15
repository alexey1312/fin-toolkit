"""Analysis agents for fin-toolkit."""

from fin_toolkit.agents.buffett import WarrenBuffettAgent
from fin_toolkit.agents.elvis import ElvisMarlamovAgent
from fin_toolkit.agents.graham import BenGrahamAgent
from fin_toolkit.agents.lynch import PeterLynchAgent
from fin_toolkit.agents.munger import CharlieMungerAgent
from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.agents.registry import AgentRegistry
from fin_toolkit.agents.wood import CathieWoodAgent

__all__ = [
    "AgentRegistry",
    "AnalysisAgent",
    "BenGrahamAgent",
    "CathieWoodAgent",
    "CharlieMungerAgent",
    "ElvisMarlamovAgent",
    "PeterLynchAgent",
    "WarrenBuffettAgent",
]
