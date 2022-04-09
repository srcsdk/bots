# hft research notes

## market microstructure foundations

### kyle (1985) - continuous auctions and insider trading
- single informed trader, noise traders, market maker
- price impact is linear in order flow: delta_p = lambda * (order_flow)
- kyle's lambda measures market depth / price sensitivity
- higher lambda = less liquid market, more price impact per unit traded
- lambda increases with information asymmetry

### glosten-milgrom (1985) - bid-ask spread with adverse selection
- spread exists because of informed traders
- market maker sets spread to compensate for losses to informed traders
- wider spread = more adverse selection risk
- spread narrows with more noise traders (uninformed flow)

### roll (1984) - effective spread estimation
- estimates spread from serial covariance of price changes
- effective_spread = 2 * sqrt(-cov(delta_p_t, delta_p_t-1))
- only works when cov is negative (which it usually is for liquid markets)

## colocation and latency arbitrage

### latency tiers
- retail: 50-100ms (broker routing, internet latency)
- premium dma: 5-15ms (direct market access, better routing)
- colocated: 0.5-2ms (server in exchange datacenter)
- fpga/asic: 0.01-0.1ms (hardware-level order processing)

### latency arbitrage mechanics
- stale quote sniping: faster participant picks off stale quotes
- cross-venue arbitrage: same asset priced differently on two exchanges
- statistical arbitrage at microsecond scale
- queue priority: first-in-first-out means latency = priority

### practical considerations
- colocation costs $5k-50k/month depending on exchange
- network hardware (switches, NICs) can cost $100k+
- fpga development requires specialized engineers
- diminishing returns below ~100 microseconds for most strategies

## order flow analysis

### trade classification
- lee-ready algorithm: classify trades as buyer/seller initiated
  - compare trade price to midpoint
  - if above mid -> buyer initiated, below -> seller initiated
  - if at mid, use tick test (compare to previous trade)
- bulk volume classification (BVC): alternative using close-open vs high-low

### volume-synchronized probability of informed trading (vpin)
- easley, lopez de prado, o'hara (2012)
- bucket-based approach: group trades into equal-volume buckets
- measure buy/sell imbalance within each bucket
- vpin = mean(abs(buy_vol - sell_vol) / bucket_vol) over N buckets
- high vpin indicates increased probability of informed trading
- useful as early warning for volatility events
- flash crash of 2010 showed elevated vpin hours before

### order flow toxicity
- toxic flow: flow that consistently moves against the market maker
- measured by adverse selection component of spread
- permanent price impact vs temporary impact
- permanent = information, temporary = liquidity

## practical considerations for retail

### what retail can actually do
- cannot compete on latency (not even close)
- focus on longer timeframes where latency doesn't matter
- use order flow data as supplementary signal, not primary
- vpin can be calculated from public trade data (delayed)

### data sources
- exchange-provided tick data (usually delayed for free tier)
- level 2 order book data from broker
- time and sales data
- sec edgar for institutional holdings (13f)

### realistic edges for retail
- behavioral: patience to hold through volatility
- informational: deep sector expertise in niche areas
- structural: willingness to provide liquidity in small caps
- temporal: longer holding periods avoid most hft competition
