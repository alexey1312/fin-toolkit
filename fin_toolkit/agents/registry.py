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

        factories: dict[str, type[ElvisMarlamovAgent | WarrenBuffettAgent]] = {
            "elvis_marlamov": ElvisMarlamovAgent,
            "warren_buffett": WarrenBuffettAgent,
        }

        for name in self._config.agents.active:
            if name not in factories:
                continue  # skip unknown agents at load time
            if name == "elvis_marlamov":
                agent: AnalysisAgent = ElvisMarlamovAgent(
                    data_provider=self._data_provider,
                    technical=self._technical,
                    fundamental=self._fundamental,
                    search=self._search,
                )
            else:
                agent = WarrenBuffettAgent(
                    data_provider=self._data_provider,
                    technical=self._technical,
                    fundamental=self._fundamental,
                )
            self._agents[name] = agent

    def get_agent(self, name: str) -> AnalysisAgent:
        """Get an agent by name. Raises AgentNotFoundError if not found."""
        if name not in self._agents:
            raise AgentNotFoundError(name)
        return self._agents[name]

    def get_active_agents(self) -> dict[str, AnalysisAgent]:
        """Return all active agents as a dict mapping name → agent."""
        return dict(self._agents)
