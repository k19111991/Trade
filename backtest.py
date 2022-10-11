import numpy as np
import pandas as pd
from bokeh.plotting import figure, show
from bokeh.layouts import column, gridplot
from bokeh.io import output_notebook, curdoc
from bokeh.palettes import Spectral, Dark2, RdYlBu, Viridis, Category10
from bokeh.models import HoverTool, ColumnDataSource, CustomJS, Legend, LinearAxis, Range1d

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
            ########################## position != 0 ##########################
            if self.df.Position[i]:
                ########################## first entry ##########################
                if self.df.Position[i - 1] == 0:
                    entry_info.append([self.df.Position[i], self.df.Date[i], self.df.Close[i - 1], self.df.High[i], self.df.Low[i]])                    
                    self.trade_cost += abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission
                    trade_commission = [abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission, 
                                        abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission if self.df.Position[i] > 0 else 0,                                
                                        abs(self.df.Position[i]) * self.df.Close[i - 1] * self.commission if self.df.Position[i] < 0 else 0]
                   
                ########################## same sign ##########################
                elif self.df.Position[i - 1] * self.df.Position[i] > 0:
                    ########################## raise quantity ##########################
                    if abs(self.df.Position[i]) > abs(self.df.Position[i - 1]):
                        entry_info.append([(self.df.Position[i] - self.df.Position[i - 1]), self.df.Date[i], self.df.Close[i - 1], self.df.High[i], self.df.Low[i]])
                        self.trade_cost += abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                        trade_commission = [abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission,                                      
                                            abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if (self.df.Position[i] - self.df.Position[i - 1]) > 0 else 0, 
                                            abs(self.df.Position[i] - self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if (self.df.Position[i] - self.df.Position[i - 1]) < 0 else 0]
                    ########################## partial exit ||| todo ##########################
                    elif abs(self.df.Position[i]) < abs(self.df.Position[i - 1]):
                        self.trade_list.append()
                
                ########################## opposite position ##########################
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
               
                ########################## calculate all ##########################
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
               
            ########################## Position == 0 ##########################
            else: 
                if self.df.Position[i - 1]:
                    for entry in entry_info:
                        profit = (self.df.Close[i - 1] - entry[2]) * entry[0] - (self.df.Close[i - 1] + entry[2]) * self.commission * abs(entry[0])
                        profit_cum += profit
                        self.trade_list.append((np.sign(entry[0]), abs(entry[0]), entry[1], entry[2], self.df.Date[i], self.df.Close[i - 1], profit, profit_cum, entry[3], entry[4], 
                                                min(0, (entry[4] - entry[2] if entry[0] > 0 else entry[3] - entry[2]) * entry[0]) - (self.df.Close[i - 1]) * self.commission * abs(entry[0])))
                    entry_info = []
                    self.trade_cost += abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                    self.df.loc[i, "Equity"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission
                    self.df.loc[i, "Equity_long"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if self.df.Position[i - 1] > 0 else 0
                    self.df.loc[i, "Equity_short"] -= abs(self.df.Position[i - 1]) * self.df.Close[i - 1] * self.commission if self.df.Position[i - 1] < 0 else 0
                self.df.loc[i, ["Equity_long", "Equity_short", "Equity", "Run_up", "Drawdown"]] = self.df.loc[i - 1, ["Equity_long", "Equity_short", "Equity", "Run_up", "Drawdown"]]
        ########################## entry_info isn't empty on last day ##########################
        if entry_info:
            for entry in entry_info:
                profit = (self.df.Close[i] - entry[2]) * entry[0] - (self.df.Close[i] + entry[2]) * self.commission * abs(entry[0])
                profit_cum += profit
                self.trade_list.append((np.sign(entry[0]), abs(entry[0]), entry[1], entry[2], self.df.Date[i], self.df.Close[i], profit, profit_cum, entry[3], entry[4], 
                                        min(0, ((entry[4] - entry[2]) if entry[0] > 0 else (entry[3] - entry[2])) * entry[0]) - (self.df.Close[i] + entry[2]) * self.commission * abs(entry[0])))
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
        ########################## Not correct, need to  annualize the return and standard deviation ##########################
        summary["Sharpe Ratio"] = (tradelist.Profit.mean() - self.rate) / tradelist.Profit.std()
        summary["Sortino Ratio"] = (tradelist.Profit.mean() - self.rate) / tradelist.Profit[tradelist.Profit <= 0].std()
        summary["Calmar Ratio"] = tradelist.Profit.mean() / data.Drawdown.min()
        
        return summary

    def plot(self, ta_list = []): # plot ta and OHLC graph
        """
        Charts graph, Equity graph and Profit/Loss graph
        """
        ########################## theme ##########################
        curdoc().theme = 'contrast'

        ########################## set figure ##########################
        df = self.df.copy()
        trade_list = self.trade_list.copy()
        df["index"] = df.index
        symbol = "BTCUSDT_15m"
        title = symbol + " / " + self.strategy.__name__
        y_p_start, y_p_end = df["Close"].min() * 0.95, df["Close"].max() * 1.05
        y_e_start, y_e_end = df[["Equity", "Equity_long", "Equity_short"]].min().min() * 0.995, df[["Equity", "Equity_long","Equity_short"]].max().max() * 1.005
        y_t_start, y_t_end = trade_list.Drawdown.min() * 1.2, trade_list.Profit.max() * 1.1
        w = (df["index"].iloc[1] - df["index"].iloc[0]) * 0.8 

        p_price  = figure(title = title, y_range = (y_p_start, y_p_end), sizing_mode = "stretch_width", plot_width = 1000, 
                          plot_height = 500, toolbar_location = "above", y_axis_label = "Price", x_axis_type = "datetime", 
                          tools = ["xpan, xwheel_zoom, xbox_zoom, reset, save"], active_scroll = "xwheel_zoom", 
                          background_fill_alpha = 0.9)
        p_equity = figure(x_range = p_price.x_range, y_range = (y_e_start, y_e_end), sizing_mode = "stretch_width", 
                          toolbar_location = None, y_axis_label = "Equity", x_axis_type = "datetime", plot_height = 250, 
                          tools = ["xpan, xwheel_zoom, xbox_zoom, reset, save"], active_scroll = "xwheel_zoom", 
                          background_fill_alpha = 0.9)
        p_trade    = figure(x_range = p_price.x_range, y_range = (y_t_start, y_t_end), sizing_mode = "stretch_width",
                          toolbar_location = None, y_axis_label = "Profit / Drawdown", plot_height = 250, 
                          tools = ["xpan, xwheel_zoom, xbox_zoom, reset, save"], active_scroll = "xwheel_zoom",
                          background_fill_alpha = 0.9) 

        hover_price_items = [("Date", "@Date{%Y-%m-%d %H:%M:%S}"), ("O", "@Open{0.0[00000]}"), ("H", "@High{0.0[00000]}"), 
                             ("L", "@Low{0.0[00000]}"), ("C", "@Close{0.0[00000]}"), ("Vol", "@Volume{0.0[00000]}")]
        hover_equity_items = [("Date", "@Date{%Y-%m-%d %H:%M:%S}"), ("Equity", "@Equity{0.0[00000]}"), 
                              ("Equity_Long", "@Equity_long{0.0[00000]}"), ("Equity_Short", "@Equity_short{0.0[00000]}"), 
                              ("Drawdown", "@Drawdown{0.0[00000]}")]
        hover_trade_items = [("Date", "@ExitTime{%Y-%m-%d %H:%M:%S}"), ("Size", "@Size"), ("PNL", "@Profit{0.0[00000]}"), 
                             ("Drawdown", "@Drawdown{0.0[00000]}")]

        ########################## p_price render ##########################
            # OHLC graph
        df_source = ColumnDataSource(df)
        inc_source = ColumnDataSource(df[["index", "Open", "High", "Low", "Close"]][df.Close > df.Open])
        dec_source = ColumnDataSource(df[["index", "Open", "High", "Low", "Close"]][df.Close <= df.Open])
        p_price.segment("index", "High", "index", "Low", color = "#728a7a", source = inc_source)
        p_price.segment("index", "High", "index", "Low", color = "#9e3f3b", source = dec_source)
        p_price.vbar("index", w, "Open", "Close", fill_color = "#728a7a", line_color = "#728a7a", source = inc_source)
        p_price.vbar("index", w, "Open", "Close", fill_color = "#9e3f3b", line_color = "#9e3f3b", source = dec_source)
        p_price.xaxis.visible = False
        r_price_for_hover = p_price.line(x = "index", y = "Close", line_width = 2, color = "#000000", alpha = 0, source = df_source)
            # set twinx volumn
        y_vol_start, y_vol_end = df.Volume.min() * 0.95, df.Volume.max() * 2 # 
        p_price.extra_y_ranges = {"vol": Range1d(y_vol_start, y_vol_end)}
        r_price_volume = p_price.vbar("index", w, "Volume", y_range_name = "vol", color = "#586d80", alpha = 0.8, source = df_source)
        p_price.add_layout(LinearAxis(y_range_name="vol" ,axis_label="Volume"), 'right')    
            # set ta line
        ta_legend_item = [("Volume", [r_price_volume])]
        if ta_list:
            for ta_name, color in zip(ta_list, Category10[5 if len(ta_list) < 3 else len(ta_list)]): 
                ta_line = p_price.line(x = "index", y = ta_name, line_width = 1.5, color = color, alpha = 0.7, source = df_source)
                ta_legend_item.append((ta_name, [ta_line]))
                hover_price_items.append((ta_name, "@" + ta_name + "{0.0[00000]}"))
        legend_price = Legend(items = ta_legend_item, label_text_color = "black", background_fill_alpha = 0.02)
        p_price.add_layout(legend_price, "right")
        # todo: add entry and exit

        ########################## p_equity render ##########################
            # equity graph
        df["Equity_pos"] = df.Equity.apply(lambda x: self.capital if x < self.capital else x)
        df["Equity_neg"] = df.Equity.apply(lambda x: self.capital if x >= self.capital else x)
        equity_pos_source = ColumnDataSource(df[["index", "Equity_pos"]])
        equity_neg_source = ColumnDataSource(df[["index", "Equity_neg"]])
        equity_legend_item = []
        r_equity_capital = p_equity.line(x = "index", y = self.capital, line_width = 2.5, color = "#9da49d", alpha = 0.5, source = df_source)
        r_equity_long  = p_equity.line(x = "index", y = "Equity_long", line_width = 2, color = "#4c5445", alpha = 0.7, source = df_source)
        r_equity_short = p_equity.line(x = "index", y = "Equity_short", line_width = 2, color = "#976666", alpha = 0.7, source = df_source)
        r_equity_total_win = p_equity.line(x = "index", y = "Equity_pos", line_width = 1.5, color = "darkseagreen", alpha = 0.7, source = equity_pos_source)
        r_equity_total_loss = p_equity.line(x = "index", y = "Equity_neg", line_width = 1.5, color = "#e1aa8d", alpha = 0.7, source = equity_neg_source)
        r_equity_total_win_a = p_equity.varea(x = "index", y1 = "Equity_pos", y2 = self.capital, color = "darkseagreen", alpha = 0.3, source = equity_pos_source)
        r_equity_total_loss_a = p_equity.varea(x = "index", y1 = "Equity_neg", y2 = self.capital, color = "#e1aa8d", alpha = 0.2, source = equity_neg_source)

            # set twinx drawdown
        y_dd_start, y_dd_end = (y_e_start - df.Equity.max()) * 1.1, df.Drawdown.max() # 
        p_equity.extra_y_ranges = {"mdd": Range1d(y_dd_start, y_dd_end)}
        r_equity_dd = p_equity.line(x = "index", y = "Drawdown", line_width = 1.5, color = "indianred", alpha = 0.7, source = df_source, y_range_name="mdd")
        r_equity_dd_a = p_equity.varea(x = "index", y1 = "Drawdown", y2 = df.Drawdown.max(), color = "indianred", alpha = 0.3, source = df_source, y_range_name="mdd")
        p_equity.add_layout(LinearAxis(y_range_name="mdd" ,axis_label="Max Drawdown"), 'right') 

            # set legend
        equity_legend_item = [("Equity", [r_equity_total_win, r_equity_total_loss, r_equity_total_win_a, r_equity_total_loss_a]), 
                              ("Max Drawdown", [r_equity_dd, r_equity_dd_a]), 
                              ("Equity long", [r_equity_long]), ("Equity short", [r_equity_short])]
        legend_equity = Legend(items = equity_legend_item, label_text_color = "black", background_fill_alpha = 0.02)
        p_equity.add_layout(legend_equity, "right")
        r_equity_long.visible = False
        r_equity_short.visible = False
        p_equity.xaxis.visible = False
        p_equity.yaxis.formatter.use_scientific = False

        ########################## p_trade render ##########################
        trade_list["index"] = [df.index[df.Date == exit][0] for exit in trade_list.ExitTime]
        trade_list["entry_index"] = [df.index[df.Date == entry][0] for entry in trade_list.EntryTime]
        trade_list["radius"] = ((trade_list.Profit.abs()) / trade_list.Profit.abs().max()) * 5 + 10 # profit% |todo size
        profit_pos_source = ColumnDataSource(trade_list[trade_list.Profit > 0])
        profit_neg_source = ColumnDataSource(trade_list[trade_list.Profit <= 0])
        r_trade_long_win = p_trade.triangle("index", "Profit", "radius", fill_color = "darkseagreen", line_alpha = 0, 
                                            source = ColumnDataSource(trade_list[(trade_list.Profit > 0) & (trade_list.Type == 1)]))
        r_trade_long_loss = p_trade.triangle("index", "Profit", "radius", fill_color = "indianred", line_alpha = 0, 
                                             source = ColumnDataSource(trade_list[(trade_list.Profit <= 0) & (trade_list.Type == 1)]))
        r_trade_short_win = p_trade.inverted_triangle("index", "Profit", "radius", fill_color = "darkseagreen", line_alpha = 0,
                                                      source = ColumnDataSource(trade_list[(trade_list.Profit > 0) & (trade_list.Type == -1)]))
        r_trade_short_loss = p_trade.inverted_triangle("index", "Profit", "radius", fill_color = "indianred", line_alpha = 0,
                                                       source = ColumnDataSource(trade_list[(trade_list.Profit <= 0) & (trade_list.Type == -1)]))
        r_trade_win_dd = p_trade.vbar("index", 3 * w, "Drawdown", "Profit", fill_color = "darkseagreen", fill_alpha = 0.5, line_alpha = 0, source = profit_pos_source)
        r_trade_loss_dd = p_trade.vbar("index", 3 * w, "Drawdown", "Profit", fill_color = "indianred", fill_alpha = 0.5, line_alpha = 0, source = profit_neg_source)
        r_trade_for_hover = p_trade.circle("index", "Profit", size = "radius", fill_alpha = 0, line_alpha = 0, source = ColumnDataSource(trade_list))

            # set legend
        trade_legend_item = [("Win trade", [r_trade_long_win, r_trade_short_win]), 
                              ("Loss trade", [r_trade_long_loss, r_trade_short_loss]), 
                              ("Drawdown", [r_trade_win_dd, r_trade_loss_dd])]
        legend_trade = Legend(items = trade_legend_item, label_text_color = "black", background_fill_alpha = 0.02)
        p_trade.add_layout(legend_trade, "right")
        r_trade_win_dd.visible = False
        r_trade_loss_dd.visible = False

        ########################## set hover ##########################
        hover_price_tooltips = """<strong><pre style = "color: rgba(255, 255, 255 ,0.7);"><span style = "color: #ae8977;">""" + \
                """\n<span style = "color: #ae8977;">""".join(["</span>: ".join(item) for item in hover_price_items]) + "</pre></strong>"
        hover_equity_tooltips = """<strong><pre style = "color: rgba(255, 255, 255 ,0.7);"><span style = "color: #ae8977;">""" + \
                """\n<span style = "color: #ae8977;">""".join(["</span>: ".join(item) for item in hover_equity_items]) + "</pre></strong>"
        hover_trade_tooltips = """<strong><pre style = "color: rgba(255, 255, 255 ,0.7);"><span style = "color: #ae8977;">""" + \
                """\n<span style = "color: #ae8977;">""".join(["</span>: ".join(item) for item in hover_trade_items]) + "</pre></strong>"

        hover_price = HoverTool(tooltips = hover_price_tooltips, formatters={"@Date": "datetime"}, mode="vline", show_arrow = False)
        hover_equity = HoverTool(tooltips = hover_equity_tooltips, formatters={"@Date": "datetime"}, mode="vline", show_arrow = False)
        hover_trade = HoverTool(tooltips = hover_trade_tooltips, formatters={"@ExitTime": "datetime"}, mode="vline", show_arrow = False)

        callback_hover = CustomJS(args = {'p': p_price}, code = """
                                        var tooltips = document.getElementsByClassName("bk-tooltip");
                                        for (var i = 0; i < tooltips.length; i++) {
                                            tooltips[i].style.top = '25px'; 
                                            tooltips[i].style.left = '80px'; 
                                            tooltips[i].style["backgroundColor"] = "rgba(0, 0, 0, 0.01)";
                                        tooltips[i].style["border"] = "0px";} """)

        ########################## auto-adjust y_range ##########################
        y_range_callback = """
        if (!window._bt_scale_range) {
            window._bt_scale_range = function (range, min, max, pad) {
                "use strict";
                if (min !== Infinity && max !== -Infinity) {
                    pad = pad ? (max - min) * .03 : 0;
                    range.start = min - pad;
                    range.end = max + pad;
                } else console.error('backtesting: scale range error:', min, max, range);};}
            /**
             * @variable cb_obj `fig_ohlc.x_range`.
             * @variable source `ColumnDataSource`
             */
            "use strict";
            let i = Math.max(Math.floor(p.x_range.start), 0),
                j = Math.min(Math.ceil(p.x_range.end), source.data['High'].length);
            let max = Math.max.apply(null, source.data['High'].slice(i, j)),
                min = Math.min.apply(null, source.data['Low'].slice(i, j));
            _bt_scale_range(p.y_range, min, max, true);
            p.x_range.start = Math.max(Math.floor(p.x_range.start), Math.floor(- source.data['High'].length * 0.01));
            p.x_range.end = Math.min(Math.ceil(p.x_range.end), Math.floor(source.data['High'].length * 1.01));
        """
        p_price.x_range.js_on_change("start", CustomJS(args = dict(p = p_price, source = df_source), code = y_range_callback))
        p_price.y_range.js_on_change("end", CustomJS(args = dict(p = p_price, source = df_source), code = y_range_callback))

        # set legend & figure
        hover_price.renderers = [r_price_for_hover]
        hover_equity.renderers = [r_equity_capital]
        hover_trade.renderers = [r_trade_for_hover]
        for fig, hov in zip([p_price, p_equity, p_trade], [hover_price, hover_equity, hover_trade]):
            fig.tools.append(hov)
            hov.callback = callback_hover
            fig.grid.grid_line_alpha = 0.05
            fig.legend.click_policy = "hide"
            fig.legend.label_text_font_size = "8pt"
            fig.yaxis.axis_label_text_font_size = "10pt"
            fig.axis.axis_label_text_font_style = "bold"
            fig.yaxis.major_label_text_font_size = "8pt"
        p_trade.xaxis.major_label_overrides = {i: str(date).replace(" ", "\n") for i, date in enumerate(df["Date"])}
        p_trade.xaxis.major_label_text_font_size = "8pt"

        output_notebook()
        show(column(p_price, p_equity, p_trade))

    def plot_trade(self): # Equity curve, MAE / profit, drawdown, MAE / trade count, 
        trade_list = self.trade_list.copy()
        trade_source = ColumnDataSource(data = trade_list)
        trade_hover = [("Date", "@ExitTime{%Y-%m-%d %H:%M:%S}"), ("Size", "@Size"), ("PNL", "@Profit{0.0[00000]}"), 
                             ("MAE", "@MAE{0.0[00000]}"), ("MFE", "@MFE{0.0[00000]}")]
        trade_hover_tooltips = """<strong><pre style = "color: rgba(255, 255, 255 ,0.7);"><span style = "color: #ae8977;">""" + \
                """\n<span style = "color: #ae8977;">""".join(["</span>: ".join(item) for item in trade_hover]) + "</pre></strong>"
        hover_trade = HoverTool(tooltips = trade_hover_tooltips, formatters={"@ExitTime": "datetime"}, show_arrow = False)
        hover_trade_MAEMFE = HoverTool(tooltips = trade_hover_tooltips, formatters={"@ExitTime": "datetime"}, 
                                       show_arrow = False, mode = "vline")
        trade_tools = ["xpan, box_select, xwheel_zoom, reset, save", hover_trade]
        trade_tools_MAEMFE = ["xpan, box_select, xwheel_zoom, reset, save", hover_trade_MAEMFE]
        
        ########################## set figure ##########################
        p_MAEMFE = figure(title = "MAE & MFE", plot_width = 480, plot_height = 300, toolbar_location = "above",
                          y_axis_label = "MAE / MFE", x_axis_label = "Index", tools = trade_tools_MAEMFE,
                          active_scroll = "xwheel_zoom", background_fill_alpha = 0.9)
        p_MAE_MFE = figure(title = "MAE vs MFE", plot_width = 480, plot_height = 300, toolbar_location = "above", 
                           y_axis_label = "MFE", x_axis_label = "MAE",  tools = trade_tools,
                           active_scroll = "xwheel_zoom", background_fill_alpha = 0.9)
        p_MFE_PNL = figure(title = "MFE vs PNL", plot_width = 480, plot_height = 300, toolbar_location = "above",
                           y_axis_label = "MFE", x_axis_label = "PNL", tools = trade_tools,
                           active_scroll = "xwheel_zoom", background_fill_alpha = 0.9)
        p_MAE_PNL = figure(title = "MAE vs PNL", plot_width = 480, plot_height = 300, toolbar_location = "above",
                           y_axis_label = "MAE", x_axis_label = "PNL", tools = trade_tools, x_range = p_MFE_PNL.x_range,
                           active_scroll = "xwheel_zoom", background_fill_alpha = 0.9)

        ########################## set render ##########################
        r_MFE = p_MAEMFE.varea(x = "index", y1 = "MFE", y2 = 0, color = "#728a7a", source = trade_source)
        r_MAE = p_MAEMFE.varea(x = "index", y1 = "MAE", y2 = 0, color = "#9e3f3b", source = trade_source)
        r_Profit = p_MAEMFE.line(x = "index", y = "Profit", line_width = 1.5, color = "#c7986e", source = trade_source, muted_alpha = 0.1)
        p_MAE_MFE.circle('MAE', 'MFE', size = 5.5, source = trade_source, color = "#586d80", hover_color = "#b88461")
        p_MFE_PNL.circle('Profit', 'MFE', size = 5.5, source = trade_source, color = "darkseagreen", 
                         hover_color = "indianred", hover_alpha = 0.8)
        p_MAE_PNL.circle('Profit', 'MAE', size = 5.5, source = trade_source, color = "indianred", 
                         hover_color = "darkseagreen", hover_alpha = 0.8)
        trade_legend_item = [("Profit", [r_Profit]), ("MFE", [r_MFE]), ("MAE", [r_MAE])]
        legend_trade = Legend(items = trade_legend_item, label_text_color = "white", background_fill_alpha = 0.1, 
                              glyph_height = 8, glyph_width = 8, label_text_font_size = "8pt")
        p_MAEMFE.add_layout(legend_trade)
        p_MAEMFE.legend.location = "top_right"
        p_MAEMFE.legend.click_policy="mute"
        r_Profit.muted = True

        ########################## set legend & figure ##########################
        callback_hover = CustomJS(args = {'p': p_MAEMFE}, code = """
                                        var tooltips = document.getElementsByClassName("bk-tooltip");
                                        for (var i = 0; i < tooltips.length; i++) {
                                            tooltips[i].style.top = '25px'; 
                                            tooltips[i].style.left = '80px'; 
                                            tooltips[i].style["backgroundColor"] = "rgba(0, 0, 0, 0.01)";
                                        tooltips[i].style["border"] = "0px";} """)
        hover_trade.callback = callback_hover
        hover_trade_MAEMFE.callback = callback_hover

        for fig in [p_MAEMFE, p_MAE_MFE, p_MFE_PNL, p_MAE_PNL]:
            fig.grid.grid_line_alpha = 0.05
            fig.xaxis.axis_label_text_font_size = "9pt"    
            fig.yaxis.axis_label_text_font_size = "9pt"
            fig.axis.axis_label_text_font_style = "bold"
            fig.axis.major_label_text_font_size = "8pt"

        show(gridplot([[p_MAEMFE, p_MFE_PNL], [p_MAE_MFE, p_MAE_PNL]]))
        
    def technical_analysis(self, ): # price, technical lines,
        None
        
    def optimization(self):
        None
 
    def optimization_graph(self):
        None
        