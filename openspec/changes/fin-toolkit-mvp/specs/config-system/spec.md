## ADDED Requirements

### Requirement: YAML configuration file
The system SHALL read configuration from `fin-toolkit.yaml` with sections: `data`, `search`, `agents`, `markets`, `api_keys`. All API keys SHALL be optional.

#### Scenario: Load valid configuration
- **WHEN** `fin-toolkit.yaml` exists with `data.primary: yahoo` and `agents.active: [elvis_marlamov]`
- **THEN** the system SHALL initialize Yahoo Finance as primary provider and Elvis Marlamov agent

#### Scenario: Missing configuration file
- **WHEN** no config file is found in `./fin-toolkit.yaml` or `~/.config/fin-toolkit/config.yaml`
- **THEN** the system SHALL use default configuration: Yahoo Finance as primary, no search provider, Elvis Marlamov agent active

#### Scenario: Local config overrides global
- **WHEN** both `./fin-toolkit.yaml` and `~/.config/fin-toolkit/config.yaml` exist
- **THEN** the system SHALL use `./fin-toolkit.yaml` (local takes precedence over global XDG config)

#### Scenario: Invalid configuration
- **WHEN** `fin-toolkit.yaml` contains `data.primary: nonexistent_provider`
- **THEN** the system SHALL raise `ConfigError` listing available providers

### Requirement: Environment variable override for secrets
API keys SHALL be readable from environment variables or `.env` file, taking precedence over `fin-toolkit.yaml` values.

#### Scenario: API key from environment
- **WHEN** `BRAVE_API_KEY` is set in environment and `fin-toolkit.yaml` has empty `api_keys.BRAVE_API_KEY`
- **THEN** the system SHALL use the environment variable value

#### Scenario: .env file support
- **WHEN** a `.env` file exists in the project root with `FMP_API_KEY=abc123`
- **THEN** the system SHALL load it and make FMP provider available

### Requirement: Provider auto-detection
The system SHALL automatically detect which providers are available based on configured API keys.

#### Scenario: No keys configured
- **WHEN** no API keys are present
- **THEN** only key-free providers (Yahoo Finance, KASE scraper) SHALL be available. SearXNG requires a configured base URL (not an API key) and SHALL only be available if `search.searxng.base_url` is set.

#### Scenario: YAML references unavailable provider
- **WHEN** `fin-toolkit.yaml` has `data.primary: fmp` but no `FMP_API_KEY` is configured
- **THEN** the system SHALL raise `ConfigError` indicating that provider `fmp` requires `FMP_API_KEY`

#### Scenario: Brave key configured
- **WHEN** `BRAVE_API_KEY` is set
- **THEN** Brave Search SHALL be added to available search providers and usable as primary or fallback

### Requirement: Rate limiting configuration
The configuration SHALL support per-provider rate limits in `fin-toolkit.yaml`, with both `requests_per_minute` (token bucket) and `max_concurrent` (semaphore) settings.

#### Scenario: Custom rate limit
- **WHEN** config has `data.providers.yahoo.rate_limit.requests_per_minute: 10`
- **THEN** the system SHALL enforce 10 req/min for Yahoo Finance provider

#### Scenario: Default rate limits
- **WHEN** no `rate_limit` is configured for a provider
- **THEN** the system SHALL use defaults: Yahoo Finance = 5 rpm / 2 concurrent, KASE = 2 rpm / 1 concurrent, FMP = 30 rpm / 5 concurrent

### Requirement: Market-to-provider mapping
The configuration SHALL support a `markets` section that maps tickers to specific providers, overriding the fallback chain.

#### Scenario: KZ market mapping
- **WHEN** config has `markets.kz: {tickers: [KCEL, KZTO, HSBK], provider: kase}`
- **THEN** the system SHALL route requests for KCEL, KZTO, HSBK to KASEProvider directly

#### Scenario: Market mapping with custom tickers
- **WHEN** user adds `markets.custom: {tickers: [MYSTOCK], provider: fmp}`
- **THEN** the system SHALL route MYSTOCK to FMP provider

### Requirement: Configuration priority
The configuration SHALL follow strict priority order: environment variables > .env file > fin-toolkit.yaml > built-in defaults. This SHALL be clearly documented.

#### Scenario: Env var overrides YAML
- **WHEN** `fin-toolkit.yaml` has `data.primary: yahoo` and env var `FIN_TOOLKIT_DATA_PRIMARY=fmp` is set
- **THEN** the system SHALL use `fmp` as primary provider

### Requirement: Pydantic validation for config
The configuration SHALL be validated through Pydantic models at load time.

#### Scenario: Type validation
- **WHEN** `agents.active` is set to a string instead of a list
- **THEN** the system SHALL raise a clear validation error indicating the expected type
