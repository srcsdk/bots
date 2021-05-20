# bots

trading bot strategies and technical analysis tools. fetches ohlc data from
yahoo finance, computes indicators, and scans for buy/sell signals using
various strategies.

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
    python bcross.py TSLA 6mo
    python movo.py MSFT --mobr

chart with strategy overlay:

    python gui.py AAPL --strategy movo --period 6mo

short squeeze analysis:

    python reta.py AMC GME BB

options analysis:

    python lambda.py AAPL call 150 2025-04-16

social sentiment:

    python hype.py --ticker AAPL
    python wsb.py --multi

reverse engineer past bottoms:

    python vested.py AAPL
    python vested.py --scan AAPL MSFT TSLA

## indicators

all indicators are in indicators.py: sma, ema, rsi, macd, bollinger bands,
atr, 52-week high/low, volume sma, gap percent.
