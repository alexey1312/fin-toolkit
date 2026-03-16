"""Tests for i18n translation and currency helpers."""

from __future__ import annotations

from fin_toolkit.report.i18n import (
    DISCLAIMER,
    HEADERS,
    METRIC_LABELS,
    SIGNALS,
    LangPair,
    currency_symbol,
    fmt_price,
    i18n_span,
)


class TestLangPair:
    def test_lang_pair_has_en_and_ru(self) -> None:
        pair = LangPair(en="Hello", ru="Привет")
        assert pair.en == "Hello"
        assert pair.ru == "Привет"


class TestTranslationDicts:
    def test_headers_has_key_sections(self) -> None:
        assert "price_chart" in HEADERS
        assert "agent_consensus" in HEADERS
        assert "fundamental_snapshot" in HEADERS
        assert "disclaimer" in HEADERS
        assert "investment_thesis" in HEADERS
        assert "target_price" in HEADERS

    def test_signals_has_all_three(self) -> None:
        assert "Bullish" in SIGNALS
        assert "Bearish" in SIGNALS
        assert "Neutral" in SIGNALS
        assert SIGNALS["Bullish"].ru == "Покупать"
        assert SIGNALS["Bearish"].ru == "Продавать"
        assert SIGNALS["Neutral"].ru == "Держать"

    def test_metric_labels_has_key_metrics(self) -> None:
        assert "pe_ratio" in METRIC_LABELS
        assert "roe" in METRIC_LABELS
        assert "debt_to_equity" in METRIC_LABELS

    def test_disclaimer_bilingual(self) -> None:
        assert DISCLAIMER.en != ""
        assert DISCLAIMER.ru != ""
        assert "investment advice" in DISCLAIMER.en.lower()
        assert "рекомендац" in DISCLAIMER.ru.lower()


class TestI18nSpan:
    def test_renders_span_with_both_langs(self) -> None:
        translations = {"title": LangPair(en="Price Chart", ru="График цены")}
        html = i18n_span("title", translations)
        assert 'class="i18n"' in html
        assert 'data-en="Price Chart"' in html
        assert 'data-ru="График цены"' in html

    def test_missing_key_returns_key(self) -> None:
        html = i18n_span("nonexistent", {})
        assert "nonexistent" in html


class TestCurrencySymbol:
    def test_moex_suffix_returns_rub(self) -> None:
        assert currency_symbol("SBER.ME") == "₽"

    def test_known_ru_ticker_returns_rub(self) -> None:
        assert currency_symbol("SBER") == "₽"
        assert currency_symbol("GAZP") == "₽"
        assert currency_symbol("LKOH") == "₽"

    def test_il_suffix_returns_tenge(self) -> None:
        assert currency_symbol("KCEL.IL") == "₸"

    def test_us_ticker_returns_dollar(self) -> None:
        assert currency_symbol("AAPL") == "$"
        assert currency_symbol("MSFT") == "$"

    def test_unknown_returns_dollar(self) -> None:
        assert currency_symbol("XYZ123") == "$"


class TestFmtPrice:
    def test_dollar_formatting(self) -> None:
        assert fmt_price(150.5, "AAPL") == "$150.50"

    def test_rub_formatting(self) -> None:
        result = fmt_price(3200.0, "SBER")
        assert "₽" in result
        assert "3" in result

    def test_tenge_formatting(self) -> None:
        result = fmt_price(5500.0, "KCEL.IL")
        assert "₸" in result

    def test_none_returns_na(self) -> None:
        assert fmt_price(None, "AAPL") == "N/A"
