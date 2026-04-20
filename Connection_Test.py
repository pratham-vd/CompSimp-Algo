import MetaTrader5
import pandas
import datetime
from dateutil.relativedelta import relativedelta

# ENTER YOUR MT5 CREDENTIALS HERE
project_settings = {
    "mt5": {
        "username": "308956197",       # Your MT5 Login ID
        "password": "P@vd2007pratham", # Your MT5 Password
        "server": "XMGlobal-MT5 6",    # Your MT5 Server Name
        "mt5_pathway": r"C:\Program Files\MetaTrader 5\terminal64.exe"
    }
}

# FUNCTION TO START METATRADER 5
def start_mt5(project_settings):
    username = int(project_settings['mt5']['username'])
    password = project_settings['mt5']['password']
    server = project_settings['mt5']['server']
    mt5_pathway = project_settings['mt5']['mt5_pathway']

    try:
        mt5_init = MetaTrader5.initialize(
            login=username,
            password=password,
            server=server,
            path=mt5_pathway
        )
    except Exception as e:
        print(f"Error initializing MetaTrader 5: {e}")
        mt5_init = False

    mt5_login = False
    if mt5_init:
        try:
            mt5_login = MetaTrader5.login(login=username, password=password, server=server)
        except Exception as e:
            print(f"Error logging into MetaTrader 5: {e}")
            mt5_login = False

    if mt5_login:
        print("MetaTrader 5 started and logged in successfully!")
        return True
    else:
        print("Failed to start or log in to MetaTrader 5.")
        return False


# FUNCTION TO INITIALIZE A SYMBOL
def initialize_symbol(symbol="BTCUSD"):
    try:
        all_symbols = MetaTrader5.symbols_get()
        symbol_names = [sym.name for sym in all_symbols]

        if symbol in symbol_names:
            MetaTrader5.symbol_select(symbol, True)
            print(f"{symbol} initialized successfully!")
            return True
        else:
            print(f"Symbol {symbol} does not exist. Please update symbol name.")
            return False

    except Exception as e:
        print(f"Error enabling {symbol}: {e}")
        return False


# FUNCTION TO PLACE ORDERS ON MT5
def place_order(order_type, symbol, volume, stop_loss, take_profit, comment,
                direct=False, stop_price=0.00):

    volume = round(float(volume), 2)
    stop_loss = round(float(stop_loss), 4)
    take_profit = round(float(take_profit), 4)
    stop_price = round(float(stop_price), 4)

    request = {
        "symbol": symbol,
        "volume": volume,
        "sl": stop_loss,
        "tp": take_profit,
        "type_time": MetaTrader5.ORDER_TIME_GTC,
        "comment": comment
    }

    # --- MARKET ORDERS ---
    if order_type == "BUY":
        tick = MetaTrader5.symbol_info_tick(symbol)
        request['action'] = MetaTrader5.TRADE_ACTION_DEAL
        request['type'] = MetaTrader5.ORDER_TYPE_BUY
        request['type_filling'] = MetaTrader5.ORDER_FILLING_IOC
        request['price'] = tick.ask  # Current ask price

    elif order_type == "SELL":
        tick = MetaTrader5.symbol_info_tick(symbol)
        request['action'] = MetaTrader5.TRADE_ACTION_DEAL
        request['type'] = MetaTrader5.ORDER_TYPE_SELL
        request['type_filling'] = MetaTrader5.ORDER_FILLING_IOC
        request['price'] = tick.bid  # Current bid price

    # --- PENDING ORDERS ---
    elif order_type == "BUY_STOP":
        request['action'] = MetaTrader5.TRADE_ACTION_PENDING
        request['type'] = MetaTrader5.ORDER_TYPE_BUY_STOP
        request['type_filling'] = MetaTrader5.ORDER_FILLING_RETURN
        request['price'] = stop_price

    elif order_type == "SELL_STOP":
        request['action'] = MetaTrader5.TRADE_ACTION_PENDING
        request['type'] = MetaTrader5.ORDER_TYPE_SELL_STOP
        request['type_filling'] = MetaTrader5.ORDER_FILLING_RETURN
        request['price'] = stop_price

    elif order_type == "BUY_LIMIT":
        request['action'] = MetaTrader5.TRADE_ACTION_PENDING
        request['type'] = MetaTrader5.ORDER_TYPE_BUY_LIMIT
        request['type_filling'] = MetaTrader5.ORDER_FILLING_RETURN
        request['price'] = stop_price

    elif order_type == "SELL_LIMIT":
        request['action'] = MetaTrader5.TRADE_ACTION_PENDING
        request['type'] = MetaTrader5.ORDER_TYPE_SELL_LIMIT
        request['type_filling'] = MetaTrader5.ORDER_FILLING_RETURN
        request['price'] = stop_price

    else:
        raise ValueError(f"Invalid order type: {order_type}")

    # --- ORDER EXECUTION LOGIC ---
    if direct is True:
        order_result = MetaTrader5.order_send(request)
        if order_result.retcode == MetaTrader5.TRADE_RETCODE_DONE:
            print(f"Order placed successfully: {symbol}")
            return order_result
        elif order_result.retcode == MetaTrader5.TRADE_RETCODE_AUTOTRADE_DISABLED:
            print("Disable AutoTrading in MT5 terminal and try again.")
        else:
            print(f"Order failed. Code: {order_result.retcode}, Details: {order_result}")
        return order_result
    else:
        result = MetaTrader5.order_check(request)
        if result.retcode in (MetaTrader5.TRADE_RETCODE_DONE, 0):  # treat 0 as success too
            print(f"Order check successful for {symbol}. Placing trade...")
            return place_order(order_type, symbol, volume, stop_loss,
                           take_profit, comment, direct=True, stop_price=stop_price)
        else:
            print(f"Order check failed: {result}")
            return result

# CALL FUNCTIONS HERE
# Start MT5
start_mt5(project_settings)

#Initialize Symbol (you can change symbol here)
initialize_symbol("BTCUSD")

#Place Order Example (edit values as needed)
place_order(
    order_type="SELL",        # "BUY", "SELL", "BUY_STOP", "SELL_STOP", "BUY_LIMIT", "SELL_LIMIT"
    symbol="BTCUSD",            # e.g. "XAUUSD.a" or "BTCUSD"
    volume=1,              # e.g. 0.01
    stop_loss=110585,           # e.g. 2380.00
    take_profit=110189,         # e.g. 2390.00
    comment="SELL",           # Add a note for tracking
    # stop_price=           # For pending orders only
)