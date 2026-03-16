"""Custom exceptions for fin-toolkit."""

from __future__ import annotations


class FinToolkitError(Exception):
    """Base exception for fin-toolkit."""

    @property
    def hint(self) -> str:
        return ""


class TickerNotFoundError(FinToolkitError):
    """Raised when a ticker is not found by the provider."""

    def __init__(self, ticker: str, provider: str = "") -> None:
        self.ticker = ticker
        self.provider = provider
        msg = f"Ticker '{ticker}' not found"
        if provider:
            msg += f" in {provider}"
        super().__init__(msg)

    @property
    def hint(self) -> str:
        if self.provider:
            return (
                f"Ticker may not be listed on {self.provider}. "
                "Try without specifying provider."
            )
        return (
            "Check ticker symbol. "
            "Moscow Exchange uses MOEX codes (SBER, not SBER.ME)."
        )


class ProviderUnavailableError(FinToolkitError):
    """Raised when a provider is temporarily unavailable."""

    def __init__(self, provider: str, reason: str = "") -> None:
        self.provider = provider
        self.reason = reason
        msg = f"Provider '{provider}' is unavailable"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)

    @property
    def hint(self) -> str:
        return (
            f"Provider '{self.provider}' may be down or misconfigured. "
            "Run 'fin-toolkit status' to check."
        )


class AllProvidersFailedError(FinToolkitError):
    """Raised when all providers in the fallback chain fail."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        details = ", ".join(f"{p}: {e}" for p, e in errors.items())
        super().__init__(f"All providers failed: {details}")

    @property
    def hint(self) -> str:
        return (
            "Run 'fin-toolkit status' to check providers. "
            "For Russian tickers try provider='moex'."
        )


class ProviderConfigError(FinToolkitError):
    """Raised when provider configuration is invalid or missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

    @property
    def hint(self) -> str:
        return "Check fin-toolkit.yaml or environment variables."


class InsufficientDataError(FinToolkitError):
    """Raised when there is not enough data for analysis."""

    def __init__(self, required: int, available: int, context: str = "") -> None:
        self.required = required
        self.available = available
        msg = f"Insufficient data: need {required}, have {available}"
        if context:
            msg += f" ({context})"
        super().__init__(msg)

    @property
    def hint(self) -> str:
        return "Try a shorter period or a different provider with more history."


class AgentNotFoundError(FinToolkitError):
    """Raised when a requested agent is not found in the registry."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}' not found in registry")

    @property
    def hint(self) -> str:
        return (
            "Available agents: elvis_marlamov, warren_buffett, "
            "ben_graham, charlie_munger, cathie_wood, peter_lynch."
        )


class ConfigError(FinToolkitError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidFilterError(FinToolkitError):
    """Raised when a screener filter expression is malformed."""

    def __init__(self, expression: str, reason: str = "") -> None:
        self.expression = expression
        msg = f"Invalid filter: '{expression}'"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)

    @property
    def hint(self) -> str:
        return (
            "Supported operators: <, >, <=, >=, =, min..max. "
            'Example: {"pe_ratio": "<15", "roe": ">0.10"}.'
        )


class WatchlistError(FinToolkitError):
    """Raised for watchlist-specific errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
