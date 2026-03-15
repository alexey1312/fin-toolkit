"""Tests for result models: Technical, Fundamental, Risk, Agent, Correlation, Search."""

from fin_toolkit.models.results import (
    AgentResult,
    CorrelationResult,
    FundamentalResult,
    RiskResult,
    SearchResult,
    TechnicalResult,
)


class TestTechnicalResult:
    def test_create_full(self) -> None:
        tr = TechnicalResult(
            rsi=65.3,
            ema_20=152.0,
            ema_50=148.0,
            ema_200=140.0,
            bb_upper=160.0,
            bb_middle=150.0,
            bb_lower=140.0,
            macd_line=2.5,
            macd_signal=1.8,
            macd_histogram=0.7,
            signals={"rsi": "neutral", "macd": "bullish", "bb": "neutral"},
            overall_bias="Bullish",
            warnings=[],
        )
        assert tr.rsi == 65.3
        assert tr.overall_bias == "Bullish"
        assert tr.signals["macd"] == "bullish"

    def test_none_indicators(self) -> None:
        tr = TechnicalResult(
            rsi=None,
            ema_20=None,
            ema_50=None,
            ema_200=None,
            bb_upper=None,
            bb_middle=None,
            bb_lower=None,
            macd_line=None,
            macd_signal=None,
            macd_histogram=None,
            signals={},
            overall_bias="Neutral",
            warnings=["Insufficient data for RSI"],
        )
        assert tr.rsi is None
        assert len(tr.warnings) == 1

    def test_model_dump(self) -> None:
        tr = TechnicalResult(
            rsi=65.3,
            ema_20=152.0,
            ema_50=None,
            ema_200=None,
            bb_upper=None,
            bb_middle=None,
            bb_lower=None,
            macd_line=None,
            macd_signal=None,
            macd_histogram=None,
            signals={"rsi": "neutral"},
            overall_bias="Neutral",
            warnings=[],
        )
        d = tr.model_dump()
        assert d["rsi"] == 65.3
        assert d["ema_50"] is None


class TestFundamentalResult:
    def test_create_full(self) -> None:
        fr = FundamentalResult(
            profitability={
                "roe": 1.56, "roa": 0.275, "roic": 0.55,
                "net_margin": 0.253, "gross_margin": 0.438,
            },
            valuation={
                "pe_ratio": 29.5, "pb_ratio": 46.7, "ev_ebitda": 23.1,
                "fcf_yield": 0.034, "dividend_yield": 0.005,
            },
            stability={"debt_to_equity": 4.67, "current_ratio": 0.99, "interest_coverage": 29.0},
            sector_comparison={"pe_vs_sector": "above_median", "roe_vs_sector": "above_median"},
            warnings=[],
        )
        assert fr.profitability["roe"] == 1.56
        assert fr.sector_comparison["pe_vs_sector"] == "above_median"

    def test_none_sector_comparison(self) -> None:
        fr = FundamentalResult(
            profitability={"roe": None},
            valuation={"pe_ratio": None},
            stability={"debt_to_equity": None},
            sector_comparison={},
            warnings=["No sector data available"],
        )
        assert fr.sector_comparison == {}
        assert len(fr.warnings) == 1


class TestRiskResult:
    def test_create_full(self) -> None:
        rr = RiskResult(
            volatility_30d=0.25,
            volatility_90d=0.22,
            volatility_252d=0.20,
            var_95=-0.032,
            var_99=-0.045,
            warnings=[],
        )
        assert rr.volatility_30d == 0.25
        assert rr.var_95 == -0.032

    def test_none_fields(self) -> None:
        rr = RiskResult(
            volatility_30d=None,
            volatility_90d=None,
            volatility_252d=None,
            var_95=None,
            var_99=None,
            warnings=["Insufficient data"],
        )
        assert rr.volatility_30d is None


class TestAgentResult:
    def test_create_bullish(self) -> None:
        ar = AgentResult(
            signal="Bullish",
            score=82.5,
            confidence=0.85,
            rationale="Strong fundamentals with positive momentum",
            breakdown={"quality": 35.0, "stability": 17.0, "valuation": 22.5, "sentiment": 8.0},
            warnings=[],
        )
        assert ar.signal == "Bullish"
        assert ar.score == 82.5
        assert ar.confidence == 0.85
        assert ar.breakdown["quality"] == 35.0

    def test_create_bearish(self) -> None:
        ar = AgentResult(
            signal="Bearish",
            score=35.0,
            confidence=0.6,
            rationale="Overvalued with declining margins",
            breakdown={"quality": 10.0, "stability": 8.0, "valuation": 12.0, "sentiment": 5.0},
            warnings=["Limited financial data available"],
        )
        assert ar.signal == "Bearish"
        assert ar.score == 35.0


class TestCorrelationResult:
    def test_create(self) -> None:
        cr = CorrelationResult(
            tickers=["AAPL", "MSFT", "GOOGL"],
            matrix={
                "AAPL": {"AAPL": 1.0, "MSFT": 0.85, "GOOGL": 0.78},
                "MSFT": {"AAPL": 0.85, "MSFT": 1.0, "GOOGL": 0.82},
                "GOOGL": {"AAPL": 0.78, "MSFT": 0.82, "GOOGL": 1.0},
            },
            warnings=[],
        )
        assert len(cr.tickers) == 3
        assert cr.matrix["AAPL"]["MSFT"] == 0.85

    def test_with_warnings(self) -> None:
        cr = CorrelationResult(
            tickers=["AAPL", "MSFT"],
            matrix={
                "AAPL": {"AAPL": 1.0, "MSFT": 0.85},
                "MSFT": {"AAPL": 0.85, "MSFT": 1.0},
            },
            warnings=["Short history for MSFT"],
        )
        assert len(cr.warnings) == 1


class TestSearchResult:
    def test_create(self) -> None:
        sr = SearchResult(
            title="Apple Q4 Earnings Beat Expectations",
            url="https://example.com/article",
            snippet="Apple reported Q4 revenue of $89.5B...",
            published_date="2024-01-25",
        )
        assert sr.title == "Apple Q4 Earnings Beat Expectations"
        assert sr.published_date == "2024-01-25"

    def test_none_published_date(self) -> None:
        sr = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Test snippet",
            published_date=None,
        )
        assert sr.published_date is None

    def test_model_dump(self) -> None:
        sr = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            published_date=None,
        )
        d = sr.model_dump()
        assert d["title"] == "Test"
