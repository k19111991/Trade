import numpy as np
import pandas as pd

"""
Technical Indicators
"""

def MA(close, num = 20):
    """
    Moving Average
    
    Parameters
    ----------
    close: price list
    num: lenth
    
    """
    
    return close.rolling(num).mean()

def EMA(close, num = 20, adjust = False, method = "span"):
    """
    Exponential Moving Average
    
    Parameters
    ----------
    close: price list
    num: lenth
    
    """
    if method == "span":
        return close.ewm(span = num, adjust = adjust).mean()
    else:
        return close.ewm(alpha = 1 / num, adjust = adjust).mean() 
    
def WMA(close, num = 20, adjust = False):
    """
    Weighted Moving Average
    
    Parameters
    ----------
    close: price list
    num: lenth
    
    """    
    weight = np.arange(1, num + 1) / (0.5 * num * (num + 1))
    dot = lambda x: np.dot(weight, x)
    close_r = close.rolling(num)
    
    return close_r.apply(dot)
    
def KD(high, low, close, num = 9, ratio = 1/3, num_slow = 10):
    """
    Stochastic Oscillator
    
    Parameters
    ----------
    high, low, close: price list
    num: lenth
    ratio: 
    num_slow: 
    
    """
    RSV = (close - low.rolling(num).min()) / (high.rolling(num).max() - low.rolling(num).min())
    K = RSV.ewm(alpha = ratio, adjust = False).mean()
    D = K.ewm(alpha = ratio, adjust = False).mean()
    D_slow = MA(D, num_slow)
    return K, D, D_slow

def RSI(close, num = 14):
    """
    Relative Strength Index
 
    Parameters
    ----------
    close: price list
    num: lenth 
    
    """
    def ema(x, sign = "p"):
        x = x[x >= 0] if sign == "p" else -x[x < 0]
        if x.empty:
            return 0
        else:
            return x.ewm(alpha = 1 / num, adjust = False).mean().iloc[-1]
    up = close.rolling(num).apply(ema, args = ("p", ))
    down = close.rolling(num).apply(ema, args = ("n", ))
    return up / (up + down)

def ATR(high, low, close, num = 14):
    """
    Average True Range
    
    Parameters
    ----------
    high, low, close: price list
    num: lenth
    
    """    
    p = pd.concat([high, low, close.shift(1)], axis=1, ignore_index=True)
    TR = p.max(axis=1) - p.min(axis=1)
    ATR = EMA(TR, num)
    return ATR

def ADX(high, low, close, num = 14):
    """
    Average Directional Movement Index
    
    Parameters
    ----------
    high, low, close: price list
    num: lenth
    
    """
    # Definition DI = DM / ATR
    up = high - high.shift(1)
    dn = low - low.shift(1)
    DM_p = ((up > dn) & (up > 0)) * up
    DM_n = ((dn > up) & (dn > 0)) * dn
    DI_p = EMA(DM_p, num)
    DI_n = EMA(DM_n, num)
    DX = (DI_p - DI_n).abs() / (DI_p + DI_n)
    ADX = EMA(DX, num)
    return ADX
    
"""Position Related""" 

def crossover():
    None

def crossunder():
    None
    
def entry_high(high, position):
    
    h = high.copy()
    for i in range(len(h)):
        if position[i]:
            h.iloc[i] = max(h.iloc[i], h.iloc[i - 1])
        else:
            h.iloc[i] = 0
    
    return h

def entry_low(low, position):
    
    l = low.copy()
    for i in range(len(l)):
        if position[i]:
            l.iloc[i] = min(l.iloc[i], l.iloc[i - 1])
        else:
            l.iloc[i] = 10**7
    
    return l

def tralling_stop(close, ):
    None