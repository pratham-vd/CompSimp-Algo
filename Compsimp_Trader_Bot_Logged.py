import MetaTrader5 as mt5
import pandas as pd
import time
import datetime
import sys
import csv
import os

print("Starting Compsimp Algo v1 (Logged Version)...")

# ========== USER CONFIGURATION ==========
SYMBOL = "GOLD"
TIMEFRAME = "M1"       # "M1", "M5", "M15", "M30", "H1", "H4", "D1"
VOL_SENSITIVITY = 1.5  # Matches Pine Script "volSen" default
RISK_PERCENT = 1.0     # Risk per trade in %
TP_RR = 2.0            # Risk:Reward ratio = 1:2
DATA_BARS_NEEDED = 200 # Number of candles for indicators
LOOP_SLEEP_SECONDS = 10
MAGIC_NUMBER = 987654

# Trading Pause Times (Local System Time)
PAUSE_START_HOUR = 3
PAUSE_START_MINUTE = 0
PAUSE_END_HOUR = 4
PAUSE_END_MINUTE = 45

# MT5 Credentials (from main.py)
MT5_USERNAME = 167785474
MT5_PASSWORD = "M@nn2007Xz"
MT5_SERVER = "XMGlobal-MT5 2"
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
# =======================================

# Timeframe Map
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}

CSV_FILENAME = "trade_history.csv"

# Global dictionary to store trade context (Signal Price, SL, TP, etc.)
# Key: Ticket (int), Value: dict
TRADE_DETAILS = {}

def log_trade_to_csv(ticket, symbol, action, close_price, profit, reason):
    """Logs detailed trade info to CSV."""
    file_exists = os.path.isfile(CSV_FILENAME)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Retrieve saved context for this trade
    ctx = TRADE_DETAILS.get(ticket, {})
    
    # Extract values (default to 0.0 or N/A if missing, e.g., after restart)
    sig_price = ctx.get('signal_price', 0.0)
    exec_price = ctx.get('exec_price', 0.0)
    slippage = ctx.get('slippage', 0.0)
    sig_sl = ctx.get('signal_sl', 0.0)
    sig_tp = ctx.get('signal_tp', 0.0)
    new_tp = ctx.get('new_tp', 0.0)
    part_tp = ctx.get('partial_tp', 0.0)
    
    # Column Order: 
    # Timestamp, Ticket, Symbol, Action, Signal Price, Exec Price, Slip, 
    # Signal SL, Signal TP, New TP, Partial TP, Close Price, Profit, Reason
    
    headers = [
        "Timestamp", "Ticket", "Symbol", "Action", 
        "Signal Price", "Exec Price", "Slip", 
        "Signal SL", "Signal TP", "New TP", "Partial TP", 
        "Close Price", "Profit", "Reason"
    ]
    
    row = [
        timestamp, ticket, symbol, action,
        f"{sig_price:.2f}", f"{exec_price:.2f}", f"{slippage:.2f}",
        f"{sig_sl:.2f}", f"{sig_tp:.2f}", f"{new_tp:.2f}", f"{part_tp:.2f}",
        f"{close_price:.2f}", f"{profit:.2f}", reason
    ]
    
    try:
        with open(CSV_FILENAME, mode='a', newline='') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)
        print(f"[CSV] Logged {action} for {ticket} to {CSV_FILENAME}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")

    # If it's a full close (not partial), remove from memory to save space
    if action == "CLOSE":
        if ticket in TRADE_DETAILS:
            del TRADE_DETAILS[ticket]

# ... [Imports and other functions remain usage of TRADE_DETAILS] ...

# (For brevity in this tool call, I will rely on context for surrounding code 
# but I need to make sure I don't delete other functions. 
# I will use separate replace calls if needed or careful targeting.)

# Let's target the logging area first.


def connect_mt5():
    """Attempts to initialize and login to MT5. Returns True if successful."""
    try:
        print("Attempting to connect to MT5...")
        if not mt5.initialize(path=MT5_PATH, login=MT5_USERNAME, password=MT5_PASSWORD, server=MT5_SERVER):
            print(f"MT5 Initialize failed, error code = {mt5.last_error()}")
            # Try without path if specific path fails, or just retry
            if not mt5.initialize():
                 print(f"MT5 Initialize (default path) failed, error code = {mt5.last_error()}")
                 return False
        
        # Ensure login
        authorized = mt5.login(login=MT5_USERNAME, password=MT5_PASSWORD, server=MT5_SERVER)
        if authorized:
            print(f"Connected to MT5 account #{MT5_USERNAME}")
            return True
        else:
            print(f"MT5 Login failed, error code = {mt5.last_error()}")
            return False
    except Exception as e:
        print(f"Exception during MT5 connection: {e}")
        return False

def prepare_symbol(symbol):
    """Selects the symbol in Market Watch."""
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        return False
    return True

def get_account_balance():
    """Fetches the current account balance."""
    try:
        account_info = mt5.account_info()
        if account_info:
            return account_info.balance
    except Exception as e:
        print(f"Error fetching balance: {e}")
    return 0.0

def get_latest_candles(symbol, timeframe, count):
    """Fetches the latest CLOSED candles (ignoring the current forming one)."""
    try:
        # Fetch count+1 candles to ensure we have enough closed bars
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 1, count) 
        
        if rates is None or len(rates) == 0:
            print("No data received")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
    except Exception as e:
        print(f"Error fetching candles: {e}")
        return None

def calculate_atr(df, period=14):
    """Calculates ATR."""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean() 
    return atr

def analyze_market(df):
    """
    Calculates indicators and checks for signals.
    Returns dict with signal details or None.
    """
    # OHLC4
    df['ohlc4'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
    
    # EMAs
    ema1_len = int(5 * VOL_SENSITIVITY * 2)
    ema2_len = int(9 * VOL_SENSITIVITY * 2)
    ema3_len = int(13 * VOL_SENSITIVITY * 2)
    
    df['ema1'] = df['ohlc4'].ewm(span=ema1_len, adjust=False).mean()
    df['ema2'] = df['ohlc4'].ewm(span=ema2_len, adjust=False).mean()
    df['ema3'] = df['ohlc4'].ewm(span=ema3_len, adjust=False).mean()
    
    # ATR
    df['atr'] = calculate_atr(df, 14)
    
    # Shift for previous values
    df['ema1_prev'] = df['ema1'].shift(1)
    df['ema2_prev'] = df['ema2'].shift(1)
    df['ema3_prev'] = df['ema3'].shift(1)
    
    # Last closed candle (last row of our closed-candle DF)
    last = df.iloc[-1]
    
    # Signals
    bull = (last['ema3'] >= last['ema3_prev']) and \
           (last['ema1'] >= last['ema2']) and \
           (last['ema1_prev'] < last['ema2_prev'])
           
    bear = (last['ema3'] <= last['ema3_prev']) and \
           (last['ema1'] <= last['ema2']) and \
           (last['ema1_prev'] > last['ema2_prev'])
           
    signal = None
    
    if bull:
        atr_stop = last['low'] - (last['atr'] * 2)
        entry = last['close']
        sl_dist = abs(entry - atr_stop)
        tp = entry + (sl_dist * TP_RR)
        signal = {
            "type": "BUY",
            "entry": entry,
            "sl": atr_stop,
            "tp": tp
        }
        
    elif bear:
        atr_stop = last['high'] + (last['atr'] * 2)
        entry = last['close']
        sl_dist = abs(entry - atr_stop)
        tp = entry - (sl_dist * TP_RR)
        signal = {
            "type": "SELL",
            "entry": entry,
            "sl": atr_stop,
            "tp": tp
        }
        
    return signal

def calculate_volume(symbol, entry, sl, risk_percent):
    """Calculates position size based on risk percentage."""
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return None
            
        balance = account_info.balance
        risk_amount = balance * (risk_percent / 100)
        
        sl_dist = abs(entry - sl)
        
        # Symbol info for tick value/size
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
            
        if symbol_info.trade_tick_size == 0:
            return 0.01 # Fallback
            
        tick_size = symbol_info.trade_tick_size
        tick_value = symbol_info.trade_tick_value
        
        if tick_value == 0: 
             return None

        loss_per_lot = (sl_dist / tick_size) * tick_value
        
        if loss_per_lot == 0:
            return None
            
        volume = risk_amount / loss_per_lot
        
        # Normalize volume
        min_vol = symbol_info.volume_min
        max_vol = symbol_info.volume_max
        step_vol = symbol_info.volume_step
        
        # Round to nearest step
        volume = round(volume / step_vol) * step_vol
        
        if volume < min_vol: volume = min_vol 
        if volume > max_vol: volume = max_vol
        
        return float(f"{volume:.2f}") 
        
    except Exception as e:
        print(f"Error calculating volume: {e}")
        return None

def has_open_position(symbol):
    """Checks if there is an open position for the symbol."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None:
        return False, None
    if len(positions) > 0:
        return True, positions[0] # Return the first position
    return False, None

def close_position(position):
    """Closes a specific position."""
    tick = mt5.symbol_info_tick(position.symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position.ticket,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
        "price": tick.ask if position.type == mt5.ORDER_TYPE_SELL else tick.bid,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Close opposite signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Failed to close position: {result.comment}")
    else:
        print(f"Position closed: {position.ticket}")

def get_filling_mode(symbol):
    """Determines the correct filling mode for the symbol."""
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return mt5.ORDER_FILLING_FOK # Default fallback
    
    filling = symbol_info.filling_mode
    
    # 2 is SYMBOL_FILLING_IOC
    if filling & 2:
        return mt5.ORDER_FILLING_IOC
    # 1 is SYMBOL_FILLING_FOK
    elif filling & 1:
        return mt5.ORDER_FILLING_FOK
    else:
        return mt5.ORDER_FILLING_RETURN

def open_trade(symbol, signal_type, volume, sl, tp, signal_price):
    """
    Opens a market trade (no SL/TP initially).
    Then modifies it to set SL and Dynamic TP based on actual execution price.
    """
    tick = mt5.symbol_info_tick(symbol)
    
    order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if signal_type == "BUY" else tick.bid
    
    fill_mode = get_filling_mode(symbol)
    
    # 1. Send Order WITHOUT SL/TP to ensure fill
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "Compsimp v1",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": fill_mode,
    }
    
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.comment} ({result.retcode})")
        return None
    else:
        # Order Filled. Now Get Execution Price.
        ticket = result.order
        exec_price = result.price 
        # Note: result.price is typically the price of the deal.
        
        # Calculate DYNAMIC TP
        # SL is fixed level (chart-based). 
        # Risk = |Exec - SL|
        # TP = Exec + (Risk * 2)
        
        dist_to_sl = abs(exec_price - sl)
        if signal_type == "BUY":
            # If Exec > SL (Standard Buy), TP is Exec + 2*Dist
            # If Exec < SL (Gap down below SL), this logic would be weird, assumes normal fill
            dynamic_tp = exec_price + (dist_to_sl * TP_RR)
            partial_tp = exec_price + dist_to_sl
        else:
            dynamic_tp = exec_price - (dist_to_sl * TP_RR)
            partial_tp = exec_price - dist_to_sl
            
        slippage = exec_price - signal_price
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] {signal_type} {symbol} | Signal: {signal_price} | Exec: {exec_price} | Slip: {slippage:.2f} | Signal SL: {sl:.2f} | Signal TP: {tp:.2f} | NEW TP: {dynamic_tp:.2f} | Partial TP: {partial_tp:.2f}")

        # 2. Modify Position to add SL/TP
        time.sleep(0.5) # Slight delay to let server register position
        request_mod = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": sl,
            "tp": dynamic_tp
        }
        
        res_mod = mt5.order_send(request_mod)
        if res_mod.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"FAILED to set SL/TP: {res_mod.comment}")
            
        # Save Context for Logging
        TRADE_DETAILS[ticket] = {
            'signal_price': signal_price,
            'exec_price': exec_price,
            'slippage': slippage,
            'signal_sl': sl,
            'signal_tp': tp,
            'new_tp': dynamic_tp,
            'partial_tp': partial_tp
        }
            
        return ticket

def check_last_trade_result(ticket):
    """Checks history to see why the position closed."""
    time.sleep(1)
    history = mt5.history_deals_get(position=ticket)
    
    if history is None or len(history) == 0:
        print(f"Could not fetch history for ticket {ticket}")
        return

    close_deal = history[-1]
    
    if close_deal.entry == mt5.DEAL_ENTRY_OUT:
        profit = close_deal.profit
        price = close_deal.price
        reason_map = {
            mt5.DEAL_REASON_CLIENT: "Manual Close",
            mt5.DEAL_REASON_MOBILE: "Mobile App",
            mt5.DEAL_REASON_WEB: "Web Terminal",
            mt5.DEAL_REASON_EXPERT: "Algo Close",
            mt5.DEAL_REASON_SL: "Stop Loss", 
            mt5.DEAL_REASON_TP: "Take Profit",
            mt5.DEAL_REASON_SO: "Stop Out",
        }
        reason = reason_map.get(close_deal.reason, f"ReasonCode {close_deal.reason}")
        
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}] Trade Closed | Ticket: {ticket} | Reason: {reason} | Price: {price} | Profit: {profit:.2f}")
        
        # LOG TO CSV
        log_trade_to_csv(ticket, SYMBOL, "CLOSE", price, profit, reason)

        # Show updated balance
        balance = get_account_balance()
        print(f"Updated Account Balance: ${balance:.2f}")

def is_pause_time():
    """Checks if current time is within the pause window."""
    now = datetime.datetime.now().time()
    start = datetime.time(PAUSE_START_HOUR, PAUSE_START_MINUTE)
    end = datetime.time(PAUSE_END_HOUR, PAUSE_END_MINUTE)
    
    # Simple check for same-day interval
    if start <= end:
        return start <= now <= end
    else: # Crosses midnight (e.g. 23:00 to 02:00)
        return now >= start or now <= end

def get_time_until_pause():
    """Calculates time remaining until next pause start."""
    now = datetime.datetime.now()
    today_pause = now.replace(hour=PAUSE_START_HOUR, minute=PAUSE_START_MINUTE, second=0, microsecond=0)
    
    if now < today_pause:
        diff = today_pause - now
    else:
        # Pause is tomorrow
        tomorrow_pause = today_pause + datetime.timedelta(days=1)
        diff = tomorrow_pause - now
        
    hours, remainder = divmod(diff.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours} hours and {minutes} minutes"

def manage_position_risk(position, current_price, processed_partial_close):
    """
    Checks if position reached 1:1 RR.
    If yes, closes 50% and moves SL to Entry (Break Even).
    """
    tn = int(position.ticket)
    if tn in processed_partial_close:
        return

    # Calculate 1:1 Target
    # Original Risk = |Entry - SL|
    # Note: If SL was manually moved, this might be off, but we assume initial logic
    dist = abs(position.price_open - position.sl)
    
    if dist == 0: return # Should not happen unless already at BE
    
    reached_target = False
    if position.type == mt5.ORDER_TYPE_BUY:
        target_price = position.price_open + dist
        if current_price >= target_price:
            reached_target = True
    else: # SELL
        target_price = position.price_open - dist
        if current_price <= target_price:
            reached_target = True
            
    if reached_target:
        # 1. Partial Close (50%)
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info: return
        
        step_vol = symbol_info.volume_step
        # Calculate half volume, ensuring it's valid
        half_vol = round((position.volume * 0.5) / step_vol) * step_vol
        
        partial_close_done = False
        partial_profit = 0.0
        partial_price = 0.0
        
        if half_vol >= symbol_info.volume_min:
             tick = mt5.symbol_info_tick(position.symbol)
             fill_mode = get_filling_mode(position.symbol)
             
             request_close = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": position.ticket,
                "symbol": position.symbol,
                "volume": half_vol,
                "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "price": tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask,
                "magic": MAGIC_NUMBER,
                "comment": "Partial Close 1:1",
                "type_filling": fill_mode,
             }
             res_close = mt5.order_send(request_close)
             if res_close.retcode != mt5.TRADE_RETCODE_DONE:
                 print(f"Partial close failed: {res_close.comment}")
             else:
                 partial_close_done = True
                 # Fetch deal info for profit/price
                 if res_close.deal:
                     time.sleep(0.1) # Wait for deal to be in history
                     deals = mt5.history_deals_get(ticket=res_close.deal)
                     if deals and len(deals) > 0:
                         partial_profit = deals[0].profit
                         partial_price = deals[0].price
                         
                 # LOG PARTIAL TO CSV
                 log_trade_to_csv(position.ticket, SYMBOL, "PARTIAL_CLOSE", partial_price, partial_profit, "1:1 Target Hit")
        
        # 2. Move SL to Break Even (Entry Price)
        request_sl = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": position.price_open, 
            "tp": position.tp,
        }
        res_sl = mt5.order_send(request_sl)
        
        sl_moved = False
        if res_sl.retcode != mt5.TRADE_RETCODE_DONE:
             print(f"Failed to move SL to BE: {res_sl.comment}")
        else:
             sl_moved = True

        if partial_close_done and sl_moved:
            print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 50% partials booked at {partial_price} (Profit: ${partial_profit:.2f}), 1:1 Hit, SL set to Entry price (Risk free). Now aiming 1:2")
             
        # Mark as processed so we don't do it again
        processed_partial_close.add(tn)


def main():
    # Show countdown to next pause
    countdown = get_time_until_pause()
    print(f"Time until next pause ({PAUSE_START_HOUR:02d}:{PAUSE_START_MINUTE:02d}): {countdown}")
    
    if not connect_mt5():
        print("Initial connection failed. Exiting.")
        return

    # Show initial balance
    balance = get_account_balance()
    print(f"Current Account Balance: ${balance:.2f}")

    if not prepare_symbol(SYMBOL):
        return

    print(f"Monitoring {SYMBOL} on {TIMEFRAME} timeframe...")
    
    mt5_timeframe = TIMEFRAME_MAP.get(TIMEFRAME, mt5.TIMEFRAME_H1)
    
    last_ticket = 0
    paused_state = False
    processed_tickets = set()
    processed_partial_close = set()
    
    while True:
        try:
            # Check Pause Time
            if is_pause_time():
                if not paused_state:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Pausing monitoring (03:00 - 04:45 local)...")
                    paused_state = True
                time.sleep(60) # Sleep checking every minute when paused
                continue
            else:
                if paused_state:
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] Resuming monitoring...")
                    paused_state = False
                    prepare_symbol(SYMBOL) # Re-ensure symbol is ready

            # Check connection
            if not mt5.terminal_info():
                print("MT5 disconnected. Reconnecting...")
                if not connect_mt5():
                    time.sleep(LOOP_SLEEP_SECONDS)
                    continue
                else:
                    print(f"Reconnected successfully. Resuming analysis...")
                    prepare_symbol(SYMBOL)
            
            # Get Data
            df = get_latest_candles(SYMBOL, mt5_timeframe, DATA_BARS_NEEDED)
            if df is not None:
                # Analyze
                signal = analyze_market(df)
                
                # Check current positions
                has_pos, current_pos = has_open_position(SYMBOL)
                
                # TRACKING LOGIC
                if last_ticket > 0:
                    if not has_pos or (has_pos and current_pos.ticket != last_ticket):
                        if last_ticket not in processed_tickets:
                             check_last_trade_result(last_ticket)
                             processed_tickets.add(int(last_ticket))
                        last_ticket = 0
                
                if has_pos:
                     # Manage Risk (Partial Close & BE)
                     # We need current price for this
                     current_price = df.iloc[-1]['close'] # Approx close price of last closed bar? 
                     # Better to use actual current tick for precision
                     tick = mt5.symbol_info_tick(SYMBOL)
                     if tick:
                         curr_price = tick.bid if current_pos.type == mt5.ORDER_TYPE_BUY else tick.ask
                         manage_position_risk(current_pos, curr_price, processed_partial_close)

                     if last_ticket == 0 and current_pos.ticket not in processed_tickets:
                         last_ticket = int(current_pos.ticket)
                         print(f"Tracking existing position: {last_ticket}")

                if signal:
                    do_trade = False
                    
                    if has_pos:
                        pos_type = "BUY" if current_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                        if pos_type != signal['type']:
                            # Prevent processing the same closing ticket multiple times
                            if int(current_pos.ticket) in processed_tickets:
                                # We already handled this close, waiting for MT5 to update
                                pass
                            else:
                                print(f"Opposite signal detected ({signal['type']}). Closing current {pos_type}...")
                                close_position(current_pos)
                                
                                # Log it immediately
                                check_last_trade_result(current_pos.ticket)
                                processed_tickets.add(int(current_pos.ticket))
                                    
                                last_ticket = 0
                                do_trade = True
                        else:
                            pass
                    else:
                        do_trade = True
                        
                    if do_trade:
                        vol = calculate_volume(SYMBOL, signal['entry'], signal['sl'], RISK_PERCENT)
                        if vol:
                            # Pass entry price as signal_price
                            new_ticket = open_trade(SYMBOL, signal['type'], vol, signal['sl'], signal['tp'], signal['entry'])
                            if new_ticket:
                                last_ticket = int(new_ticket)
                        else:
                            print("Invalid volume calculation. Trade skipped.")
            
            time.sleep(LOOP_SLEEP_SECONDS)
            
        except KeyboardInterrupt:
            print("Stopping bot...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(LOOP_SLEEP_SECONDS)
            
    mt5.shutdown()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        input("Press Enter to exit...")
