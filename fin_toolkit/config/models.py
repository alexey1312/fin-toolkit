"""Pydantic models for fin-toolkit configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, Field


class RateLimitConfig(BaseModel):
    """Rate limiting configuration for a provider."""

    requests_per_minute: int = 5
    max_concurrent: int = 2


class DataConfig(BaseModel):
    """Data provider configuration."""

    primary_provider: str = "yahoo"
    fallback_providers: list[str] = Field(
        default_factory=lambda: ["smartlab", "moex", "financialdatasets", "edgar"],
    )


class SearchConfig(BaseModel):
    """Search provider configuration."""

    providers: list[str] = Field(
        default_factory=lambda: [
            "duckduckgo", "searxng", "google", "perplexity", "tavily", "brave", "serper", "exa",
        ],
    )
    searxng_url: str = "http://localhost:8888"
    gemini_model: str = "gemini-3.1-flash-lite"


class AgentsConfig(BaseModel):
    """Agent configuration."""

    active: list[str] = Field(
        default_factory=lambda: [
            "elvis_marlamov",
            "warren_buffett",
            "ben_graham",
            "charlie_munger",
            "cathie_wood",
            "peter_lynch",
        ],
    )


class MarketConfig(BaseModel):
    """Market-to-provider mapping."""

    provider: str
    tickers: list[str]


DEFAULT_RATE_LIMITS: dict[str, RateLimitConfig] = {
    "yahoo": RateLimitConfig(requests_per_minute=5, max_concurrent=2),
    "kase": RateLimitConfig(requests_per_minute=2, max_concurrent=1),
    "moex": RateLimitConfig(requests_per_minute=10, max_concurrent=3),
    "smartlab": RateLimitConfig(requests_per_minute=5, max_concurrent=2),
    "fmp": RateLimitConfig(requests_per_minute=30, max_concurrent=5),
    "financialdatasets": RateLimitConfig(requests_per_minute=30, max_concurrent=5),
    "brave": RateLimitConfig(requests_per_minute=10, max_concurrent=3),
}

DEFAULT_MARKETS: dict[str, MarketConfig] = {
    "kz": MarketConfig(
        provider="kase",
        tickers=["KCEL", "KZTO", "KEGC", "HSBK", "CCBN", "KZAP"],
    ),
}

# Providers that don't need API keys
KEY_FREE_PROVIDERS = {"yahoo", "kase", "moex", "smartlab"}

# Environment variable names for API keys
PROVIDER_KEY_MAP: dict[str, str] = {
    "fmp": "FMP_API_KEY",
    "financialdatasets": "FINANCIAL_DATASETS_API_KEY",
    "brave": "BRAVE_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "tavily": "TAVILY_API_KEY",
    "serper": "SERPER_API_KEY",
    "exa": "EXA_API_KEY",
    "google": "GEMINI_API_KEY",
}

# Search providers that need configuration (not API keys)
SEARCH_URL_PROVIDERS: dict[str, str] = {
    "searxng": "searxng_url",
}


class ToolkitConfig(BaseModel):
    """Root configuration for fin-toolkit."""

    data: DataConfig = Field(default_factory=DataConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    rate_limits: dict[str, RateLimitConfig] = Field(default_factory=dict)
    markets: dict[str, MarketConfig] = Field(default_factory=dict)
    api_keys: dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        # Apply default rate limits for missing providers
        for provider, rl_config in DEFAULT_RATE_LIMITS.items():
            if provider not in self.rate_limits:
                self.rate_limits[provider] = rl_config

        # Apply default markets for missing entries
        for market, mkt_config in DEFAULT_MARKETS.items():
            if market not in self.markets:
                self.markets[market] = mkt_config

    def available_providers(self) -> list[str]:
        """Return list of available data providers based on API keys."""
        available = list(KEY_FREE_PROVIDERS)
        for provider, env_var in PROVIDER_KEY_MAP.items():
            if self.api_keys.get(provider) or os.environ.get(env_var):
                available.append(provider)
        return sorted(available)

    def available_search_providers(self) -> list[str]:
        """Return list of available search providers."""
        available: list[str] = []
        key_based = ("google", "perplexity", "tavily", "brave", "serper", "exa")
        for provider in key_based:
            env_var = PROVIDER_KEY_MAP.get(provider, "")
            if self.api_keys.get(provider) or os.environ.get(env_var):
                available.append(provider)
        # DuckDuckGo is always available (no API key needed)
        available.append("duckduckgo")
        # SearXNG is available if URL is configured
        if self.search.searxng_url:
            available.append("searxng")
        return sorted(available)

    def get_ticker_provider(self, ticker: str) -> str | None:
        """Get the designated provider for a ticker from market mapping."""
        for market in self.markets.values():
            if ticker in market.tickers:
                return market.provider
        return None
