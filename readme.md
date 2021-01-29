# bots

trading bot strategies, technical analysis, and portfolio risk tools. fetches
ohlc data from yahoo finance, computes indicators, and scans for buy/sell
signals using various strategies.

## install

from pypi:

    pip install bots

from source:

    git clone <repo-url>
    cd bots
    pip install -e .

requires python 3.7+ and matplotlib.

## strategies

- **gapup** -- buy when rsi < 30, macd turning up, near 52-week low, recent gap down
- **bcross** -- gapup variant requiring macd to cross above signal line
- **across** -- bcross without requiring macd banana up
- **nolo** -- across within 30% of 52-week low
- **movo** -- momentum + volume: price breaking above sma with volume surge
- **nobr** -- nolo + rsi < 45
- **mobr** -- nobr + movo combined, both must trigger within 3 days
- **meanrev** -- mean reversion with z-score and bollinger band entries
- **ichimoku** -- ichimoku cloud tenkan/kijun crossover signals
- **reta** -- short squeeze detection and scoring
- **vested** -- reverse engineer indicators that flagged bottoms in past winners
- **lambda** -- options strategy based on black-scholes greeks
- **hype** -- social media ticker sentiment aggregator (reddit)
- **wsb** -- wallstreetbets ticker mention scanner
- **current** -- market data feed (vix, treasury rates, economic calendar)

## usage

fetch ohlc data:

    python ohlc.py AAPL 6mo

run a strategy scan:

    python gapup.py AAPL
    python movo.py MSFT --mobr
    python meanrev.py TSLA
    python ichimoku.py NVDA

chart with strategy overlay:

    python gui.py AAPL --strategy movo --period 6mo

scan multiple tickers:

    python scanner.py gapup
    python scanner.py --all

backtest a strategy:

    python backtest.py AAPL gapup
    python compare.py ticker AAPL
    python compare.py rank

portfolio and risk:

    python portfolio.py size 10000 150 142
    python var.py AAPL MSFT GOOGL
    python montecarlo.py TSLA 1000 252
    python kelly.py 0.55 3.5 2.0

analysis tools:

    python correlation.py AAPL MSFT GOOGL AMZN
    python pairs.py AAPL MSFT
    python multiframe.py NVDA
    python fibonacci.py AAPL
    python strength.py AAPL MSFT GOOGL

alerts and watchlist:

    python alerts.py add AAPL rsi 30 below
    python alerts.py check
    python watchlist.py add TSLA
    python watchlist.py scan

## indicators

all indicators in indicators.py: sma, ema, rsi, macd, bollinger bands,
atr, 52-week high/low, volume sma, gap percent, vwap, obv,
accumulation/distribution, stochastic, williams %r, cci.
