import requests
import numpy as np
import pandas as pd
from enum import Enum
from datetime import datetime

"""
Example:

symbol_list = ["BTCUSDT"]
interval = Interval.Minute_30.value
start_time = datetime_timestamp(2021, 10, 1, 0, 0, 0)
end_time = datetime_timestamp(2022, 6, 30, 0, 0, 0)
column_name = ["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", "Quote asset volume", 
       "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"]
Data = pd.DataFrame(get_klines("BTCUSDT", interval, start_time, end_time), columns = column_name)
"""

class Interval(Enum):
    """
    Interval for klines
    
    """
    Minute_1 = '1m'
    Minute_3 = '3m'
    Minute_5 = '5m'
    Minute_15 = '15m'
    Minute_30 = '30m'
    Hour_1 = '1h'
    Hour_2 = '2h'
    Hour_4 = '4h'
    Hour_6 = '6h'
    Hour_8 = '8h'
    Hour_12 = '12h'
    Day_1 = '1d'
    Day_3 = '3d'
    Week_1 = '1w'
    Month_1 = '1M'
    
class OrderType(Enum):
    """
    Order type
    
    """
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class positionside(Enum):
    BOTH = 'BOTH'
    LONG = 'LONG'
    SHORT = 'SHORT'

class TimeInForce(Enum):
    GTC="GTC"
    IOD="IOC"
    FOK="FOK"
    GTX="GTX"

class OrderSide(Enum):
    """
    Order Side
    
    """
    BUY = "BUY"
    SELL = "SELL"

class ContractType(Enum):
    PERPETUAL = "PERPETUAL"
    CURRENT_MONTH = "CURRENT_MONTH"
    NEXT_MONTH = "NEXT_MONTH"
    CURRENT_QUARTER = "CURRENT_QUARTER"
    NEXT_QUARTER = "NEXT_QUARTER"

def get_exchange_info():
    """
    All Coin List
    
    """
    return requests.get("https://api.binance.com/api/v1/exchangeInfo").json()

def get_symbol(target: str = None, margined = "USDT", status = "TRADING"):
    """
    Get Specific Symbol List
    
    """
    SymbolList = get_exchange_info()
    SymbolList = [s["symbol"] for s in SymbolList["symbols"] if s["status"] == status]
    if target:
        SymbolList = [s for s in SymbolList if s[:len(target)] == target]
    if margined:
        SymbolList = [s for s in SymbolList if s[-len(margined):] == margined]
    return SymbolList

def datetime_timestamp(year, month, day, hour = 0, min = 0, second = 0):
    """
    Milliseconds Timestamp | UTC +8
    """
    time = datetime(year, month, day, hour, min, second).timestamp()
    return int(time) * 1000

def get_klines(symbol: str, interval, starttime=None, endtime=None, limit=1000):
    """
    Get Historical Klines from Binance
    
    Parameters
    ----------
    symbol : list of str
    interval : str
        Time scale can be 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M
    starttime : int
        Timestamp
        
    Returns
    -------
    out : list
    
    """
    params = {"symbol": symbol,
              "interval": interval,
              "limit": limit}
    if starttime:
        params["startTime"] = starttime
    if endtime:
        params["endTime"] = endtime
    url = "https://api.binance.com/api/v3/klines"
    
    data = []
    
    while starttime <= endtime:
        parameter = "&".join(f"{key}={params[key]}" for key in params.keys())
        path = url + "?" + parameter
        kline = requests.get(path).json()
        print(datetime.fromtimestamp(kline[0][0] / 1000), datetime.fromtimestamp(kline[-1][0] / 1000), len(kline))
        data += kline
        starttime = kline[-1][0] + 1
        params["startTime"] = starttime
        
    print("------", symbol, "------", datetime.fromtimestamp(data[0][0] / 1000), "-", datetime.fromtimestamp(data[-1][0] / 1000))    

    return data

def get_price_data(symbol, interval, start_time, end_time):
    column_name = ["Open time", "Open", "High", "Low", "Close", "Volume", "Close time", "Quote asset volume", 
                   "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"]
    data = pd.DataFrame(get_klines(symbol, interval, start_time, end_time), columns = column_name)
    return data

