# 📈 Trend Breakout with Volume-Weighted Buy-Sell Strategy

## 1. Strategy Description

This trading algorithm combines **trend detection**, **macro-level high/low analysis**, and **volume spike confirmation** to generate buy and sell signals. The strategy aims to capture emerging uptrends while minimizing downside risk using **stop-losses** and **volume-based sell triggers**.

### 🔹 Steps Followed

1. **Trend Detection**

   * Uses rolling windows of closing prices to detect **uptrends** (rising highs/lows) or **downtrends** (falling highs/lows).
   * Labels each price point with trend classification:

     * `1` → Uptrend
     * `0` → Downtrend
     * `-1` → Neutral

2. **Macro High/Low Breakpoints**

   * Identifies **lows** (support points) and **highs** (resistance points) across the trend labels.
   * Tracks breakpoints to determine **buy/sell patterns**.

3. **Buy Signal Logic**

   * A valid **buy pattern** occurs when sequential lows and highs follow a specific order (`L1 < H1 < L2 < H2 < L3`).
   * If confirmed:

     * Allocates **3–5% of available capital** depending on previous buy levels.
     * Places a **limit buy order** with calculated volume.
     * Dynamically sets a **stop-loss** at either:

       * `8% below current price`, or
       * `second last low` (whichever is larger).

4. **Sell Signal Logic**

   * **Forced Sell:** When the number of macro lows decreases (trend breakdown).
   * **Volume Spike Sell:** If current volume exceeds **105% of recent average volume** and price is above open → triggers **limit sell order**.

5. **Risk Management**

   * Uses incremental position sizing (3–5% of capital).
   * Dynamically calculated **stop-losses**.
   * Immediate liquidation on strong **downtrend or spike detection**.

---

### 🔹 Trading Interpretations

* ✅ **Buy** when an uptrend pattern with confirmed macro lows & highs forms, supported by volume.
* ✅ **Sell** when:

  * Trend weakens (macro low count decreases), OR
  * Volume spikes above recent average, signaling potential exhaustion.
* 📉 This strategy attempts to **ride trend breakouts early** while avoiding **false rallies and volume blow-offs**.

---

## 2. Libraries Used

The following libraries are used in the implementation:

* **AlgoAPI** (custom trading API wrapper)

  * `AlgoAPIUtil` → For constructing order objects.
  * `AlgoAPI_Backtest` → For handling backtest event flow.
* **datetime** (standard Python library)

  * Used for timestamps and order reference IDs.

