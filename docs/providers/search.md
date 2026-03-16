# Search Providers

fin-toolkit uses a **fallback chain** for news search — first available provider wins. The `SearchRouter` iterates the chain and returns results from the first provider that succeeds.

## Fallback Chain

| # | Provider | API Key | Env Var | Notes |
|---|----------|---------|---------|-------|
| 1 | DuckDuckGo | No | — | Always available, default |
| 2 | SearXNG | No | — | Self-hosted (`docker run -p 8888:8080 searxng/searxng`) |
| 3 | Google | Yes | `GEMINI_API_KEY` | Gemini + Search Grounding |
| 4 | Perplexity | Yes | `PERPLEXITY_API_KEY` | AI-powered search with citations |
| 5 | Tavily | Yes | `TAVILY_API_KEY` | Optimized for AI agents |
| 6 | Brave | Yes | `BRAVE_API_KEY` | Web search |
| 7 | Serper | Yes | `SERPER_API_KEY` | Google Search wrapper |
| 8 | Exa | Yes | `EXA_API_KEY` | Semantic / neural search |

## DuckDuckGo

Default, always available. Uses `ddgs` package.

- Uses `ddgs.news()` for articles with dates; falls back to `text()` if news returns empty
- No rate limiting concerns for typical usage

## SearXNG

Self-hosted metasearch engine. No API key, but requires a running instance.

```bash
docker run -p 8888:8080 searxng/searxng
```

Configure URL in `fin-toolkit.yaml`:

```yaml
search:
  searxng_url: http://localhost:8888
```

## Google (Gemini)

Uses Gemini API with Search Grounding for high-quality results.

```yaml
search:
  gemini_model: gemini-3.1-flash-lite  # configurable
```

## Adding a New Search Provider

Implement the `SearchProvider` protocol (~50 lines of code):

```python
@runtime_checkable
class SearchProvider(Protocol):
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]: ...
```

Then register in `config/models.py` and wire in `cli.py`.
