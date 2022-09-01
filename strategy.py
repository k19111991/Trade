import numpy as np
import pandas as pd
import indicators as ta

"""
Trading Strategy
"""

def ketlner(data, paras: dict):
    """ 
    Ketlner channel 
    
    """
    atr = ta.ATR(data.High, data.Low, data.Close, num = paras["num"])
    up = ta.EMA(data.Close, paras["num"]) + paras["ratio"] * atr
    dn = ta.EMA(data.Close, paras["num"]) - paras["ratio"] * atr
    long = np.where(data.Close > up, 1, 0)
    short = np.where(data.Close < dn, -1, 0)
    
    # entry
    signal = pd.Series(long + short)
    
    # exit
    exit = pd.DataFrame(0, index = range(len(signal)), columns = ["exit"])
    
    return signal, exit