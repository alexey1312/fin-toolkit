## ADDED Requirements

### Requirement: DataProvider Protocol interface
The system SHALL define a `@runtime_checkable` async `DataProvider` Protocol with three methods: `async get_prices(ticker, start, end) -> PriceData`, `async get_financials(ticker) -> FinancialStatements`, `async get_metrics(ticker) -> KeyMetrics`. All data providers MUST satisfy this Protocol. Return types are Pydantic models, not raw dicts or DataFrames. Synchronous providers (e.g. yfinance) SHALL use `asyncio.to_thread` to wrap blocking calls.

#### Scenario: Provider implements DataProvider Protocol
- **WHEN** a new data provider class implements `get_prices`, `get_financials`, and `get_metrics` methods with correct signatures and Pydantic return types
- **THEN** it SHALL be accepted as a valid `DataProvider` without explicit inheritance

#### Scenario: Provider missing required method
- **WHEN** a class is used as `DataProvider` but does not implement `get_financials`
- **THEN** mypy SHALL report a type error at static analysis time

### Requirement: Typed response models
The system SHALL define Pydantic models for all data provider responses:
- `PricePoint`: `date: str`, `open: float`, `high: float`, `low: float`, `close: float`, `volume: int`
- `PriceData`: `ticker: str`, `period: str`, `prices: list[PricePoint]`
- `FinancialStatements`: `ticker: str`, `income_statement: dict | None`, `balance_sheet: dict | None`, `cash_flow: dict | None`
- `KeyMetrics`: `ticker: str`, `pe_ratio: float | None`, `pb_ratio: float | None`, `market_cap: float | None`, `dividend_yield: float | None`, `roe: float | None`, `roa: float | None`, `debt_to_equity: float | None`

Additional result models:
- `TechnicalResult`: `rsi: float | None`, `ema_20: float | None`, `ema_50: float | None`, `ema_200: float | None`, `bb_upper: float | None`, `bb_middle: float | None`, `bb_lower: float | None`, `macd_line: float | None`, `macd_signal: float | None`, `macd_histogram: float | None`, `signals: dict[str, str]`, `overall_bias: str`, `warnings: list[str]`
- `FundamentalResult`: `profitability: dict[str, float | None]` (roe, roa, roic, net_margin, gross_margin), `valuation: dict[str, float | None]` (pe_ratio, pb_ratio, ev_ebitda, fcf_yield, dividend_yield), `stability: dict[str, float | None]` (debt_to_equity, current_ratio, interest_coverage), `sector_comparison: dict[str, str | None]` (pe_vs_sector, etc.), `warnings: list[str]`
- `RiskResult`: `volatility_30d: float | None`, `volatility_90d: float | None`, `volatility_252d: float | None`, `var_95: float | None`, `var_99: float | None`, `warnings: list[str]`
- `CorrelationResult`: `tickers: list[str]`, `matrix: dict[str, dict[str, float]]`, `warnings: list[str]`
- `AgentResult`: `signal: str` ("Bullish" | "Neutral" | "Bearish"), `score: float` (0-100), `confidence: float` (0.0-1.0), `rationale: str`, `breakdown: dict[str, float]`, `warnings: list[str]`
- `SearchResult`: `title: str`, `url: str`, `snippet: str`, `published_date: str | None`

All models SHALL support `.model_dump()` for JSON serialization (used by MCP tools).

#### Scenario: PriceData serialization
- **WHEN** a `PriceData` instance is serialized via `.model_dump()`
- **THEN** the output SHALL be a JSON-compatible dict usable directly as MCP tool response

### Requirement: Yahoo Finance provider
The system SHALL provide a `YahooFinanceProvider` that implements `DataProvider` using the `yfinance` library. It SHALL support US, EU tickers and partial KASE tickers. No API key SHALL be required.

#### Scenario: Fetch historical prices
- **WHEN** `get_prices("AAPL", "2024-01-01", "2024-12-31")` is called
- **THEN** the system SHALL return a `PriceData` with `PricePoint` entries containing date, open, high, low, close, volume

#### Scenario: Fetch financial statements
- **WHEN** `get_financials("AAPL")` is called
- **THEN** the system SHALL return a `FinancialStatements` with `income_statement`, `balance_sheet`, `cash_flow`

#### Scenario: Fetch key metrics
- **WHEN** `get_metrics("AAPL")` is called
- **THEN** the system SHALL return a `KeyMetrics` with `pe_ratio`, `pb_ratio`, `market_cap`, `dividend_yield`, `roe`, `roa`, `debt_to_equity`

#### Scenario: Invalid ticker
- **WHEN** `get_prices("INVALIDTICKER123", ...)` is called
- **THEN** the system SHALL raise `TickerNotFoundError` with the ticker name in the message

### Requirement: KASE scraper provider
The system SHALL provide a `KASEProvider` that implements `DataProvider` by scraping kase.kz public pages. No API key SHALL be required.

#### Scenario: Fetch KASE stock prices
- **WHEN** `get_prices("KCEL", "2024-01-01", "2024-12-31")` is called on KASEProvider
- **THEN** the system SHALL return a `PriceData` with price points from kase.kz data

#### Scenario: Fetch KASE financial statements
- **WHEN** `get_financials("KCEL")` is called on KASEProvider
- **THEN** the system SHALL return a `FinancialStatements` with available data; fields not publicly accessible SHALL be `None`

#### Scenario: Fetch KASE key metrics
- **WHEN** `get_metrics("KCEL")` is called on KASEProvider
- **THEN** the system SHALL return a `KeyMetrics` with fields computable from available public data (e.g. `market_cap` if available); fields not publicly accessible on kase.kz (e.g. `pe_ratio`, `roe`, `roa`) SHALL be `None`. If `FinancialStatements` data is available, the provider MAY compute derived metrics (e.g. `debt_to_equity` from balance sheet).

#### Scenario: KASE site unavailable
- **WHEN** kase.kz returns HTTP 5xx or connection timeout
- **THEN** the system SHALL raise `ProviderUnavailableError` with retry information

### Requirement: Rate limiting
Each data provider SHALL respect configurable rate limits defined in `fin-toolkit.yaml` (`rate_limit.requests_per_minute` + `rate_limit.max_concurrent`). Defaults: Yahoo=5 rpm / 2 concurrent, KASE=2 rpm / 1 concurrent, FMP=30 rpm / 5 concurrent. Rate limiting SHALL use a token bucket algorithm for requests_per_minute and `asyncio.Semaphore` for max_concurrent.

#### Scenario: Rate limit exceeded
- **WHEN** more than `requests_per_minute` calls are made within 60 seconds
- **THEN** the provider SHALL delay subsequent requests until tokens are refilled in the bucket

#### Scenario: Concurrent limit exceeded
- **WHEN** `max_concurrent` requests are already in-flight
- **THEN** additional requests SHALL await until a slot becomes available

### Requirement: Market-based provider routing
The system SHALL support market-based routing: tickers can be mapped to specific providers via `markets` config section. This takes precedence over the fallback chain.

#### Scenario: KZ ticker routed to KASE provider
- **WHEN** `get_stock_data("KCEL", ...)` is called and `markets.kz.tickers` includes "KCEL" with `provider: kase`
- **THEN** the system SHALL route directly to KASEProvider, bypassing the primary/fallback chain

#### Scenario: Explicit provider parameter overrides market mapping
- **WHEN** `get_stock_data("KCEL", provider="yahoo")` is called with explicit provider
- **THEN** the system SHALL use YahooFinanceProvider regardless of market mapping

#### Scenario: Unknown ticker uses fallback chain
- **WHEN** a ticker is not found in any market mapping
- **THEN** the system SHALL use the standard primary → fallback chain

### Requirement: Provider fallback chain
The system SHALL support a fallback chain: if the primary provider fails for a ticker (and no market mapping applies), the system SHALL try the fallback provider as configured in `fin-toolkit.yaml`.

#### Scenario: Primary provider fails, fallback succeeds
- **WHEN** primary provider raises `ProviderUnavailableError` for a ticker
- **AND** a fallback provider is configured
- **THEN** the system SHALL transparently retry with the fallback provider and return data

#### Scenario: All providers fail
- **WHEN** both primary and fallback providers fail for a ticker
- **THEN** the system SHALL raise `AllProvidersFailedError` listing each provider and its error

### Requirement: KeyMetrics as raw provider data
`KeyMetrics` SHALL represent raw summary metrics from the data provider (e.g. yfinance `.info`), NOT computed analysis. `KeyMetrics.pe_ratio` may differ from `FundamentalResult.valuation["pe_ratio"]` because providers may use trailing/forward PE while `FundamentalAnalyzer` computes trailing PE from financial statements. `KeyMetrics` is intended for quick lookup; `FundamentalResult` for detailed analysis with sector comparison.
