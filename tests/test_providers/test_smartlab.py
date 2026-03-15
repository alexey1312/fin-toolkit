"""Tests for SmartLab provider."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from fin_toolkit.exceptions import TickerNotFoundError
from fin_toolkit.providers.smartlab import SmartLabProvider, _parse_fundamental_table, _parse_number


# ---------------------------------------------------------------------------
# _parse_number
# ---------------------------------------------------------------------------


class TestParseNumber:
    def test_simple_int(self) -> None:
        assert _parse_number("100") == pytest.approx(100.0)

    def test_thousands_space(self) -> None:
        assert _parse_number("5 311") == pytest.approx(5311.0)

    def test_decimal(self) -> None:
        assert _parse_number("1 084.0") == pytest.approx(1084.0)

    def test_negative(self) -> None:
        assert _parse_number("-517.2") == pytest.approx(-517.2)

    def test_percentage(self) -> None:
        assert _parse_number("24.2%") == pytest.approx(24.2)

    def test_empty(self) -> None:
        assert _parse_number("") is None

    def test_none_text(self) -> None:
        assert _parse_number("—") is None

    def test_zero(self) -> None:
        assert _parse_number("0.00") == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _parse_fundamental_table (HTML → dict)
# ---------------------------------------------------------------------------

_SAMPLE_HTML = """
<table class="simple-little-table little trades-table" cellspacing="0">
<tr>
    <th>№</th><th>Название</th><th>Тикер</th>
    <th class="chartrow">&nbsp;</th><th class="chartrow">&nbsp;</th>
    <th>Капит-я<br/> млрд руб</th>
    <th>EV<br/> млрд руб</th>
    <th>Выручка</th>
    <th>Чистая<br/>прибыль</th>
    <th>ДД ао, %</th><th>ДД ап, %</th>
    <th>ДД/ЧП,<br/> %</th>
    <th>P/E</th><th>P/S</th><th>P/B</th>
    <th>EV/EBITDA</th>
    <th>Рентаб.<br/>EBITDA</th>
    <th>долг/EBITDA</th>
    <th>отчет</th>
</tr>
<tr>
    <td>1</td>
    <td><a href="/forum/LKOH">Лукойл</a></td>
    <td>LKOH</td>
    <td><a class="charticon" href="/gr/MOEX.LKOH"></a></td>
    <td><a class="charticon2" href="/q/LKOH/f/y/"></a></td>
    <td>4 011</td>
    <td>2 865</td>
    <td>8 622</td>
    <td>848.5</td>
    <td>18.2%</td>
    <td></td>
    <td>85%</td>
    <td>4.7</td>
    <td>0.5</td>
    <td>0.6</td>
    <td>1.6</td>
    <td>21%</td>
    <td>-0.6</td>
    <td>2024-МСФО</td>
</tr>
<tr>
    <td>2</td>
    <td><a href="/forum/SBER">Сбербанк</a></td>
    <td>SBER</td>
    <td><a class="charticon" href="/gr/MOEX.SBER"></a></td>
    <td><a class="charticon2" href="/q/SBER/f/y/"></a></td>
    <td>6 782</td>
    <td>2 844</td>
    <td></td>
    <td>1 707</td>
    <td>12.5%</td>
    <td>12.5%</td>
    <td>50%</td>
    <td>3.97</td>
    <td></td>
    <td>0.81</td>
    <td></td>
    <td></td>
    <td>0.0</td>
    <td>2025-МСФО</td>
</tr>
</table>
"""


class TestParseFundamentalTable:
    def test_parses_two_tickers(self) -> None:
        result = _parse_fundamental_table(_SAMPLE_HTML)
        assert "LKOH" in result
        assert "SBER" in result

    def test_lkoh_metrics(self) -> None:
        result = _parse_fundamental_table(_SAMPLE_HTML)
        lkoh = result["LKOH"]
        assert lkoh["market_cap"] == pytest.approx(4011.0)
        assert lkoh["pe_ratio"] == pytest.approx(4.7)
        assert lkoh["pb_ratio"] == pytest.approx(0.6)
        assert lkoh["ev_ebitda"] == pytest.approx(1.6)
        assert lkoh["dividend_yield"] == pytest.approx(18.2)

    def test_sber_missing_values(self) -> None:
        result = _parse_fundamental_table(_SAMPLE_HTML)
        sber = result["SBER"]
        assert sber["market_cap"] == pytest.approx(6782.0)
        assert sber["revenue"] is None  # empty cell
        assert sber["pe_ratio"] == pytest.approx(3.97)


# ---------------------------------------------------------------------------
# SmartLabProvider.get_metrics
# ---------------------------------------------------------------------------


class TestSmartLabGetMetrics:
    async def test_valid_ticker(self) -> None:
        provider = SmartLabProvider()
        # Mock the HTTP call to return our sample HTML
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_HTML

        with patch("fin_toolkit.providers.smartlab.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.get_metrics("LKOH")

        assert result.ticker == "LKOH"
        assert result.pe_ratio == pytest.approx(4.7)
        assert result.pb_ratio == pytest.approx(0.6)
        assert result.ev_ebitda == pytest.approx(1.6)
        assert result.market_cap == pytest.approx(4_011_000_000_000)  # млрд → руб

    async def test_ticker_not_found(self) -> None:
        provider = SmartLabProvider()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_HTML

        with patch("fin_toolkit.providers.smartlab.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            with pytest.raises(TickerNotFoundError):
                await provider.get_metrics("INVALID")


# ---------------------------------------------------------------------------
# SmartLabProvider.get_financials
# ---------------------------------------------------------------------------

_SAMPLE_FINANCIALS_HTML = """
<table class="simple-little-table financials" cellspacing="0">
<tr class="header_row">
    <th colspan="2">Лукойл</th>
    <td class="chartrow">&nbsp;</td>
    <td><strong>2022</strong></td>
    <td><strong>2023</strong></td>
    <td><strong>2024</strong></td>
    <td class="ltm_spc">&nbsp;</td>
    <td><strong>LTM</strong></td>
</tr>
<tr field="revenue">
    <th>Выручка,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>9 431</td><td>7 928</td><td>8 622</td>
    <td class="ltm_spc">&nbsp;</td><td>8 622</td>
</tr>
<tr field="ebitda">
    <th>EBITDA,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>1 404</td><td>2 005</td><td>1 800</td>
    <td class="ltm_spc">&nbsp;</td><td>1 800</td>
</tr>
<tr field="net_income">
    <th>Чистая прибыль,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>773.4</td><td>790.0</td><td>848.5</td>
    <td class="ltm_spc">&nbsp;</td><td>848.5</td>
</tr>
<tr field="assets">
    <th>Активы,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>6 865</td><td>8 600</td><td>9 200</td>
    <td class="ltm_spc">&nbsp;</td><td>9 200</td>
</tr>
<tr field="net_assets">
    <th>Чистые активы,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>4 515</td><td>6 384</td><td>6 800</td>
    <td class="ltm_spc">&nbsp;</td><td>6 800</td>
</tr>
<tr field="debt">
    <th>Долг,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>758.0</td><td>396.0</td><td>350.0</td>
    <td class="ltm_spc">&nbsp;</td><td>350.0</td>
</tr>
<tr field="ocf">
    <th>Опер.денежный поток,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>1 127</td><td>1 824</td><td>1 500</td>
    <td class="ltm_spc">&nbsp;</td><td>1 500</td>
</tr>
<tr field="capex">
    <th>CAPEX,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>433.0</td><td>720.0</td><td>600.0</td>
    <td class="ltm_spc">&nbsp;</td><td>600.0</td>
</tr>
<tr field="interest_expenses">
    <th>Процентные расходы,млрд руб</th><th></th>
    <td class="chartrow"></td>
    <td>30.8</td><td>24.7</td><td>20.0</td>
    <td class="ltm_spc">&nbsp;</td><td>20.0</td>
</tr>
<tr field="number_of_shares">
    <th>Число акций ао,млн</th><th></th>
    <td class="chartrow"></td>
    <td>650.3</td><td>692.9</td><td>692.9</td>
    <td class="ltm_spc">&nbsp;</td><td>692.9</td>
</tr>
<tr field="common_share">
    <th>Цена акции ао,руб</th><th></th>
    <td class="chartrow"></td>
    <td>6 559</td><td>4 071</td><td>5 800</td>
    <td class="ltm_spc">&nbsp;</td><td>5 800</td>
</tr>
</table>
"""


class TestSmartLabGetFinancials:
    async def test_valid_ticker(self) -> None:
        provider = SmartLabProvider()
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = _SAMPLE_FINANCIALS_HTML
        mock_resp.raise_for_status = lambda: None

        with patch("fin_toolkit.providers.smartlab.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_resp
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await provider.get_financials("LKOH")

        assert result.ticker == "LKOH"
        assert result.income_statement is not None
        assert result.income_statement["revenue"] == pytest.approx(8_622_000_000_000)
        assert result.income_statement["ebitda"] == pytest.approx(1_800_000_000_000)
        assert result.income_statement["net_income"] == pytest.approx(848_500_000_000)
        assert result.balance_sheet is not None
        assert result.balance_sheet["total_assets"] == pytest.approx(9_200_000_000_000)
        assert result.cash_flow is not None
        assert result.income_history is not None
        assert len(result.income_history) >= 3
