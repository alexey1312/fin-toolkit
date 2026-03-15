## Context

Существующие AI hedge fund фреймворки (virattt/ai-hedge-fund, virattt/dexter) жёстко связаны с платными US-only API. fin-toolkit создаётся с нуля как модульный Python-пакет, где каждый слой (данные, поиск, анализ, агенты) работает через Protocol-интерфейсы, а Claude Code выступает оркестратором через MCP-сервер.

Текущее состояние: проект начинается с нуля. Elvis Marlamov agent реализован отдельно и будет перенесён. Warren Buffett agent будет адаптирован из ai-hedge-fund.

Целевые пользователи: разработчики и аналитики, использующие Claude Code / Codex для финансового анализа US и KZ рынков.

## Goals / Non-Goals

**Goals:**
- Protocol-first архитектура: любой провайдер заменяем без изменения потребителей
- Zero mandatory keys: полностью работоспособен без платных API
- MCP-сервер как единая точка входа для Claude Code
- KASE/AIX как first-class рынок наравне с US
- Конфигурация через единый YAML без кода
- TDD: тесты пишутся до имплементации, coverage >= 80%
- DX: `mise install` → `uv sync` → готов к работе; pitchfork auto-start MCP при cd в проект

**Non-Goals:**
- Real-time streaming котировок (batch-запросы достаточны)
- Автоматическое исполнение сделок (только анализ и рекомендации)
- Собственный UI/dashboard (Claude Code — единственный интерфейс)
- Поддержка криптовалютных бирж
- Мульти-агентный debate protocol (future roadmap)
- Portfolio backtesting (future roadmap)

## Decisions

### 1. mise + uv + pitchfork как toolchain

**Выбор**: mise (tool versions) + uv (package manager) + pitchfork (daemon manager)
**Альтернатива**: pyenv + pip/poetry, docker-compose
**Обоснование**: mise управляет версиями python/uv/ruff/pitchfork в едином `mise.toml` — один файл для всего tooling. uv на порядок быстрее pip/poetry для resolve/install. pitchfork автоматически стартует/останавливает MCP-сервер при `cd` в проект через shell hook — zero-setup DX для Claude Code.

### 2. Python Protocol вместо ABC для интерфейсов провайдеров

**Выбор**: `typing.Protocol` (структурная типизация)
**Альтернатива**: `abc.ABC` (номинальная типизация)
**Обоснование**: Protocol не требует наследования — любой класс с нужными методами автоматически совместим. Это упрощает создание третьесторонних провайдеров и тестовых заглушек. Статическая проверка через mypy без runtime overhead.

### 3. FastMCP как MCP-фреймворк

**Выбор**: FastMCP (Python)
**Альтернатива**: mcp SDK от Anthropic напрямую, TypeScript MCP SDK
**Обоснование**: FastMCP предоставляет декларативный API (`@mcp.tool()`), автоматическую генерацию JSON Schema из type hints, встроенную валидацию. Python-экосистема совместима с pandas/yfinance. Декларативность снижает boilerplate по сравнению с raw mcp SDK.

### 4. yfinance как primary data provider

**Выбор**: yfinance (Yahoo Finance unofficial API)
**Альтернатива**: FMP (платный), Alpha Vantage (ограниченный free tier), polygon.io
**Обоснование**: Бесплатный, без API-ключа, покрывает US/EU рынки и частично KASE. Риск: неофициальный API, возможны блокировки — митигируется fallback на FMP + rate limiting.

### 5. BeautifulSoup + httpx для KASE scraper

**Выбор**: httpx (async HTTP) + BeautifulSoup4 (парсинг)
**Альтернатива**: Selenium/Playwright (для JS-rendered страниц), Scrapy
**Обоснование**: kase.kz отдаёт статический HTML — headless browser избыточен. httpx поддерживает async для параллельных запросов. BS4 — стандарт для парсинга HTML в Python.

### 6. `ta` (Technical Analysis library) для технического анализа

**Выбор**: `ta` (https://github.com/bukosabino/ta)
**Альтернатива**: pandas-ta (заброшена, последний коммит 2023, 500+ open issues, проблемы с pandas 2.x), ta-lib (C-биндинги), ручные расчёты
**Обоснование**: Чистый Python, активно поддерживается, нативная интеграция с pandas DataFrame. Покрывает все нужные индикаторы (RSI, EMA, Bollinger, MACD). pandas-ta отвергнута как фактически заброшенная. ta-lib быстрее, но требует компиляции C-библиотек (сложна на macOS/Windows).

### 7. Pydantic для валидации и сериализации

**Выбор**: Pydantic v2
**Обоснование**: Валидация конфигов (fin-toolkit.yaml), сериализация ответов MCP tools, type-safe модели для финансовых данных. `.model_dump()` для JSON-сериализации без промежуточных шагов.

### 8. Структура пакета — плоский монорепо

**Выбор**: единый пакет `fin_toolkit` с подмодулями
**Альтернатива**: отдельные пакеты на провайдер
**Обоснование**: Один пакет проще в разработке, тестировании и установке.

### 9. YAML для конфигурации + XDG paths

**Выбор**: YAML конфиг + .env для секретов. Пути по XDG: глобальный `~/.config/fin-toolkit/config.yaml`, локальный override `./fin-toolkit.yaml` в директории проекта.
**Альтернатива**: TOML, JSON, Python-конфиг, `~/.fin-toolkit.yaml` в домашней директории
**Обоснование**: YAML — стандарт в ML/data-science экосистеме, читабелен, поддерживает комментарии. XDG Base Directory (`~/.config/`) — стандарт для Unix user config, не засоряет home. Секреты (API-ключи) читаются из .env через python-dotenv. Порядок поиска конфига: `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults.

### 10. Типизированные возвращаемые значения в Protocol

**Выбор**: Pydantic-модели (`PriceData`, `FinancialStatements`, `KeyMetrics`) как return types Protocol
**Альтернатива**: `pd.DataFrame` / `dict`
**Обоснование**: DataFrame — implementation detail, не контракт. Dict теряет типизацию. Pydantic-модели обеспечивают валидацию на границе провайдера, JSON-сериализацию для MCP tools без дополнительных преобразований, и документируют структуру данных. Провайдеры используют pandas внутренне, но конвертируют в Pydantic на выходе.

### 10a. KeyMetrics (raw) vs FundamentalResult (computed) — разграничение

**Выбор**: `KeyMetrics` — raw summary-метрики от провайдера (yfinance `.info`), `FundamentalResult` — вычисленный анализ от `FundamentalAnalyzer` с sector comparison.
**Обоснование**: `KeyMetrics.pe_ratio` может отличаться от computed P/E в `FundamentalResult.valuation["pe_ratio"]`, т.к. yfinance может использовать trailing/forward PE, а analyzer — trailing. `KeyMetrics` служит для quick lookup (MCP tool `get_stock_data`), `FundamentalResult` — для полного анализа (`run_fundamental_analysis`). Агенты используют `KeyMetrics` для быстрых проверок и `FundamentalAnalyzer` для детального скоринга.

### 11. Dependency Injection для агентов

**Выбор**: Constructor injection через dataclass-подобные агенты
**Альтернатива**: Global registry / service locator
**Обоснование**: Агенты получают `DataProvider` и анализаторы (`TechnicalAnalyzer`, `FundamentalAnalyzer`) через `__init__`. Делает зависимости явными, упрощает тестирование с моками. `AgentRegistry` отвечает за сборку агентов с правильными зависимостями при инициализации из конфига.

### 12a. Agents как mini-orchestrators (не pure functions)

**Выбор**: Агенты (`ElvisMarlamovAgent`, `WarrenBuffettAgent`) — мини-оркестраторы: `analyze(ticker)` внутри вызывает `data_provider.get_prices()`, `get_financials()`, `get_metrics()`, затем передаёт данные в инжектированные analyzers. Это async I/O операция, не pure function.
**Альтернатива**: `analyze(ticker, price_data, financials, metrics, news?)` — передавать готовые данные, делая агента pure function
**Обоснование**: Агенты — это высокоуровневые оркестраторы с бизнес-логикой (скоринг, пороги, graceful degradation при missing data). Они решают ЧТО запрашивать в зависимости от контекста (Elvis → нужен sentiment, Buffett → нет). Перенос fetching наружу усложнит MCP tool `run_agent` — ему пришлось бы знать зависимости каждого агента. Тестируемость обеспечивается mock DataProvider через constructor DI.

**Три уровня orchestration:**
1. **MCP tools** (`run_technical_analysis`, `run_risk_analysis`) — fetch + передача в pure analyzers
2. **Agents** (`run_agent`) — fetch + multi-analyzer orchestration + scoring logic
3. **Analyzers** (`TechnicalAnalyzer`, `FundamentalAnalyzer`, risk functions) — pure functions, только вычисления

### 12b. Market-based provider routing

**Выбор**: `ProviderRouter` поддерживает market-based routing помимо fallback chain. Конфиг `markets` определяет маппинг market → provider. Ticker resolution: (1) explicit `provider` parameter в MCP tool, (2) market mapping из конфига (`markets.kz.tickers: [KCEL, KZTO, ...]` → `provider: kase`), (3) fallback chain (primary → fallback).
**Альтернатива**: Только fallback chain
**Обоснование**: Yahoo Finance может вернуть частичные/некорректные данные для KASE тикеров (partial support) вместо ошибки. Fallback chain не спасёт — primary provider "успешно" вернёт мусор. Market mapping гарантирует что KZ тикеры идут сразу в KASE provider. Для неизвестных тикеров — стандартный fallback.

### 12. Async Protocol + asyncio.to_thread для синхронных провайдеров

**Выбор**: Все Protocol-интерфейсы (`DataProvider`, `SearchProvider`) определяются как **async** (`async def get_prices(...)`). Синхронные библиотеки (yfinance) оборачиваются через `asyncio.to_thread`.
**Альтернатива**: Sync Protocol, async только для HTTP-провайдеров
**Обоснование**: FastMCP — async-native фреймворк. httpx (KASE scraper) и Brave Search — async. Единый async Protocol позволяет rate limiting через `asyncio.Semaphore`, параллельный fetch нескольких тикеров через `asyncio.gather`, и естественную интеграцию с FastMCP tools. yfinance — единственный sync-провайдер, `asyncio.to_thread` добавляет 1 строку overhead. `@runtime_checkable` декоратор нужен для isinstance-проверок в ProviderRouter.

### 13. Rate limiting для внешних API

**Выбор**: Configurable per-provider rate limiting через token bucket алгоритм (async). `asyncio.Semaphore` ограничивает concurrency (макс. параллельных запросов), token bucket контролирует rate (запросов в минуту).
**Альтернатива**: Без rate limiting, global rate limiter, только Semaphore
**Обоснование**: yfinance throttling при частых запросах, kase.kz может блокировать по IP. Каждый провайдер имеет свой лимит в конфиге (`rate_limit.requests_per_minute` + `rate_limit.max_concurrent`). Default: yfinance=5 rpm / 2 concurrent, kase=2 rpm / 1 concurrent. Реализация: `TokenBucketRateLimiter` с `asyncio.Semaphore` для concurrency + token refill по таймеру для rate.

### 14. Sector medians — hardcoded Damodaran

**Выбор**: Hardcoded медианы для 9 секторов (Technology, Finance, Healthcare, Energy, Consumer, Telecom, Materials, Industrials, Utilities) из публичных Damodaran datasets
**Альтернатива**: Динамический расчёт из провайдера, отдельный API
**Обоснование**: Для P/E vs sector comparison нужен источник медиан. Damodaran datasets — общепризнанный академический источник, обновляемый ежегодно. Hardcoded значения хранятся в `references/sector_medians.json`, обновляются вручную. 9 секторов покрывают основные US и KASE тикеры (KCEL → Telecom, KZTO → Industrials, нефтегаз → Energy).

### 15. TDD подход

**Выбор**: Тесты пишутся первыми, реализация минимальна для прохождения
**Обоснование**: Финансовые расчёты требуют точности — TDD гарантирует корректность каждого индикатора, ratio, scoring блока. Mock-данные для провайдеров снимают зависимость от внешних API при тестировании.

### 16. MCP tools как orchestration layer

**Выбор**: MCP tool implementations отвечают за fetching данных через DataProvider и передачу чистым калькуляторам (analyzers, risk module). Analyzers — pure functions над typed data.
**Альтернатива**: Analyzers сами fetch'ат данные
**Обоснование**: Разделение ответственности — analyzers тестируются без сети (mock PriceData/FinancialStatements), MCP tools тестируются как integration layer. Пример: `run_risk_analysis(tickers, period)` → MCP tool fetch'ит PriceData per ticker → передаёт в `calculate_volatility(price_data)`, `correlation_matrix(prices)`. Risk module никогда не вызывает DataProvider напрямую.

### 17. Graceful degradation для search

**Выбор**: Если ни один SearchProvider не сконфигурирован (нет Brave ключа, нет SearXNG инстанса), `search_news` MCP tool возвращает пустой список + warning, а не ошибку.
**Альтернатива**: Raise ProviderConfigError
**Обоснование**: "Zero mandatory keys" означает, что каждый MCP tool должен работать или gracefully degrade. Search — enhancement, не core функциональность. Агенты с Sentiment блоком получают 0 баллов за sentiment — это корректное поведение, а не crash.

### 18. Distribution: PyPI + uvx + curl bootstrap

**Выбор**: Пакет публикуется на PyPI. Primary install path — `uvx fin-toolkit setup` (zero-install запуск из PyPI). Secondary — curl-скрипт из GitHub raw для bootstrap с нуля.
**Альтернатива**: Docker, brew, только git clone
**Обоснование**: `uvx` — стандарт для Python MCP-серверов, не требует глобальной установки, изолирует зависимости. В `.mcp.json` (локально) или `~/.claude.json` (глобально, `--global` flag) прописывается `{"command": "uvx", "args": ["fin-toolkit", "serve"]}` — Claude Code сам запускает сервер при каждом старте сессии. curl-скрипт решает проблему bootstrap (у пользователя нет uv): скрипт хостится на `https://raw.githubusercontent.com/alexey1312/fin-toolkit/main/install.sh`, ставит uv через `astral.sh/uv/install.sh`, затем `uv tool install fin-toolkit && fin-toolkit setup`.

### 19. CLI: setup / serve / status

**Выбор**: Три CLI-команды через entry point в `pyproject.toml`
**Обоснование**:
- `fin-toolkit setup` — создаёт локальный `.mcp.json` + глобальный `~/.config/fin-toolkit/config.yaml` с defaults. `--global` записывает MCP server entry в `~/.claude.json` (Claude Code global config) вместо локального `.mcp.json`. Идемпотентна — повторный вызов не перезаписывает существующий конфиг.
- `fin-toolkit serve` — запускает FastMCP-сервер на stdio. Ищет конфиг: `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults. Вызывается из `.mcp.json` или pitchfork.
- `fin-toolkit status` — показывает доступные провайдеры, конфигурацию, наличие API-ключей.

### 20. Sector auto-detection через yfinance

**Выбор**: MCP tool `run_fundamental_analysis` принимает optional `sector` параметр. Если не передан — пытается определить sector из `yfinance.Ticker.info["sector"]`.
**Альтернатива**: Всегда требовать sector явно
**Обоснование**: Для US тикеров yfinance даёт sector в 90% случаев. Для KASE — нет, тогда sector comparison = None. Это лучший UX: Claude Code может вызывать tool без sector, и для AAPL/MSFT получит полный результат.

## Risks / Trade-offs

**[yfinance нестабильность]** → Yahoo может изменить/заблокировать неофициальный API.
→ Митигация: fallback-провайдер (FMP), кэширование ответов, rate limiting (5 req/min default).

**[KASE scraper хрупкость]** → kase.kz может изменить HTML-структуру без предупреждения.
→ Митигация: версионированные парсеры, integration-тесты с snapshot-данными, алерт при изменении структуры.

**[`ta` library зависимость]** → Библиотека `ta` активно поддерживается, но является third-party обёрткой над pandas.
→ Митигация: обёртка через отдельный модуль `analysis/indicators.py` изолирует зависимость. При необходимости замены на ручные расчёты (~50 строк на индикатор) — меняется только один файл.

**[FastMCP breaking changes]** → FastMCP активно развивается, API может меняться.
→ Митигация: pin версии, абстрагировать tool-регистрацию.

**[Скоринговая система субъективна]** → Пороги Elvis Marlamov agent (75/50 баллов) выбраны экспертно.
→ Trade-off: принимаем субъективность, документируем методологию, делаем пороги конфигурируемыми.

**[SearXNG требует инфраструктуру]** → SearXNG не требует API-ключа, но требует self-hosted инстанс. Для пользователя без инфраструктуры — search недоступен без Brave ключа.
→ Митигация: graceful degradation (Decision #17) — search_news возвращает пустой список + warning. В README документировать: для search нужен либо Brave API key, либо SearXNG инстанс.

**[Отсутствие real-time данных]** → Batch-запросы дают задержку 15-20 минут (Yahoo Finance).
→ Trade-off: приемлемо для фундаментального анализа, не подходит для HFT/скальпинга.

**[KASE авторизация]** → Публичных страниц kase.kz достаточно для базовых котировок. Полная отчётность может требовать авторизации.
→ Митигация: graceful degradation — парсим что доступно публично, `get_financials()` возвращает `None` для недоступных полей.

## Architecture: Orchestrator + Subagents + Worktrees

Имплементация через паттерн **orchestrator + subagents** с **git worktree isolation**.

### Принцип

- **Subagent валидирует себя** — green build в своём worktree (pytest + mypy + ruff)
- **Orchestrator валидирует интеграцию** — sequential merge-back с full test suite после каждого merge

### Execution Model

```
Orchestrator (Opus) — работает на main
│
│ ──── Sequential Phase: Base ──────────────────────────────
│
├── [main] Subagent A: Scaffolding → Models → Config
│   Коммит на main напрямую, каждый шаг = green build.
│   Это "base" для всех worktrees.
│
│ ──── Parallel Block 1: Worktrees from main ───────────────
│
├── [worktree] Subagent B: feat/data-providers
│   ├── git worktree add ../fin-toolkit-data-providers feat/data-providers
│   ├── TDD: тесты → impl → green build в worktree
│   └── commit в ветку feat/data-providers
│
├── [worktree] Subagent C: feat/technical-analysis       ║ параллельно
├── [worktree] Subagent D: feat/fundamental-analysis     ║ с B
├── [worktree] Subagent E: feat/risk-analysis            ║
│
│ ──── Merge Gate 1: Orchestrator ──────────────────────────
│
├── Orchestrator merge-back (sequential):
│   1. merge feat/data-providers → main     → full pytest → green? ✓
│   2. merge feat/technical-analysis → main → full pytest → green? ✓
│   3. merge feat/fundamental-analysis → main → full pytest → ✓
│   4. merge feat/risk-analysis → main      → full pytest → ✓
│   Если конфликт или red build → orchestrator фиксит до перехода далее.
│
│ ──── Parallel Block 2: Worktrees from updated main ───────
│
├── [worktree] Subagent F: feat/search-providers         ║ параллельно
├── [worktree] Subagent G: feat/agent-system             ║
├── [worktree] Subagent I: feat/skills (markdown only)   ║
│
│ ──── Merge Gate 2 ────────────────────────────────────────
│
├── Orchestrator merge-back (sequential):
│   1. merge feat/search-providers → main → full pytest → ✓
│   2. merge feat/agent-system → main     → full pytest → ✓
│   3. merge feat/skills → main           → full pytest → ✓
│
│ ──── Sequential: MCP Server (интегрирует всё) ────────────
│
├── [main] Subagent H: MCP Server (tools only)
│   Работает на main (нужны все модули), коммит напрямую
│
│ ──── Parallel Block 3: CLI + Integration ─────────────────
│
├── [worktree] Subagent K: feat/cli (setup/serve/status + install.sh)  ║ параллельно
├── [worktree] Subagent J: feat/integration-docs                       ║
│
│ ──── Merge Gate 3 + Final Validation ─────────────────────
│
└── Orchestrator:
    1. merge feat/cli → main → full pytest → ✓
    2. merge feat/integration-docs → main → full pytest → ✓
    3. Final: pytest --cov-fail-under=80, mypy, ruff, E2E test (mock providers)
```

### Валидация на каждом уровне

| Уровень | Кто | Что проверяет | Когда |
|---------|-----|---------------|-------|
| **Subagent** | Каждый subagent в worktree | `pytest` (свои тесты), `mypy`, `ruff` | Перед коммитом в ветку |
| **Merge Gate** | Orchestrator на main | `pytest` (ВСЕ тесты), `mypy`, `ruff` | После каждого merge в main |
| **Final Gate** | Orchestrator | `pytest --cov-fail-under=80`, E2E, полный lint | После последнего merge |

### Worktree Lifecycle

1. Orchestrator создаёт worktree: `git worktree add ../fin-toolkit-{name} feat/{name}`
2. Subagent работает в worktree, коммитит в feature branch
3. Orchestrator делает `git merge feat/{name}` на main
4. При успехе: `git worktree remove ../fin-toolkit-{name}`, delete branch
5. При конфликте: orchestrator резолвит на main, перезапускает тесты

### Что делать при red merge

1. Orchestrator запускает `pytest -x --tb=short` для быстрого обнаружения
2. Анализирует: конфликт имён? Несовместимость интерфейсов? Import error?
3. Фиксит минимально на main (не трогая worktree — она уже merged)
4. Коммит: `fix: resolve merge conflict between {branch-a} and {branch-b}`
5. Продолжает merge следующей ветки
