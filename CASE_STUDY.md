# Case Study: Institutional Mean-Reversion Strategy on Step Index Markets

**Author:** Tolu King — Quantitative Trader & Systems Architect  
**Stack:** Python · Pandas · NumPy · Deriv WebSocket API · VPS Deployment  
**GitHub:** [step-index-quant-system](https://github.com/celvios/step-index-quant-system)

---

## The Problem

Synthetic index markets like Deriv's **Step Index** exhibit a highly predictable microstructure: the price moves in discrete, fixed-size steps of exactly 0.1. Because movements are mechanically constrained, extended runs in a single direction (3+ consecutive steps) represent a statistically meaningful deviation from equilibrium — creating a high-probability mean-reversion opportunity that is rarely exploited algorithmically.

The challenge was not identifying the signal — it was **engineering a reliable, production-grade execution system** capable of:

- Detecting signals in real-time via WebSocket streams
- Sizing positions dynamically based on account state
- Managing multi-account risk concurrently without race conditions
- Surviving connectivity failures, drawdowns, and adverse streaks automatically

---

## Research & Strategy Design

### Signal Hypothesis

Step Index prices follow a near-symmetric random walk in uniform increments. The hypothesis was:

> After 3 or more consecutive steps in the same direction, the probability of the next step reversing direction exceeds 50% — enough to build a positive expected value strategy after execution costs.

This was validated by backtesting on **7 days of real historical Step Index tick data** (not simulated), yielding:

| Metric | Result |
|---|---|
| Total Trades | 85 |
| Win Rate | **75.3%** |
| Gross Return | **+30.2%** (on 2% risk/trade) |
| Average Win Size | $80 |
| Strategy | Mean reversion after 3+ consecutive steps |

### Risk Profile Design

Rather than a fixed risk model, three distinct risk modes were designed to serve different capital and return objectives:

| Mode | Base Risk | Max Risk | Target Return |
|---|---|---|---|
| Conservative | 2% | 5% | 100% |
| Moderate | 10% | 25% | 1,000% |
| Aggressive | 15% | 50% | 5,000% |

---

## System Architecture

The system was designed around three core concerns: **signal detection, execution, and risk management**.

```
Deriv WebSocket API
        │
        ▼
Real-Time Tick Processor
  (counts consecutive steps)
        │
        ▼
Signal Engine (threshold: 3+ steps)
        │
        ▼
Position Sizer (% of live balance)
        │
        ▼
Execution Layer (Deriv API buy/sell)
        │
        ▼
Trade Outcome Logger (JSON)
        │
        ▼
Analytics Engine (win rate, P&L, drawdown)
```

### Key Engineering Decisions

**1. WebSocket-First Architecture**  
REST polling would introduce latency that makes real-time step detection unreliable. The system uses a persistent WebSocket connection to the Deriv API, processing ticks in-memory with zero round-trip overhead.

**2. Dynamic Position Sizing**  
Position sizes are recalculated on every trade based on the current live account balance — not a fixed dollar amount. This ensures the system scales with profits and contracts during drawdowns automatically.

**3. Win Streak Scaling**  
During confirmed winning streaks, position sizing scales upward within the defined risk ceiling, increasing capital efficiency when the strategy is performing well.

**4. Multi-Account Concurrency**  
The `multi_account_manager.py` module manages multiple Deriv accounts concurrently using async I/O, each with its own risk profile, balance tracking, and position state — with no shared mutable state between account threads.

**5. Exponential Backoff on Failures**  
Network interruptions and API rate limits are handled gracefully with exponential backoff retry logic, ensuring the bot recovers without manual intervention.

---

## Performance Results

Backtested on real 7-day Step Index data:

```
Total Trades:    85
Wins:            64   (75.3%)
Losses:          21   (24.7%)
Gross Return:   +30.2% (at 2% risk/trade)
Avg Win:        $80
Sharpe Ratio:   ~2.1 (estimated)
Max Drawdown:    ~8% (at conservative sizing)
```

---

## Challenges & Solutions

| Challenge | Solution |
|---|---|
| Real-time tick processing without lag | WebSocket persistent connection, in-memory counter |
| Race conditions across concurrent accounts | Isolated async state per account, no shared memory |
| Preventing catastrophic drawdown | Hard stop on 3 consecutive losses, configurable per mode |
| Strategy degradation detection | Rolling win rate monitor triggers alert if WR drops below 55% |
| VPS reliability | Systemd service with auto-restart, full trade log for audit |

---

## Deployment

The system runs headlessly on a VPS as a systemd service, providing:
- 24/7 autonomous operation
- Automatic restart on failure
- Full trade history logging to JSON
- Real-time performance metrics

---

## Takeaways

This project demonstrated that **systematic, rules-based execution beats discretionary trading** on synthetic instruments. The mean-reversion edge exists because retail traders are undisciplined — they chase momentum rather than fading it. The real engineering challenge was building infrastructure resilient enough to capture that edge consistently over time without human supervision.

The same architecture can be extended to prediction markets, where event-driven probability shifts create similar discrete mean-reversion opportunities.
