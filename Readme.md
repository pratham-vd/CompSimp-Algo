================================================================================
                        COMPSIMP TRADER BOT - USER MANUAL
================================================================================

This manual provides a detailed explanation of the `compsimp_trader_bot.py` script.
It explains configuration, trading logic, risk management, and execution details.

--------------------------------------------------------------------------------
1. CONFIGURATION (Lines 7-29)
--------------------------------------------------------------------------------
This section allows you to control the bot's behavior.

- `SYMBOL`: The asset to trade (e.g., "GOLD", "EURUSD"). Must match Market Watch.
- `TIMEFRAME`: The timeframe to analyze (e.g., "M1", "H1").
- `VOL_SENSITIVITY`: Controls EMA speed. Higher (e.g., 2.0) = smoother, Lower (e.g., 1.0) = faster.
- `RISK_PERCENT`: Percentage of account balance to risk per trade (e.g., 1.0 = 1%).
- `TP_RR`: Risk:Reward ratio for the final Take Profit (Fixed at 2.0).
- `PAUSE_START_HOUR/MINUTE`: Start time for the daily trading pause (monitoring stops).
- `PAUSE_END_HOUR/MINUTE`: End time for the daily trading pause (monitoring resumes).
- `MT5 Creds`: Your Login ID, Password, and Server.

--------------------------------------------------------------------------------
2. TRADING STRATEGY
--------------------------------------------------------------------------------
The bot uses a trend-following strategy based on EMA crossovers and Volatility (ATR).

- **Indicators**:
    - **EMAs**: Three Exponential Moving Averages (EMA1, EMA2, EMA3).
    - **ATR**: Average True Range (14 periods) used for SL distance.
- **Buy Signal (Bull)**:
    - EMA3 is trending up.
    - EMA1 crosses above EMA2.
- **Sell Signal (Bear)**:
    - EMA3 is trending down.
    - EMA1 crosses below EMA2.
- **Stop Loss (SL)**: Set at `Low - (2 * ATR)` for Buys, `High + (2 * ATR)` for Sells.
- **Take Profit (TP)**: Dynamically calculated to be strictly 2x the Risk distance.

--------------------------------------------------------------------------------
3. EXECUTION & RISK MANAGEMENT (Advanced)
--------------------------------------------------------------------------------
This bot uses sophisticated execution logic to ensure accuracy and safety.

A. **Broker Compatibility (Filling Mode)**
   - The bot automatically detects if your broker/symbol requires `IOC`, `FOK`, or `RETURN` filling modes.
   - This prevents "Unsupported filling mode" errors on brokers like XM, Exness, etc.

B. **Dynamic Execution (Slippage Protection)**
   - **Step 1**: Bot sends a market order *without* SL/TP to ensure immediate fill.
   - **Step 2**: Bot captures the **Execution Price** (which may differ from Signal Price due to slippage).
   - **Step 3**: Bot calculates the exact TP required to achieve a 1:2 Risk-Reward from the *Execution Price*.
   - **Step 4**: Bot modifies the open order to attach the fixed SL and the new Dynamic TP.
   - **Result**: You always get a true 1:2 potential return, regardless of slippage.

C. **Partial Close & Breakeven**
   - **Trigger**: When floating profit reaches **1:1 Risk-Reward** (profit = initial risk).
   - **Action 1**: The bot closes **50%** of the volume immediately.
   - **Action 2**: The bot moves the Stop Loss to the **Entry Price (Breakeven)**.
   - **Result**: The remaining 50% of the trade runs "risk-free" targeting the final 1:2 TP.

D. **Trading Pause**
   - The bot will sleep and ignore all signals between the configured generic start and end times.
   - Example: Pauses from 03:00 to 04:45 local time to avoid high-spread rollover periods.

--------------------------------------------------------------------------------
4. LOGGING & TRANSPARENCY
--------------------------------------------------------------------------------
The terminal provides real-time feedback:

- **Startup**: Shows Account Balance and time until next Pause.
- **Trade Open**: Logs the configured Signal Price vs. Actual Execution Price (Slippage). shows the calculated "Partial TP" (1:1 level) and "New TP" (1:2 level).
- **Partial Close**: Logs the exact price and profit booked when 50% is closed.
- **Trade Close**: Logs the final result, reason (SL/TP/Algo), and updated Account Balance.

--------------------------------------------------------------------------------
5. MARKET DATA
--------------------------------------------------------------------------------
- The bot fetches `DATA_BARS_NEEDED` (default 200) candles.
- It calculates indicators based on **Closed Candles** only (Index 1 to N).
- Index 0 (current forming candle) is ignored to prevent "repainting" signals.

--------------------------------------------------------------------------------
END OF MANUAL
--------------------------------------------------------------------------------
