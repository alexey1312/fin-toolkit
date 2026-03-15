## ADDED Requirements

### Requirement: Fundamental ratios calculation
The system SHALL provide a `FundamentalAnalyzer` that computes financial ratios from typed provider data (`FinancialStatements`, `KeyMetrics`). Categories: profitability, valuation, stability.

#### Scenario: Calculate profitability ratios
- **WHEN** `analyze(financials: FinancialStatements, metrics: KeyMetrics)` is called with complete income statement and balance sheet
- **THEN** the result SHALL contain `roe`, `roa`, `roic`, `net_margin`, `gross_margin`

#### Scenario: Calculate valuation ratios
- **WHEN** `analyze(financials, metrics)` is called with earnings and market data
- **THEN** the result SHALL contain `pe_ratio`, `pb_ratio`, `ev_ebitda`, `fcf_yield`, `dividend_yield`

#### Scenario: Calculate stability ratios
- **WHEN** `analyze(financials, metrics)` is called with balance sheet data
- **THEN** the result SHALL contain `debt_to_equity`, `current_ratio`, `interest_coverage`

### Requirement: Missing data handling
The system SHALL handle partial financial data gracefully — compute available ratios and mark unavailable ones as `None`.

#### Scenario: Missing cash flow statement
- **WHEN** `FinancialStatements.cash_flow` is `None`
- **THEN** `fcf_yield` SHALL be `None` and other ratios SHALL still be computed

### Requirement: Sector comparison context
The system SHALL provide optional sector median context for ratios. Sector medians are hardcoded for 9 sectors (Technology, Finance, Healthcare, Energy, Consumer, Telecom, Materials, Industrials, Utilities) based on publicly available Damodaran datasets, stored in `references/sector_medians.json`. The 9 sectors cover major US and KASE tickers (KCEL → Telecom, KZTO → Industrials, Oil&Gas → Energy).

#### Scenario: Compare PE to sector with hardcoded medians
- **WHEN** `analyze(financials, metrics, sector="Technology")` is called
- **THEN** the result SHALL include `pe_vs_sector` comparing to hardcoded Technology sector median P/E

#### Scenario: Unknown sector
- **WHEN** `analyze(financials, metrics, sector="UnknownSector")` is called
- **THEN** `pe_vs_sector` SHALL be `None` with a warning that sector median is unavailable
