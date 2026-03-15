## ADDED Requirements

### Requirement: SearchProvider Protocol interface
The system SHALL define a `@runtime_checkable` async `SearchProvider` Protocol with method `async search(query: str, max_results: int) -> list[SearchResult]`. SearchResult SHALL contain: `title`, `url`, `snippet`, `published_date` (optional).

#### Scenario: Provider implements SearchProvider Protocol
- **WHEN** a class implements `search(query: str, max_results: int) -> list[SearchResult]`
- **THEN** it SHALL be accepted as a valid `SearchProvider`

### Requirement: Brave Search provider
The system SHALL provide a `BraveSearchProvider` that implements `SearchProvider` using the Brave Search API. It SHALL require `BRAVE_API_KEY` from configuration.

#### Scenario: Search financial news
- **WHEN** `search("SBER earnings 2024", max_results=5)` is called
- **THEN** the system SHALL return up to 5 `SearchResult` objects with relevant news articles

#### Scenario: Missing API key
- **WHEN** `BraveSearchProvider` is instantiated without `BRAVE_API_KEY` configured
- **THEN** the system SHALL raise `ProviderConfigError` indicating the missing key

### Requirement: SearXNG provider
The system SHALL provide a `SearXNGProvider` that implements `SearchProvider` using a self-hosted SearXNG instance. No API key SHALL be required — only a base URL.

#### Scenario: Search with SearXNG
- **WHEN** `search("KCEL Kazakhstan stock analysis", max_results=10)` is called
- **THEN** the system SHALL query the configured SearXNG instance and return `SearchResult` objects

#### Scenario: SearXNG instance unavailable
- **WHEN** the configured SearXNG base URL is unreachable
- **THEN** the system SHALL raise `ProviderUnavailableError` with the URL in the message

### Requirement: SearchProvider Protocol as async
The `SearchProvider` Protocol SHALL be `@runtime_checkable` and async: `async search(query: str, max_results: int) -> list[SearchResult]`. This is consistent with `DataProvider` Protocol — all provider protocols are async.

### Requirement: Search fallback chain
The system SHALL support fallback for search providers analogous to data providers, configured in `fin-toolkit.yaml`.

#### Scenario: Primary search fails, fallback succeeds
- **WHEN** primary search provider fails
- **AND** a fallback search provider is configured and available
- **THEN** the system SHALL transparently use the fallback provider

### Requirement: Graceful degradation when no search provider
The system SHALL handle the case where no SearchProvider is configured (no API keys, no SearXNG instance).

#### Scenario: No search provider available
- **WHEN** no SearchProvider is configured
- **THEN** `SearchRouter` SHALL return an empty list and the MCP `search_news` tool SHALL return `[]` with a warning, not raise an error
