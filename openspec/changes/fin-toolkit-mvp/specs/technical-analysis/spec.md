## ADDED Requirements

### Requirement: Technical indicators calculation
The system SHALL provide a `TechnicalAnalyzer` that computes standard technical indicators using the `ta` library (Technical Analysis, https://github.com/bukosabino/ta). All calculations SHALL be deterministic (no LLM involvement). Input is `PriceData` (typed Pydantic model); internal conversion to pandas DataFrame is an implementation detail. The `ta` dependency SHALL be isolated behind `analysis/indicators.py` module to allow replacement without affecting consumers.

#### Scenario: Calculate RSI
- **WHEN** `analyze(price_data: PriceData)` is called with at least 14 data points
- **THEN** the result SHALL contain `rsi` with the 14-period RSI value for the latest date

#### Scenario: Calculate moving averages
- **WHEN** `analyze(price_data: PriceData)` is called with at least 200 data points
- **THEN** the result SHALL contain `ema_20`, `ema_50`, `ema_200` values

#### Scenario: Calculate Bollinger Bands
- **WHEN** `analyze(price_data: PriceData)` is called with at least 20 data points
- **THEN** the result SHALL contain `bb_upper`, `bb_middle`, `bb_lower` for 20-period bands with 2 standard deviations

#### Scenario: Calculate MACD
- **WHEN** `analyze(price_data: PriceData)` is called with at least 26 data points
- **THEN** the result SHALL contain `macd_line`, `macd_signal`, `macd_histogram`

### Requirement: Insufficient data handling
The system SHALL handle cases where price data is insufficient for indicator calculation.

#### Scenario: Not enough data for EMA-200
- **WHEN** `analyze(price_data: PriceData)` is called with only 50 data points
- **THEN** the result SHALL contain `ema_20` and `ema_50` but `ema_200` SHALL be `None` with a warning

### Requirement: Technical analysis output format
The system SHALL return technical analysis results as a `TechnicalResult` Pydantic model with fields: `rsi: float | None`, `ema_20: float | None`, `ema_50: float | None`, `ema_200: float | None`, `bb_upper: float | None`, `bb_middle: float | None`, `bb_lower: float | None`, `macd_line: float | None`, `macd_signal: float | None`, `macd_histogram: float | None`, `signals: dict[str, str]` (indicator → signal), `overall_bias: str` ("bullish" | "bearish" | "neutral"), `warnings: list[str]`.

#### Scenario: Generate signals summary
- **WHEN** RSI > 70 and price > BB upper
- **THEN** `signals` SHALL include `{"rsi": "overbought", "bollinger": "above_upper"}` with overall bias `"bearish"`
