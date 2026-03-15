## Execution Policy

- **TDD**: Для каждого модуля — сначала тесты, потом имплементация. Red → Green → Refactor.
- **Worktrees**: Параллельные subagents работают в изолированных `git worktree`. Каждый worktree = отдельная feature branch.
- **Валидация (subagent)**: Перед коммитом в ветку — `uv run pytest && uv run mypy fin_toolkit/ && uv run ruff check`.
- **Валидация (orchestrator)**: После merge каждой ветки в main — `uv run pytest` (ПОЛНЫЙ suite). Red merge → orchestrator фиксит до перехода дальше.
- **Commits**: Каждый коммит ДОЛЖЕН быть green. Conventional commits: `feat:`, `test:`, `fix:`.

---

## 1. Project Scaffolding & Tooling [main, sequential]

> **Subagent A** — работает на main напрямую, все остальные ждут.
> **Commit**: `feat: scaffold fin-toolkit with mise + uv + pitchfork`

- [ ] 1.1 Создать `mise.toml`:
  ```toml
  [tools]
  python = "3.11"
  uv = "latest"
  ruff = "latest"
  pitchfork = "latest"

  [settings]
  python.uv_venv_auto = "create|source"
  ```
- [ ] 1.2 Инициализировать uv-проект: `uv init` (в текущей директории) → `pyproject.toml`
- [ ] 1.3 Добавить зависимости в `pyproject.toml`:
  - runtime: yfinance, pandas, ta, fastmcp, pydantic, httpx, beautifulsoup4, python-dotenv, pyyaml
  - dev: pytest, pytest-cov, pytest-asyncio, mypy, ruff
- [ ] 1.4 Создать структуру пакета:
  ```
  fin_toolkit/
  ├── __init__.py
  ├── models/          # Pydantic models (PriceData, etc.)
  ├── providers/       # DataProvider, SearchProvider
  ├── analysis/        # Technical, Fundamental, Risk
  ├── agents/          # Elvis, Buffett, Registry
  ├── mcp_server/      # FastMCP server + tools
  ├── config/          # YAML loader, Pydantic config models
  └── references/      # sector_medians.json
  tests/
  ├── conftest.py      # shared fixtures, mock data
  ├── test_models/
  ├── test_providers/
  ├── test_analysis/
  ├── test_agents/
  ├── test_mcp/
  └── test_config/
  skills/
  ├── dcf-valuation/
  ├── technical-screen/
  ├── earnings-analysis/
  ├── portfolio-review/
  └── kase-analysis/
  ```
- [ ] 1.5 Создать `pitchfork.toml`:
  ```toml
  [daemons.fin-toolkit-mcp]
  run = "uv run fin-toolkit serve"
  auto = ["start", "stop"]
  ready_output = "MCP server started"
  ```
- [ ] 1.6 Создать базовый `fin-toolkit.yaml` с default-конфигурацией
- [ ] 1.7 Настроить pytest (`pyproject.toml`): `testpaths`, `asyncio_mode = "auto"`, coverage config
- [ ] 1.8 Настроить ruff + mypy в `pyproject.toml`
- [ ] 1.9 Создать `tests/conftest.py` с shared mock fixtures (mock price data, mock financials)
- [ ] 1.10 **Validate**: `uv sync && uv run pytest` green (пустой тест)

---

## 2. Typed Models & Exceptions [main, sequential]

> **Subagent A** (продолжение) — базовые типы нужны всем worktrees.
> **Commit**: `feat: add typed Pydantic models and custom exceptions`

- [ ] 2.1 **Тесты**: `tests/test_models/test_price_data.py` — PricePoint, PriceData creation, .model_dump(), validation
- [ ] 2.2 **Тесты**: `tests/test_models/test_financial_models.py` — FinancialStatements, KeyMetrics, None fields
- [ ] 2.3 **Тесты**: `tests/test_models/test_results.py` — TechnicalResult (все indicator fields + signals + overall_bias + warnings), FundamentalResult (profitability/valuation/stability dicts + sector_comparison + warnings), RiskResult (volatility_30d/90d/252d + var_95/99 + warnings), AgentResult (signal/score/confidence/rationale/breakdown/warnings), CorrelationResult (tickers + matrix + warnings), SearchResult (title/url/snippet/published_date)
- [ ] 2.4 **Impl**: `fin_toolkit/models/` — все Pydantic-модели с полными field definitions
- [ ] 2.5 **Impl**: `fin_toolkit/exceptions.py` — TickerNotFoundError, ProviderUnavailableError, AllProvidersFailedError, ProviderConfigError, InsufficientDataError, AgentNotFoundError, ConfigError
- [ ] 2.6 **Validate**: `uv run pytest` green, `uv run mypy` clean

---

## 3. Config System [main, sequential]

> **Subagent A** (продолжение) — конфиг нужен провайдерам во всех worktrees.
> **Commit**: `feat: add YAML config system with Pydantic validation`

- [ ] 3.1 **Тесты**: `tests/test_config/test_config.py` — валидный конфиг, невалидный, missing file, env override, rate limit defaults, auto-detection, **market mapping**, **config priority: env > .env > yaml > defaults**
- [ ] 3.2 **Impl**: Pydantic config models: `DataConfig`, `SearchConfig`, `AgentsConfig`, `RateLimitConfig`, `MarketsConfig`, `ToolkitConfig`. `MarketsConfig` включает market-to-provider mapping (e.g. `markets.kz.tickers: [KCEL, KZTO, ...], markets.kz.provider: kase`)
- [ ] 3.3 **Impl**: загрузка `fin-toolkit.yaml` + `.env` + fallback на defaults
- [ ] 3.4 **Impl**: auto-detection доступных провайдеров на основе ключей
- [ ] 3.5 **Validate**: green build
- [ ] 3.6 **Orchestrator**: Это "base commit" — все worktrees создаются от этой точки

---

## 4–7: Parallel Block 1 ║ [worktrees от main после task 3]

> Orchestrator создаёт 4 worktrees параллельно.
> Каждый subagent: TDD в своём worktree → commit в feature branch.
> После завершения всех — orchestrator мержит sequential с full test suite.

### 4. Data Providers ║ [worktree: feat/data-providers]

> **Subagent B** — `git worktree add ../ft-data-providers feat/data-providers`
> **Commit в ветку**: `feat: add DataProvider protocol, Yahoo and KASE providers`

#### 4a. DataProvider Protocol (async) + Rate Limiter
- [ ] 4.1 **Тесты**: `tests/test_providers/test_protocol.py` — mock async-класс с правильными методами удовлетворяет `@runtime_checkable` Protocol, isinstance check
- [ ] 4.2 **Тесты**: `tests/test_providers/test_rate_limiter.py` — token bucket: requests_per_minute enforced (burst followed by throttle), max_concurrent via Semaphore, token refill over time
- [ ] 4.3 **Impl**: `DataProvider` async Protocol definition с `@runtime_checkable`
- [ ] 4.4 **Impl**: `TokenBucketRateLimiter` — async rate limiter (token bucket для requests_per_minute + asyncio.Semaphore для max_concurrent)

#### 4b. Yahoo Finance Provider
- [ ] 4.5 **Тесты**: `tests/test_providers/test_yahoo.py` — get_prices (mock yfinance), get_financials, get_metrics, invalid ticker → TickerNotFoundError
- [ ] 4.6 **Impl**: `YahooFinanceProvider` — async методы через `asyncio.to_thread` для синхронного yfinance, конвертация DataFrame → Pydantic models

#### 4c. KASE Scraper Provider
- [ ] 4.7 **Тесты**: `tests/test_providers/test_kase.py` — snapshot HTML fixtures, get_prices, get_financials (None для недоступных), HTTP error handling
- [ ] 4.8 **Impl**: `KASEProvider` — httpx + BS4, парсинг kase.kz, graceful degradation

#### 4d. Provider Router
- [ ] 4.9 **Тесты**: `tests/test_providers/test_router.py` — primary succeeds, primary fails → fallback, all fail → AllProvidersFailedError, **market mapping: KZ ticker → KASE provider**, explicit provider parameter override, unknown ticker → fallback chain
- [ ] 4.10 **Impl**: `ProviderRouter` с market-based routing + fallback chain. Routing order: (1) explicit `provider` param, (2) market mapping из конфига (`markets.kz.tickers`), (3) primary → fallback chain
- [ ] 4.11 **Validate в worktree**: `uv run pytest tests/test_providers/ tests/test_models/ tests/test_config/ && uv run mypy && uv run ruff check`

### 5. Technical Analysis ║ [worktree: feat/technical-analysis]

> **Subagent C** — `git worktree add ../ft-technical feat/technical-analysis`
> **Commit в ветку**: `feat: add technical analysis module with ta library`

- [ ] 5.1 **Тесты**: `tests/test_analysis/test_technical.py` — RSI (synthetic PriceData, known value), EMA 20/50/200, Bollinger Bands, MACD, insufficient data → None + warning, signals generation, overall_bias
- [ ] 5.2 **Impl**: `TechnicalAnalyzer.analyze(price_data: PriceData) -> TechnicalResult` (внутренняя конвертация PriceData → DataFrame для `ta` library). Обёртка через `analysis/indicators.py` изолирует зависимость от `ta`
- [ ] 5.3 **Impl**: signal generation logic (overbought/oversold, trend direction, overall bias)
- [ ] 5.4 **Validate в worktree**: `uv run pytest tests/test_analysis/test_technical.py tests/test_models/ && uv run mypy && uv run ruff check`

### 6. Fundamental Analysis ║ [worktree: feat/fundamental-analysis]

> **Subagent D** — `git worktree add ../ft-fundamental feat/fundamental-analysis`
> **Commit в ветку**: `feat: add fundamental analysis with sector medians`

- [ ] 6.1 **Тесты**: `tests/test_analysis/test_fundamental.py` — profitability ratios, valuation ratios, stability ratios, missing data → None, sector comparison (known median vs value), unknown sector → None
- [ ] 6.2 **Impl**: `FundamentalAnalyzer.analyze(financials, metrics, sector?) -> FundamentalResult`
- [ ] 6.3 **Impl**: `fin_toolkit/references/sector_medians.json` — hardcoded Damodaran medians для 9 секторов (Technology, Finance, Healthcare, Energy, Consumer, Telecom, Materials, Industrials, Utilities)
- [ ] 6.4 **Validate в worktree**: `uv run pytest tests/test_analysis/test_fundamental.py tests/test_models/ && uv run mypy && uv run ruff check`

### 7. Risk Analysis ║ [worktree: feat/risk-analysis]

> **Subagent E** — `git worktree add ../ft-risk feat/risk-analysis`
> **Commit в ветку**: `feat: add risk analysis module`

- [ ] 7.1 **Тесты**: `tests/test_analysis/test_risk.py` — volatility (synthetic, known value), VaR, correlation matrix (3 tickers), Kelly Criterion, edge cases (insufficient data, negative Kelly → 0.0)
- [ ] 7.2 **Impl**: `calculate_volatility(price_data, window)`, `calculate_var(price_data, confidence, horizon_days)`
- [ ] 7.3 **Impl**: `correlation_matrix(prices: dict[str, PriceData]) -> CorrelationResult`
- [ ] 7.4 **Impl**: `kelly_criterion(win_rate, win_loss_ratio) -> float`
- [ ] 7.5 **Validate в worktree**: `uv run pytest tests/test_analysis/test_risk.py tests/test_models/ && uv run mypy && uv run ruff check`

### ── Merge Gate 1 [orchestrator на main] ──

> Orchestrator мержит ветки sequential, запускает FULL test suite после каждого merge.

- [ ] MG1.1 `git merge feat/data-providers` → `uv run pytest` (ALL) → green? ✓
- [ ] MG1.2 `git merge feat/technical-analysis` → `uv run pytest` (ALL) → green? ✓
- [ ] MG1.3 `git merge feat/fundamental-analysis` → `uv run pytest` (ALL) → green? ✓
- [ ] MG1.4 `git merge feat/risk-analysis` → `uv run pytest` (ALL) → green? ✓
- [ ] MG1.5 Cleanup worktrees: `git worktree remove`, delete branches
- [ ] MG1.6 **Commit если нужен fix**: `fix: resolve integration issues from parallel merge`

---

## 8–9–11: Parallel Block 2 ║ [worktrees от main после MG1]

### 8. Search Providers ║ [worktree: feat/search-providers]

> **Subagent F** — `git worktree add ../ft-search feat/search-providers`
> **Commit в ветку**: `feat: add SearchProvider protocol, Brave and SearXNG`

- [ ] 8.1 **Тесты**: `tests/test_providers/test_search.py` — SearchProvider Protocol compliance, Brave search (mock API), SearXNG (mock HTTP), missing key → ProviderConfigError, fallback chain
- [ ] 8.2 **Impl**: `SearchProvider` Protocol + `SearchResult` model (если не в models/)
- [ ] 8.3 **Impl**: `BraveSearchProvider`, `SearXNGProvider`
- [ ] 8.4 **Impl**: `SearchRouter` с fallback
- [ ] 8.5 **Validate в worktree**: `uv run pytest tests/test_providers/ && uv run mypy && uv run ruff check`

### 9. Agent System ║ [worktree: feat/agent-system]

> **Subagent G** — `git worktree add ../ft-agents feat/agent-system`
> **Commit в ветку**: `feat: add agent system with Elvis Marlamov and Warren Buffett`

- [ ] 9.1 **Тесты**: `tests/test_agents/test_protocol.py` — AnalysisAgent Protocol compliance
- [ ] 9.2 **Тесты**: `tests/test_agents/test_elvis.py` — scoring blocks (Quality 40, Stability 20, Valuation 30, Sentiment 10), strong stock → Bullish (>=75), weak → Bearish (<50), mock DI, **без SearchProvider → Sentiment=0 + warning**, missing metrics → confidence снижен + warning
- [ ] 9.3 **Тесты**: `tests/test_agents/test_buffett.py` — value investing criteria, AgentResult format, mock DI, missing data graceful degradation
- [ ] 9.4 **Тесты**: `tests/test_agents/test_registry.py` — load from config, get_active_agents, unknown agent → AgentNotFoundError
- [ ] 9.5 **Impl**: `AnalysisAgent` Protocol
- [ ] 9.6 **Impl**: `ElvisMarlamovAgent` с constructor DI (DataProvider + analyzers + optional SearchProvider). Sentiment block = 0 если search не инжектирован.
- [ ] 9.7 **Impl**: `WarrenBuffettAgent` с constructor DI (адаптация из ai-hedge-fund)
- [ ] 9.8 **Impl**: `AgentRegistry` — сборка агентов с зависимостями из конфига (включая optional SearchProvider)
- [ ] 9.9 **Validate в worktree**: `uv run pytest tests/test_agents/ && uv run mypy && uv run ruff check`

### 11. Skills ║ [worktree: feat/skills]

> **Subagent I** — `git worktree add ../ft-skills feat/skills`
> Skills — markdown файлы, не зависят от кода, только ссылаются на MCP tool names. Можно писать параллельно с Block 2.
> **Commit в ветку**: `feat: add Claude Code skills for financial analysis workflows`

- [ ] 11.1 **Impl**: `skills/dcf-valuation/SKILL.md` — YAML frontmatter + DCF workflow (get_stock_data → run_fundamental_analysis → user assumptions → compute intrinsic value)
- [ ] 11.2 **Impl**: `skills/dcf-valuation/references/dcf-guide.md` — detailed DCF methodology
- [ ] 11.3 **Impl**: `skills/technical-screen/SKILL.md` — technical screening workflow
- [ ] 11.4 **Impl**: `skills/earnings-analysis/SKILL.md` — earnings quality workflow
- [ ] 11.5 **Impl**: `skills/portfolio-review/SKILL.md` — multi-stock + risk analysis workflow
- [ ] 11.6 **Impl**: `skills/kase-analysis/SKILL.md` — Kazakhstan market workflow
- [ ] 11.7 Каждый skill: error handling секция (MCP connection, missing keys, pitchfork)
- [ ] 11.8 **Validate в worktree**: verify YAML frontmatter syntax

### ── Merge Gate 2 [orchestrator на main] ──

- [ ] MG2.1 `git merge feat/search-providers` → `uv run pytest` (ALL) → green? ✓
- [ ] MG2.2 `git merge feat/agent-system` → `uv run pytest` (ALL) → green? ✓
- [ ] MG2.3 `git merge feat/skills` → `uv run pytest` (ALL) → green? ✓
- [ ] MG2.4 Cleanup worktrees
- [ ] MG2.5 **Commit если нужен fix**: `fix: resolve integration issues from parallel merge`

---

## 10. MCP Server [main, sequential]

> **Subagent H** — работает на main (нужны все модули).
> **Commit**: `feat: add FastMCP server with 6 tools`

- [ ] 10.1 **Тесты**: `tests/test_mcp/test_tools.py` — каждый tool: valid input → JSON, invalid ticker → is_error, rate limit → transparent retry
- [ ] 10.2 **Impl**: FastMCP server (`server.py`) с @mcp.tool() декораторами
- [ ] 10.3 **Impl**: `get_stock_data(ticker, period, provider?)` → JSON PriceData
- [ ] 10.4 **Impl**: `run_technical_analysis(ticker)` → JSON TechnicalResult
- [ ] 10.5 **Impl**: `run_fundamental_analysis(ticker, sector?)` → JSON FundamentalResult. Auto-detect sector через yfinance.Ticker.info["sector"] если не передан
- [ ] 10.6 **Impl**: `run_risk_analysis(tickers, period)` → JSON RiskResult. MCP tool = orchestration layer: fetch PriceData per ticker → pass to risk pure functions
- [ ] 10.7 **Impl**: `search_news(query, max_results)` → JSON SearchResult[]. Graceful degradation: если нет SearchProvider → return `[]` + warning
- [ ] 10.8 **Impl**: `run_agent(ticker, agent)` → JSON AgentResult. Agent = mini-orchestrator (сам fetch'ит данные через injected DataProvider)
- [ ] 10.9 **Impl**: unified error handler (is_error + descriptive message)
- [ ] 10.10 **Impl**: `fin-toolkit serve` — запуск FastMCP на stdio, загрузка конфига (или defaults). Минимальный CLI entry point в `pyproject.toml` (`[project.scripts]`): `fin-toolkit = "fin_toolkit.cli:main"`
- [ ] 10.11 **Validate**: `uv run pytest` (ALL) green

---

## 12–13: Parallel Block 3 ║ [worktrees от main после task 10]

### 13. CLI ║ [worktree: feat/cli]

> **Subagent K** — `git worktree add ../ft-cli feat/cli`
> **Commit в ветку**: `feat: add CLI setup, status commands and install script`

- [ ] 13.1 **Тесты**: `tests/test_cli/test_setup.py` — setup создаёт `.mcp.json` + `~/.config/fin-toolkit/config.yaml`, идемпотентность (повторный вызов не перезаписывает), `--global` пишет в `~/.claude.json`, сохранение existing servers, локальный `./fin-toolkit.yaml` override
- [ ] 13.2 **Impl**: `fin-toolkit setup [--global]` — создаёт локальный `.mcp.json` (или `--global` → `~/.claude.json`) с `{"command": "uvx", "args": ["fin-toolkit", "serve"]}` + `~/.config/fin-toolkit/config.yaml` defaults. Идемпотентна.
- [ ] 13.3 **Impl**: `fin-toolkit status` — показывает конфиг, доступные провайдеры (✓/✗), активных агентов, наличие `.mcp.json`
- [ ] 13.4 **Impl**: `install.sh` в корне репо — bootstrap скрипт: проверка/установка uv, `uv tool install fin-toolkit`, `fin-toolkit setup`
- [ ] 13.5 **Validate в worktree**: `uv run pytest tests/test_cli/ && uv run mypy && uv run ruff check`

### 12. Integration & Documentation ║ [worktree: feat/integration-docs]

> **Subagent J** — `git worktree add ../ft-integration feat/integration-docs`
> **Commit в ветку**: `feat: add CLAUDE.md, .mcp.json, README, integration tests`

- [ ] 12.1 **Тесты**: `tests/test_integration/test_e2e.py` — полный pipeline: config → mock provider → analysis → MCP tool response. Использовать mock/recorded fixtures (VCR pattern), НЕ live API. Live API тесты — отдельный marker `pytest -m live`
- [ ] 12.2 **Impl**: `CLAUDE.md` с master instructions для Claude Code
- [ ] 12.3 **Impl**: `.mcp.json` пример конфигурации (для тех кто настраивает вручную)
- [ ] 12.4 **Impl**: README — quick start: `uvx fin-toolkit setup` (primary) + `curl | sh` (bootstrap), архитектура, примеры
- [ ] 12.5 **Validate в worktree**: `uv run pytest tests/test_integration/ && uv run mypy && uv run ruff check`

### ── Merge Gate 3 + Final Validation [orchestrator на main] ──

- [ ] MG3.1 `git merge feat/cli` → `uv run pytest` (ALL) → green? ✓
- [ ] MG3.2 `git merge feat/integration-docs` → `uv run pytest` (ALL) → green? ✓
- [ ] MG3.3 Cleanup worktrees
- [ ] MG3.4 **Final Gate**:
  - `uv run pytest --cov=fin_toolkit --cov-fail-under=80`
  - `uv run mypy fin_toolkit/`
  - `uv run ruff check fin_toolkit/`
- [ ] MG3.5 **E2E (mock)**: `uv run pytest tests/test_integration/ -v` — полный pipeline на mock providers
- [ ] MG3.6 **E2E (live, optional)**: `uv run pytest -m live` — ручной smoke test AAPL, SBER, KCEL (не блокирует merge)

---

## Dependency Graph + Worktree Map

```
[main] 1 (Scaffolding) → 2 (Models) → 3 (Config)  ← base for all worktrees
                                          │
                    ┌─────────┬────────────┼────────────┐
                    ▼         ▼            ▼            ▼
              [worktree]  [worktree]  [worktree]  [worktree]
              4 Data      5 Tech      6 Fund      7 Risk        ║ Parallel Block 1
              Providers   Analysis    Analysis    Analysis
                    │         │            │            │
                    └─────────┴────────────┴────────────┘
                                          │
                              ── Merge Gate 1 ──
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              [worktree]           [worktree]            [worktree]
              8 Search             9 Agents              11 Skills   ║ Parallel Block 2
                    │                     │                     │
                    └─────────────────────┴─────────────────────┘
                                          │
                              ── Merge Gate 2 ──
                                          │
                              [main] 10 MCP Server (tools + serve)
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                                           ▼
              [worktree]                                  [worktree]
              13 CLI                                      12 Integration   ║ Parallel Block 3
              (setup/status/install.sh)                   (docs + E2E)
                    │                                           │
                    └─────────────────────┴─────────────────────┘
                                          │
                              ── Merge Gate 3 ──
                                          │
                                    Final ✓
```

## Validation Matrix

| Уровень | Кто выполняет | Что проверяет | Scope | Когда |
|---------|---------------|---------------|-------|-------|
| **Worktree** | Subagent | pytest (свои тесты + models + config), mypy, ruff | Свой модуль + shared deps | Перед commit в feature branch |
| **Merge Gate** | Orchestrator | pytest (ALL тесты), mypy, ruff | Весь проект | После каждого merge в main |
| **Final Gate** | Orchestrator | pytest --cov-fail-under=80, mypy, ruff, E2E (mock) | Весь проект + coverage | После всех merges |
| **Live E2E** | Orchestrator (optional) | pytest -m live | AAPL, SBER, KCEL через real API | Ручной smoke test, не блокирует |

## Red Merge Protocol

Если после merge `uv run pytest` падает:

1. `uv run pytest -x --tb=short` — найти первый упавший тест
2. Определить причину: import conflict? name clash? interface mismatch?
3. Fix минимально на main (не трогая уже merged код без необходимости)
4. `fix: resolve merge conflict between {branch-a} and {branch-b}`
5. `uv run pytest` (ALL) → green → продолжить merge следующей ветки
