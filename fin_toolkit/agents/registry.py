"""Agent registry for loading and managing analysis agents."""

from __future__ import annotations

from fin_toolkit.agents.protocol import AnalysisAgent
from fin_toolkit.analysis.fundamental import FundamentalAnalyzer
from fin_toolkit.analysis.technical import TechnicalAnalyzer
from fin_toolkit.config.models import ToolkitConfig
from fin_toolkit.exceptions import AgentNotFoundError
from fin_toolkit.providers.protocol import DataProvider
from fin_toolkit.providers.search_protocol import SearchProvider


class AgentRegistry:
    """Registry that loads and manages analysis agents based on config."""

    # Map of known agent names → factory callables
    _AGENT_FACTORIES: dict[str, str] = {
        "elvis_marlamov": "fin_toolkit.agents.elvis.ElvisMarlamovAgent",
        "warren_buffett": "fin_toolkit.agents.buffett.WarrenBuffettAgent",
        "ben_graham": "fin_toolkit.agents.graham.BenGrahamAgent",
        "charlie_munger": "fin_toolkit.agents.munger.CharlieMungerAgent",
        "cathie_wood": "fin_toolkit.agents.wood.CathieWoodAgent",
        "peter_lynch": "fin_toolkit.agents.lynch.PeterLynchAgent",
    }

    def __init__(
        self,
        config: ToolkitConfig,
        data_provider: DataProvider,
        technical: TechnicalAnalyzer,
        fundamental: FundamentalAnalyzer,
        search: SearchProvider | None = None,
    ) -> None:
        self._config = config
        self._data_provider = data_provider
        self._technical = technical
        self._fundamental = fundamental
        self._search = search
        self._agents: dict[str, AnalysisAgent] = {}
        self._load_agents()

    def _load_agents(self) -> None:
        """Instantiate agents listed in config.agents.active."""
        from fin_toolkit.agents.buffett import WarrenBuffettAgent
        from fin_toolkit.agents.elvis import ElvisMarlamovAgent
        from fin_toolkit.agents.graham import BenGrahamAgent
        from fin_toolkit.agents.lynch import PeterLynchAgent
        from fin_toolkit.agents.munger import CharlieMungerAgent
        from fin_toolkit.agents.wood import CathieWoodAgent

        # Agents that accept a search provider
        search_agents = {"elvis_marlamov"}

        factories: dict[str, type] = {
            "elvis_marlamov": ElvisMarlamovAgent,
            "warren_buffett": WarrenBuffettAgent,
            "ben_graham": BenGrahamAgent,
            "charlie_munger": CharlieMungerAgent,
            "cathie_wood": CathieWoodAgent,
            "peter_lynch": PeterLynchAgent,
        }

        for name in self._config.agents.active:
            cls = factories.get(name)
            if cls is None:
                continue  # skip unknown agents at load time

            kwargs: dict[str, object] = {
                "data_provider": self._data_provider,
                "technical": self._technical,
                "fundamental": self._fundamental,
            }
            if name in search_agents:
                kwargs["search"] = self._search

            self._agents[name] = cls(**kwargs)

    def get_agent(self, name: str) -> AnalysisAgent:
        """Get an agent by name. Raises AgentNotFoundError if not found."""
        if name not in self._agents:
            raise AgentNotFoundError(name)
        return self._agents[name]

    def get_active_agents(self) -> dict[str, AnalysisAgent]:
        """Return all active agents as a dict mapping name → agent."""
        return dict(self._agents)
