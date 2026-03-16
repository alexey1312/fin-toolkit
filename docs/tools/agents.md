# Agent Tools

## run_agent

Run a single AI analysis agent on a ticker.

```
ticker: "AAPL"
agent: "elvis_marlamov"   # or warren_buffett, ben_graham, charlie_munger, cathie_wood, peter_lynch
```

Returns: signal (Bullish/Neutral/Bearish), score (0–100), confidence (0.0–1.0), rationale, breakdown by scoring blocks.

See [Analysis Agents](#available-agents) for details on each agent's methodology.

## run_all_agents

Run all active agents on a ticker and compute consensus.

```
ticker: "AAPL"
```

Returns: consensus score, signal, confidence, and per-agent results. Agents run concurrently via `asyncio.gather`.

## run_recommendation

Generate a buy/hold recommendation with position sizing.

```
ticker: "AAPL"
period: "1y"
```

Returns: consensus, risk metrics, technical signals, position size (0–25% portfolio), stop-loss level.

---

## Available Agents

| Agent | Style | Scoring Blocks |
|-------|-------|----------------|
| `elvis_marlamov` | Fundamentals + sentiment | valuation / quality / catalysts / financial_health |
| `warren_buffett` | Value investing | margin_of_safety / durable_advantage / management_quality |
| `ben_graham` | Deep value | net_net_value / earnings_stability / financial_strength |
| `charlie_munger` | Wonderful business at fair price | business_quality / fair_price / financial_fortress |
| `cathie_wood` | Innovation & growth | growth_signals / innovation_premium / market_position |
| `peter_lynch` | GARP | peg_value / earnings_quality / common_sense |

Each agent implements the `AnalysisAgent` protocol and returns an `AgentResult` with signal, score, confidence, and per-block breakdown.
