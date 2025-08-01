import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import math
import finnhub as fh
import os
import time
import json
import robin_stocks.robinhood as rh
from datetime import datetime as dt
import datetime
import pytz


_debug = False


class Utils:
    def __init__(self):
        pass


    # calculate percent increase of a stock with the starting and ending value
    def percent_change(self, first, second):
        # # turns it from a series to a number
        if type(first) is list:
            first = first.iloc[0]
            second = second.iloc[0]
        increase = second - first
        return (increase/first)*100
    

    def trunc(self, num, numdigits):
        # not sure if this is necessary but it wasnt working for some reason
        num = float(num)
        num *= math.pow(10, numdigits)
        num = math.trunc(num)
        return num / math.pow(10, numdigits)



class Stock:
    marker = None
    def __init__(self, marker, name=marker):
        self.Util = Utils()
        self.marker = marker
        self.name = name
        self.last_week_data = yf.download(marker, period="5d", interval="1d")
        self.multiple = True if len(marker) > 5 else False
        self.num_stocks = len(marker.split(" ")) if self.multiple else 1
        if _debug:
            self.save_csv()


    # returns the weekly percent change
    def weekly_change(self, stock):
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            return self.Util.percent_change(open.iloc[0], close.iloc[len(close)-1])
        # handle one stock
        else:
            return self.Util.percent_change(self.last_week_data.iloc[0, 3], self.last_week_data.iloc[4, 0])


    # returns the average daily percent change for the week
    def daily_avg_change(self, stock):
        sum_change = 0
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            for i in range(len(open)):
                sum_change += self.Util.percent_change(open.iloc[i], close.iloc[i])
        # handle one stock
        else:
            for index, data in self.last_week_data.iterrows():
                sum_change += self.Util.percent_change(data.iloc[3], data.iloc[0])
        return sum_change/5
    

    def lowest_daily_change(self, stock):
        daily_change = []
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            for i in range(len(open)):
                daily_change.append(self.Util.percent_change(open.iloc[i], close.iloc[i]))
        # handle one stock
        else:
            for index, data in self.last_week_data.iterrows():
                daily_change.append(self.Util.percent_change(data.iloc[3], data.iloc[0]))
        return sorted(daily_change)[0]


    # returns if the percent change was positive everyday for the past week
    def is_change_positive_everyday(self, stock):
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            for i in range(len(open)):
                if close.iloc[i] - open.iloc[i] < 0:
                    return False
        # handle one stock
        else:
            for index, data in self.last_week_data.iterrows():
                if data.iloc[0] - data.iloc[3] < 0:
                    return False 
        return True


    # identify stocks that are being traded
    def filter(self, stock):
        if self.weekly_change(stock) == 0 or self.weekly_change(stock) == None or math.isnan(self.weekly_change(stock)):
            return False
        return True
    

    # return most recent value
    def current_value(self, stock):
        return self.last_week_data["Close", stock].iloc[-1]


    # prints out info for the week
    def info(self, stock=marker):
        print(self.last_week_data)
        print("Weekly average change: " + str(self.Util.trunc(self.daily_avg_change(stock), 5)) + "%")
        print("Weekly change overall: " + str(self.Util.trunc(self.weekly_change(stock), 5)) + "%")
        print("Lowest daily change: " + str(self.Util.trunc(self.lowest_daily_change(stock), 5) + "%"))
        print("Change has been positive everyday: " + str(self.is_change_positive_everyday(stock)))
    

    def info_multiple(self):
        marker_list = self.marker.split(" ")
        for marker in marker_list:
            self.info(marker)


    def save_csv(self):
        self.last_week_data.to_csv(os.path.join(os.getcwd(), "data.csv"), index=False)



class Trader:
    def __init__(self):
        self.Json = Info()
        self.Util = Utils()
        client = fh.Client(api_key=self.Json.get_finnhub_api_key())
        self.marker_list = [i['symbol'] for i in client.stock_symbols("US", currency="USD", mic="XNYS", security_type="Common Stock")]
        # self.marker_list = self.marker_list[:5000] # limits stocks to 5000
        # puts markers together with a space in between each to create the string
        self.marker_string = "" 
        for marker in self.marker_list:
            self.marker_string += marker + " "


    # threshold values are given as a float representing a percent
    def identify_top_stocks(self, quantity=5, avg_daily_gain_threshold=1, weekly_gain_threshold=5, lowest_daily_gain_threshold=0.2, positive_everyday=True, stock_price_threshold=0):
        Info = Stock(self.marker_string, "Trader Info")
        top_list = []
        for marker in self.marker_list:
            if not Info.filter(marker):
                if _debug:
                    print(f"{marker} disqualified by filter parameters")
                continue
            if Info.current_value(marker) <= stock_price_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching price threshold")
                continue
            if Info.daily_avg_change(marker) <= avg_daily_gain_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching daily gain threshold")
                continue
            if Info.weekly_change(marker) <= weekly_gain_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching weekly gain threshold")
                continue
            if Info.lowest_daily_change(marker) <= lowest_daily_gain_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching lowest daily gain threshold")
                continue
            if positive_everyday and not Info.is_change_positive_everyday(marker):
                if _debug:
                    print(f"{marker} disqualified for not having positive change everyday")
                continue
            top_list.append({
                    "marker": marker,
                    "daily gain": Info.daily_avg_change(marker), 
                    "weekly gain": Info.weekly_change(marker), 
                    "positive everyday": Info.is_change_positive_everyday(marker)
                    })
            print(f"{marker} added to list")
        # sorts based on highest daily gain
        top_list = sorted(top_list, key=lambda stock: stock['daily gain'], reverse=True)
        return top_list[:quantity]
    

    # if amount is -1, function will trade all available funds
    # percent gain to sell is the average percent rise to sell at, -1 means do not sell
    def auto_trade(self, amount=-1, percent_gain_to_sell=-1, quantity=5, avg_daily_gain_threshold=1, weekly_gain_threshold=5, lowest_daily_gain_threshold=0.2, positive_everyday=True, stock_price_threshold=0):
        API = RobinhoodAPI()
        while True:
            # during trading day and during week
            now = dt.now(tz=pytz.timezone("America/New_York"))
            print(now.time())
            if datetime.time(9,30) <= now.time() <= datetime.time(16) and now.isoweekday() < 6:
                print("active trading time")
                # buys if last trade was before today or never traded before
                if (self.Json.get_last_trade() is False) or (self.Json.get_last_trade() and (dt.strptime(self.Json.get_last_trade(), "%m/%d/%Y, %H:%M:%S").date() < now.date())):
                    # sells currently held stocks if there are any
                    if len(self.Json.get_updated_data()["current stocks"].keys()) > 0:
                        print("selling all")
                        self.sell_all(API=API)
                    print("buying all top stocks")
                    self.buy_top_stocks(API=API, amount=amount, quantity=quantity, avg_daily_gain_threshold=avg_daily_gain_threshold, weekly_gain_threshold=weekly_gain_threshold, lowest_daily_gain_threshold=lowest_daily_gain_threshold ,positive_everyday=positive_everyday, stock_price_threshold=stock_price_threshold)
                
                # sells if percent gain is above threshold
                if percent_gain_to_sell > 0:
                    for stock, info in self.Json.get_updated_data()["current stocks"].items():
                        if self.Util.percent_change(info["value"], info["shares"] * float(rh.get_latest_price(inputSymbols=stock)[0])) >= percent_gain_to_sell:
                            print(f"selling {stock} because of gain percent")
                            API.sell(marker=stock, amount=-1)

                # sells at end of day
                if now.time() >= datetime.time(15,55):
                    print("selling all at end of day")
                    self.sell_all(API=API)
            # checks in every minute
            time.sleep(60)


    def buy_top_stocks(self, API, amount, quantity, avg_daily_gain_threshold, weekly_gain_threshold, lowest_daily_gain_threshold, positive_everyday, stock_price_threshold):
        stocks = self.identify_top_stocks(quantity=quantity, avg_daily_gain_threshold=avg_daily_gain_threshold, weekly_gain_threshold=weekly_gain_threshold, lowest_daily_gain_threshold=lowest_daily_gain_threshold, positive_everyday=positive_everyday, stock_price_threshold=stock_price_threshold)
        withdrawable_amount = float(rh.profiles.load_portfolio_profile()["withdrawable_amount"])
        if amount < 0:
            amount = withdrawable_amount
        elif amount > withdrawable_amount:
            amount = withdrawable_amount
        for stock in stocks:
            try:
                API.buy(marker=stock["marker"], amount=amount/len(stocks))
                print(stock)
            except Exception as e:
                print(e)


    def sell_all(self, API, exclude=[]):
        for stock, info in self.Json.get_updated_data()["current stocks"].items():
            if stock not in exclude:
                API.sell(marker=stock, amount=-1)



class RobinhoodAPI:
    def __init__(self):
        self.Json = Info()
        self.Util = Utils()
        login_info = self.Json.get_robinhood_login()
        rh.login(login_info[0], login_info[1])
    

    def buy(self, marker, amount):
        latest_price = float(rh.get_latest_price(inputSymbols=marker)[0])
        # for some reason rh.get_latest_price and the account profile method returns the price as a list of strings
        shares = amount/latest_price
        info = rh.order_buy_market(symbol=marker, quantity=self.Util.trunc(shares, 4), timeInForce="gfd")
        print(info)
        self.Json.log_trade(type="buy", marker=marker, date=dt.now(tz=pytz.timezone("America/New_York")).strftime("%m/%d/%Y, %H:%M:%S"), shares=float(info["quantity"]), value=shares*latest_price)


    # may need to create try accept block around build holdings access incase trying to access stock dont have
    # if amount is -1, all shares will be sold
    def sell(self, marker, amount=-1):
        latest_price = float(rh.get_latest_price(inputSymbols=marker)[0])
        if amount < 0:
            # may need to change "quantity held", needs testing
            shares = float(rh.build_holdings()[marker]["quantity"])
        else:
            shares = amount/latest_price
        info = rh.order_sell_market(symbol=marker, quantity=self.Util.trunc(shares, 4), timeInForce="gfd")
        print(info)
        self.Json.log_trade(type="sell", marker=marker, date=dt.now(tz=pytz.timezone("America/New_York")).strftime("%m/%d/%Y, %H:%M:%S"), shares=float(info["quantity"]), value=shares*latest_price)



class Info:
    def __init__(self, file_path=None):
        self.Util = Utils()
        self.file = file_path or os.path.join(os.getcwd(), "info.json")
        self.data = self.get_updated_data()

    
    def get_robinhood_login(self):
        username = self.data["details"]["robinhood username"]
        password = self.data["details"]["robinhood password"]
        return [username, password]
    

    def get_finnhub_api_key(self):
        key = self.data["details"]["finnhub api key"]
        return key
    

    def log_trade(self, type, marker, date, shares, value):
        data = self.get_updated_data()

        stock_data = {
            "date": date,
            "shares": shares,
            "value": value,
        }

        if type == "buy":
            # add to data if its already present when buying
            if marker in data["current stocks"].keys():
                stock_data.update({
                    "shares": shares + data["current stocks"][marker]["shares"],
                    "value": float(rh.get_latest_price(inputSymbols=marker)[0])*(shares + data["current stocks"][marker]["shares"])
                })
            data["current stocks"][marker] = stock_data
            
        # modify data if its already present when selling
        elif type == "sell":
            # remove from currently owned stock list if all shares are sold
            # subtract 0.001 to share amount because math is rounded and may not be correct, so prevents having 0.00000001 shares in logbook
            if marker in data["current stocks"] and shares >= (data["current stocks"][marker]["shares"] - 0.001):
                data["current stocks"].pop(marker)
            elif marker in data["current stocks"]:
                stock_data.update({
                    "shares": data["current stocks"][marker]["shares"] - shares,
                    "value": float(rh.get_latest_price(inputSymbols=marker)[0])*(data["current stocks"][marker]["shares"] - shares)
                })
                data["current stocks"][marker] = stock_data
        
        trade_data = {
            "marker": marker,
            "shares": shares,
            "value": value
        }

        sell_data = {
            "percent change": None,
            "monetary change": None,
            "time held": None
        }

        if type == "sell":
            # iterate in reverse through the sales log dict
            for key in reversed(data["trade log"]["buy"].keys()):
                if data["trade log"]["buy"][key]["marker"] == marker:
                    sell_data.update({
                        "percent change": self.Util.percent_change(data["trade log"]["buy"][key]["value"], value),
                        "monetary change": value - data["trade log"]["buy"][key]["value"],
                        "time held": str(dt.strptime(date, "%m/%d/%Y, %H:%M:%S") - dt.strptime(key, "%m/%d/%Y, %H:%M:%S"))
                    })
                    break
            trade_data.update(sell_data)

        data["trade log"][type][date] = trade_data
        data["statistics"]["last trade"] = date
        self.update_data(data)


    def get_updated_data(self):
        with open(file=self.file, mode="r") as f:
            data = json.load(f)
        return data
    

    def update_data(self, data):
        with open(file=self.file, mode="w") as f:
            json.dump(data, f, indent=3)


    def clear_trade_log(self):
        data = self.get_updated_data()
        data["trade log"]["buy"] = {}
        data["trade log"]["sell"] = {}
        self.update_data(data)


    def get_last_trade(self):
        data = self.get_updated_data()
        if data["statistics"]["last trade"] != "":
            last_trade = data["statistics"]["last trade"]
            return last_trade
        else:
            return False
    

    def get_last_buy(self):
        data = self.get_updated_data()
        if len(data["trade log"]["buy"].keys()) > 0:
            last_buy = data["trade log"]["buy"].keys()[-1]
            return last_buy
        else:
            return False
    

    def get_last_sell(self):
        data = self.get_updated_data()
        if len(data["trade log"]["sell"].keys()) > 0:
            last_sell = data["trade log"]["sell"].keys()[-1]
            return last_sell
        else:
            return False



def main():
    trader = Trader()
    trader.auto_trade(amount=-1, percent_gain_to_sell=10, quantity=10, avg_daily_gain_threshold=1, weekly_gain_threshold=5, lowest_daily_gain_threshold=0.2, positive_everyday=True, stock_price_threshold=5)
    # print(trader.identify_top_stocks(avg_daily_gain_threshold=1, weekly_gain_threshold=5, lowest_daily_gain_threshold=0.2, stock_price_threshold=3))



if __name__ == "__main__":
    main()
