import numpy as np
import pandas as pd

class Backtest():
    def __init__(self, data, strategy, parameter, commission = 0.004, capital = 100000, riskfree_rate = 0.01):
        self.df = data.copy()
        self.strategy = strategy
        self.parameter = parameter
        self.summary = {}
        self.trade_list = []
        self.commission = commission
        self.capital = capital
        self.rate = riskfree_rate
        self.trade_cost = 0
    def get_position(self, entry, exit = pd.DataFrame([])):
        """
        Get Position
        
        Parameters
        ----------
        entry: entry signal
        exit: exit signal 
        """
        if exit.empty:
            exit = pd.DataFrame(0, index = range(len(entry)), columns = ["exit"])
        position = entry.copy()
        for i in range(1, len(entry)):
            position.iloc[i] = (entry.iloc[i] if entry.iloc[i] else position.iloc[i - 1]) * (exit.iloc[i] == 0)
        position = position.shift(1)
        return position.fillna(0)
    
    def strategy_performance(self):
        """
        Calculate Strategy performance
        """
        self.df["Entry"], self.df["Exit"] = self.strategy(self.df, self.parameter)
        self.df["Position"] = self.get_position(self.df.Entry, self.df.Exit)
        self.df["PnL"] = ((self.df.Close - self.df.Close.shift(1)) * self.df.Position).cumsum()
        self.df[["Equity_long", "Equity_short", "Equity"]] = pd.DataFrame(self.capital, index = range(len(self.df)), columns = ["l", "s", "all"])
        self.df[["Run_up", "Drawdown"]] = pd.DataFrame(0, index = range(len(self.df)), columns = ["r", "d"])        
        self.trade_list = [] # type, quantity, entry_time, entry_price, exit_time, exit_price, profit, profit_cum, entry_high, entry_low, MaxDrawdown
        entry_info = [] # position, entry_time, entry_price, entry_high, entry_low
        equity_max, equity_min = self.capital, self.capital
        trade_commission = [0, 0, 0] # Equity, Equity long, Equity short
        profit, profit_cum = 0, 0
        
        for i in range(1, len(self.df)):
            # Position != 0
            if self.df.Position[i]:
                # first entry
                if self.df.Position[i - 1] == 0:
                    entry_info.append([self.df.Position[i], self.df.Date[i], self.df.Close[i - 1], self.df.High[i], self.df.Low[i]])                    
                    self.trade_cost += abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission
                    trade_commission = [abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission, 
                                        abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission if self.df.Position[i] > 0 else 0,                                
                                        abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission if self.df.Position[i] < 0 else 0]
                   
                # same sign
                elif self.df.Position[i - 1] * self.df.Position[i] > 0:
                    # raise quantity
                    if abs(self.df.Position[i]) > abs(self.df.Position[i - 1]):
                        entry_info.append([(self.df.Position[i] - self.df.Position[i - 1]), self.df.Date[i], self.df.Close[i - 1], self.df.High[i], self.df.Low[i]])
                        self.trade_cost += abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                        trade_commission = [abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission,                                      
                                            abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if (self.df.Position[i] - self.df.Position[i - 1]) > 0 else 0, 
                                            abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if (self.df.Position[i] - self.df.Position[i - 1]) < 0 else 0]
                    # partial exit ||| todo
                    elif abs(self.df.Position[i]) < abs(self.df.Position[i - 1]):
                        self.trade_list.append()
                
                # opposite position 
                else:
                    for entry in entry_info:
                        profit = (self.df.Close[i - 1] - entry[2]) * entry[0] - (self.df.Close[i - 1] + entry[2]) * self.commission * abs(entry[0])
                        profit_cum += profit
                        self.trade_list.append((np.sign(entry[0]), abs(entry[0]), entry[1], entry[2], self.df.Date[i], self.df.Close[i - 1], profit, profit_cum, entry[3], entry[4], 
                                                min(0, (entry[4] - entry[2] if entry[0] > 0 else entry[3] - entry[2]) * entry[0]) - (self.df.Close[i - 1] + entry[2]) * self.commission * abs(entry[0])))
                    entry_info = []
                    entry_info.append([self.df.Position[i], self.df.Date[i], self.df.Close[i - 1], self.df.High[i], self.df.Low[i]])
                    self.trade_cost += abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                    trade_commission = [abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission,                                  
                                        abs(self.df.Position[i] if self.df.Position[i] > 0 else self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission, 
                                        abs(self.df.Position[i] if self.df.Position[i] < 0 else self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission]
               
                # calculate all 
                equity_change = self.df.Position[i] * (self.df.Close[i] - self.df.Close[i - 1])
                self.df.loc[i, "Equity_long"] = self.df.Equity_long[i - 1] + (equity_change if self.df.Position[i] > 0 else 0) - trade_commission[1]
                self.df.loc[i, "Equity_short"] = self.df.Equity_short[i - 1] + (equity_change if self.df.Position[i] < 0 else 0) - trade_commission[2]
                self.df.loc[i, "Equity"] = self.df.Equity[i - 1] + equity_change - trade_commission[0]
                trade_commission = [0, 0, 0]
                equity_max = max(equity_max, self.df.Equity[i])
                equity_min = min(equity_min, self.df.Equity[i])
                self.df.loc[i, "Run_up"] = self.df.Equity[i] - equity_min
                self.df.loc[i, "Drawdown"] = self.df.Equity[i] - equity_max
                for entry in entry_info:
                    entry[3] = max(self.df.High[i], entry[3])
                    entry[4] = min(self.df.Low[i], entry[4])
               
            # Position == 0
            else: 
                if self.df.Position[i - 1]:
                    for entry in entry_info:
                        profit = (self.df.Close[i - 1] - entry[2]) * entry[0] - (self.df.Close[i - 1] + entry[2]) * self.commission * abs(entry[0])
                        profit_cum += profit
                        self.trade_list.append((np.sign(entry[0]), abs(entry[0]), entry[1], entry[2], self.df.Date[i], self.df.Close[i - 1], profit, profit_cum, entry[3], entry[4], 
                                                min(0, (entry[4] - entry[2] if entry[0] > 0 else entry[3] - entry[2]) * entry[0]) - (self.df.Close[i - 1] + entry[2]) * self.commission * abs(entry[0])))
                    entry_info = []
                    self.trade_cost += abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                    self.df.loc[i, "Equity"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                    self.df.loc[i, "Equity_long"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if self.df.Position[i - 1] > 0 else 0
                    self.df.loc[i, "Equity_short"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if self.df.Position[i - 1] < 0 else 0
                self.df.loc[i, ["Equity_long", "Equity_short", "Equity", "Run_up", "Drawdown"]] = self.df.loc[i - 1, ["Equity_long", "Equity_short", "Equity", "Run_up", "Drawdown"]]
        # entry_info isn't empty on last day
        if entry_info:
            for entry in entry_info:
                profit = (self.df.Close[i] - entry[2]) * entry[0] - (self.df.Close[i] + entry[2]) * self.commission * abs(entry[0])
                profit_cum += profit
                self.trade_list.append((np.sign(entry[0]), abs(entry[0]), entry[1], entry[2], self.df.Date[i], self.df.Close[i], profit, profit_cum, entry[3], entry[4], 
                                        min(0, (entry[4] - entry[2] if entry[0] > 0 else entry[3] - entry[2]) * entry[0]) -  - (self.df.Close[i] + entry[2]) * self.commission * abs(entry[0])))
            entry_info = []
            self.trade_cost += abs(self.df.Position[i]) * self.df.Close[i] * self.commission
            self.df.loc[i, "Equity"] -= abs(self.df.Position[i]) * self.df.Close[i] * self.commission
            self.df.loc[i, "Equity_long"] -= abs(self.df.Position[i]) * self.df.Close[i] * self.commission if self.df.Position[i] > 0 else 0
            self.df.loc[i, "Equity_short"] -= abs(self.df.Position[i]) * self.df.Close[i] * self.commission if self.df.Position[i] < 0 else 0
        self.trade_list = pd.DataFrame(self.trade_list, columns = ["Type", "Quantity", "EntryTime", "EntryPrice", "ExitTime", "ExitPrice", 
                                                                   "Profit", "ProfitCum", "EntryHigh", "EntryLow", "Drawdown"])
        self.trade_list["MFE"] = pd.concat([(self.trade_list.EntryHigh - self.trade_list.EntryPrice) * self.trade_list.Type, (self.trade_list.EntryLow - self.trade_list.EntryPrice) * self.trade_list.Type], axis = 1).max(axis = 1)
        self.trade_list["MAE"] = pd.concat([(self.trade_list.EntryHigh - self.trade_list.EntryPrice) * self.trade_list.Type, (self.trade_list.EntryLow - self.trade_list.EntryPrice) * self.trade_list.Type], axis = 1).min(axis = 1)
        self.trade_list["Size"] = self.trade_list.Type * self.trade_list.Quantity
        self.summary = self.trade_summary(self.df, self.trade_list)
        
        return self.summary
    
    def trade_summary(self, data, tradelist):
        """
        Strategy Performance Summary
        """
        summary = {}
        summary["Net Profit"] = data.Equity.iloc[-1] - self.capital
        summary["Gross Profit"] = tradelist.Profit[tradelist.Profit > 0].sum()
        summary["Gross Loss"] = tradelist.Profit[tradelist.Profit <= 0].sum()
        summary["Commission"] = self.trade_cost
        summary["Max Drawdown"] = data.Drawdown.min()
        summary["Max Drawdown Date"] = str(data.Date[data.Drawdown == data.Drawdown.min()].values[0])
        summary["Profit Factor"] = summary["Gross Profit"] / -summary["Gross Loss"]
        summary["Win Rate"] = (tradelist.Profit > 0).sum() / len(tradelist)
        # Not correct, need to  annualize the return and standard deviation
        summary["Sharpe Ratio"] = (tradelist.Profit.mean() - self.rate) / tradelist.Profit.std()
        summary["Sortino Ratio"] = (tradelist.Profit.mean() - self.rate) / tradelist.Profit[tradelist.Profit <= 0].std()
        summary["Calmar Ratio"] = tradelist.Profit.mean() / data.Drawdown.min()
        
        return summary

    def plot(self, ta_list = []): # Equity curve, MAE / profit, drawdown, MAE / trade count, 
        None
        
    def technical_analysis(self): #, ta = [[strategy.ketlner, para],]): # plot ta and OHLC graph
        None
        
    def optimization(self):
        None
        