## Why

Существующие AI-фреймворки для финансового анализа (ai-hedge-fund, Dexter) жёстко привязаны к платным US-ориентированным API (Financial Datasets, Exa). Невозможно заменить источник данных без переписывания кода, нет поддержки локальных рынков (KASE/AIX, Казахстан), а входной порог — набор платных ключей.

Нужен **protocol-first фреймворк**, где провайдеры данных и поиска взаимозаменяемы через единый интерфейс, всё работает без единого платного API-ключа, а Claude Code/Codex выступает оркестратором через MCP-сервер.

## What Changes

- Создание нового Python-пакета `fin-toolkit` с модульной архитектурой провайдеров
- **Tooling**: mise (версии python/uv/ruff/pitchfork), uv (пакетный менеджер), pitchfork (daemon manager для MCP-сервера)
- **Data Layer**: Async `DataProvider` Protocol (`@runtime_checkable`) + Yahoo Finance (бесплатный, через `asyncio.to_thread`) + KASE scraper (kase.kz, httpx async) + ProviderRouter с fallback + market-based routing + rate limiting (token bucket per-provider)
- **Search Layer**: `SearchProvider` Protocol + Brave Search + SearXNG (self-hosted) + SearchRouter с fallback
- **Analysis Engine**: технический анализ (RSI, EMA, Bollinger, MACD), фундаментальный анализ (P/E, P/B, ROE, DCF inputs), оценка рисков (VaR, Kelly Criterion, корреляции)
- **Agent System**: Elvis Marlamov agent (100 баллов, RU/KZ рынок) + Warren Buffett agent (value investing) с constructor DI (DataProvider + Analyzers + optional SearchProvider для sentiment)
- **CLI & Distribution**: `fin-toolkit setup` — one-click установка MCP-сервера в Claude Code (создаёт `.mcp.json` + `fin-toolkit.yaml`). Два пути установки: `uvx fin-toolkit setup` (primary, PyPI) и `curl -fsSL https://raw.githubusercontent.com/alexey1312/fin-toolkit/main/install.sh | sh` (bootstrap с нуля, ставит uv если нет). Пакет публикуется на PyPI.
- **MCP Server**: FastMCP-сервер (async) с tools: `get_stock_data`, `run_technical_analysis`, `run_fundamental_analysis(ticker, sector?)` с sector auto-detect, `run_risk_analysis` (orchestration layer — fetch + compute), `search_news` (graceful degradation если нет SearchProvider), `run_agent`. Авто-старт через pitchfork
- **Skills**: SKILL.md-инструкции для Claude Code (dcf-valuation, technical-screen, earnings-analysis, portfolio-review, kase-analysis)
- **Конфигурация** через `fin-toolkit.yaml` — все API-ключи опциональны
- **TDD**: тесты пишутся до имплементации, pytest + mock-данные, coverage >= 80%

## Capabilities

### New Capabilities
- `cli-setup`: CLI для установки и настройки — `fin-toolkit setup` создаёт `.mcp.json` (локально) или `--global` пишет в `~/.claude.json` + создаёт `~/.config/fin-toolkit/config.yaml` с defaults + показывает статус провайдеров. `fin-toolkit serve` запускает MCP-сервер (ищет конфиг: `./fin-toolkit.yaml` → `~/.config/fin-toolkit/config.yaml` → defaults). `fin-toolkit status` показывает доступные провайдеры и конфигурацию. Установка: `uvx fin-toolkit setup` (primary) или `curl | sh` bootstrap-скрипт из GitHub
- `data-providers`: Async Protocol-based data layer (`@runtime_checkable`) — `DataProvider` с реализациями Yahoo Finance (asyncio.to_thread), KASE scraper (httpx async). Типизированные Pydantic-модели: `PriceData`, `FinancialStatements`, `KeyMetrics`. Market-based routing (KZ тикеры → KASE, остальные → Yahoo). Rate limiting per-provider (token bucket)
- `search-providers`: Protocol-based search layer — `SearchProvider` с реализациями Brave, SearXNG
- `technical-analysis`: Детерминистические расчёты через `ta` (Technical Analysis library) — RSI, EMA (20/50/200), Bollinger Bands, MACD
- `fundamental-analysis`: Ratio engine — рентабельность (ROE, ROA, ROIC), оценка (P/E, P/B, EV/EBITDA, FCF Yield), устойчивость (Debt/Equity, Current Ratio). Hardcoded sector medians (Damodaran) для сравнения
- `risk-analysis`: Историческая волатильность, VaR, корреляционная матрица (принимает готовые PriceData), Kelly Criterion (утилитарный калькулятор)
- `agent-system`: Скоринговые мини-оркестраторы с constructor DI (DataProvider + Analyzers + optional SearchProvider инжектятся) — Elvis Marlamov (100 баллов, Sentiment=0 без SearchProvider) и Warren Buffett. Агенты сами fetch'ат данные через DataProvider и вызывают analyzers — это отличает их от pure-function analyzers. AgentRegistry собирает агентов с зависимостями из конфига. Graceful degradation при отсутствии данных (KASE)
- `mcp-server`: FastMCP async-сервер с 6 tools (orchestration layer — fetch + compute), stdio transport, авто-старт через pitchfork при `cd` в проект. Sector auto-detect для fundamental analysis, graceful degradation для search_news
- `config-system`: YAML-конфигурация + .env для секретов + Pydantic-валидация + auto-detection провайдеров + market-to-provider mapping + per-provider rate limits. Приоритет: env vars > .env file > fin-toolkit.yaml > defaults
- `skills`: 5 SKILL.md-инструкций по Anthropic Skills стандарту — progressive disclosure, MCP-enhanced workflows, error handling

### Modified Capabilities

(нет существующих capabilities — проект создаётся с нуля)

## Impact

- **Новый пакет**: Python 3.11+, публикуется на PyPI. Установка для пользователей: `uvx fin-toolkit setup` (one-click) или `curl -fsSL https://raw.githubusercontent.com/alexey1312/fin-toolkit/main/install.sh | sh` (bootstrap с нуля). Для разработчиков: `git clone` + `mise install && uv sync`
- **Tooling**: mise.toml (python, uv, ruff, pitchfork), pyproject.toml (uv), pitchfork.toml (MCP daemon)
- **Зависимости**: yfinance, pandas, ta, fastmcp, pydantic, httpx, beautifulsoup4, python-dotenv
- **Dev-зависимости**: pytest, pytest-cov, pytest-asyncio, mypy, ruff
- **MCP интеграция**: `fin-toolkit setup` создаёт `.mcp.json` автоматически (command: `uvx fin-toolkit serve`). Опционально pitchfork для auto-start/stop
- **Skills**: 5 SKILL.md в `skills/` — устанавливаются в `~/.claude/skills/` или через Claude.ai
- **Внешние системы**: Yahoo Finance (бесплатно), kase.kz (скрапинг), опционально Brave/SearXNG/FMP
- **Тестирование**: TDD — тесты пишутся первыми, pytest, mock-данные, coverage >= 80%
- **CLI**: `fin-toolkit setup` (one-click MCP setup), `fin-toolkit serve` (запуск MCP-сервера), `fin-toolkit status` (диагностика). Также через pitchfork daemon
