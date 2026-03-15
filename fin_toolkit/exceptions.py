"""Custom exceptions for fin-toolkit."""


class FinToolkitError(Exception):
    """Base exception for fin-toolkit."""


class TickerNotFoundError(FinToolkitError):
    """Raised when a ticker is not found by the provider."""

    def __init__(self, ticker: str, provider: str = "") -> None:
        self.ticker = ticker
        self.provider = provider
        msg = f"Ticker '{ticker}' not found"
        if provider:
            msg += f" in {provider}"
        super().__init__(msg)


class ProviderUnavailableError(FinToolkitError):
    """Raised when a provider is temporarily unavailable."""

    def __init__(self, provider: str, reason: str = "") -> None:
        self.provider = provider
        self.reason = reason
        msg = f"Provider '{provider}' is unavailable"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class AllProvidersFailedError(FinToolkitError):
    """Raised when all providers in the fallback chain fail."""

    def __init__(self, errors: dict[str, str]) -> None:
        self.errors = errors
        details = ", ".join(f"{p}: {e}" for p, e in errors.items())
        super().__init__(f"All providers failed: {details}")


class ProviderConfigError(FinToolkitError):
    """Raised when provider configuration is invalid or missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InsufficientDataError(FinToolkitError):
    """Raised when there is not enough data for analysis."""

    def __init__(self, required: int, available: int, context: str = "") -> None:
        self.required = required
        self.available = available
        msg = f"Insufficient data: need {required}, have {available}"
        if context:
            msg += f" ({context})"
        super().__init__(msg)


class AgentNotFoundError(FinToolkitError):
    """Raised when a requested agent is not found in the registry."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        super().__init__(f"Agent '{agent_name}' not found in registry")


class ConfigError(FinToolkitError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
