## ADDED Requirements

### Requirement: Historical volatility calculation
The system SHALL compute historical volatility for configurable windows (30, 90, 252 trading days). Input is `PriceData` (typed model from DataProvider), not raw DataFrame.

#### Scenario: Calculate 30-day volatility
- **WHEN** `calculate_volatility(price_data: PriceData, window=30)` is called with at least 30 price points
- **THEN** the system SHALL return annualized volatility as a decimal (e.g., 0.25 = 25%)

#### Scenario: Insufficient data for window
- **WHEN** `calculate_volatility(price_data, window=252)` is called with only 100 price points
- **THEN** the system SHALL raise `InsufficientDataError` specifying required vs available data points

### Requirement: Value at Risk (VaR) calculation
The system SHALL compute parametric VaR at configurable confidence levels (95%, 99%).

#### Scenario: Calculate 95% VaR
- **WHEN** `calculate_var(price_data: PriceData, confidence=0.95, horizon_days=1)` is called
- **THEN** the system SHALL return the maximum expected loss at 95% confidence over 1 day

### Requirement: Portfolio correlation matrix
The system SHALL compute pairwise correlation matrix from pre-fetched price data. The caller (MCP tool or higher-level orchestrator) is responsible for fetching `PriceData` per ticker via `DataProvider` — the risk module itself does NOT call DataProvider.

#### Scenario: Compute correlation for portfolio
- **WHEN** `correlation_matrix(prices: dict[str, PriceData])` is called with price data for 3+ tickers
- **THEN** the system SHALL return a `CorrelationResult` with pairwise Pearson correlations

### Requirement: Position sizing via Kelly Criterion
The system SHALL compute Kelly fraction for position sizing. This is a pure mathematical utility — the caller provides historical win rate and win/loss ratio (e.g., from backtesting or manual estimation).

#### Scenario: Calculate Kelly fraction
- **WHEN** `kelly_criterion(win_rate=0.6, win_loss_ratio=1.5)` is called
- **THEN** the system SHALL return the optimal fraction of capital to allocate (Kelly %)

#### Scenario: Negative expected value
- **WHEN** `kelly_criterion(win_rate=0.3, win_loss_ratio=0.8)` is called (negative EV)
- **THEN** the system SHALL return 0.0 (do not allocate) with a warning
