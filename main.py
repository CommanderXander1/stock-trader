import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime as dt
import csv
import math
import finnhub as fh
import numpy as np
import math
import os
from selenium import webdriver
from selenium.webdriver.common import by



_debug = False


class Stock:
    marker = None
    def __init__(self, marker, name=marker):
        self.marker = marker
        self.name = name
        self.last_week_data = yf.download(marker, period="5d", interval="1d")
        self.multiple = True if len(marker) > 5 else False
        self.num_stocks = len(marker.split(" ")) if self.multiple else 1
        if _debug:
            self.save_csv()


    # calculate percent increase of a stock with the starting and ending value
    def percent_change(self, first, second):
        # # turns it from a series to a number
        if type(first) is list:
            first = first.iloc[0]
            second = second.iloc[0]
        increase = second - first
        return (increase/first)*100
    

    def trunc(self, num, numdigits):
        num *= math.pow(10, numdigits)
        num = math.trunc(num)
        return num / math.pow(10, numdigits)


    # returns the weekly percent change
    def weekly_change(self, stock):
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            return self.percent_change(open.iloc[0], close.iloc[len(close)-1])
        # handle one stock
        else:
            return self.percent_change(self.last_week_data.iloc[0, 3], self.last_week_data.iloc[4, 0])


    # returns the average daily percent change for the week
    def weekly_avg_change(self, stock):
        sum_change = 0
        # handle multiple stocks
        if self.multiple:
            open = self.last_week_data["Open", stock]
            close = self.last_week_data["Close", stock]
            for i in range(len(open)):
                sum_change += self.percent_change(open.iloc[i], close.iloc[i])
        # handle one stock
        else:
            for index, data in self.last_week_data.iterrows():
                sum_change += self.percent_change(data.iloc[3], data.iloc[0])
        return sum_change/5


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
        print("Weekly average change: " + str(self.trunc(self.weekly_avg_change(stock), 5)) + "%")
        print("Weekly change overall: " + str(self.trunc(self.weekly_change(stock), 5)) + "%")
        print("Change has been positive everyday: " + str(self.is_change_positive_everyday(stock)))
    

    def info_multiple(self):
        marker_list = self.marker.split(" ")
        for marker in marker_list:
            self.info(marker)


    def save_csv(self):
        self.last_week_data.to_csv(os.path.join(os.getcwd(), "output.csv"), index=False)



class Trader:
    def __init__(self, finnhub_api_key):
        client = fh.Client(api_key=finnhub_api_key)
        self.marker_list = [i['symbol'] for i in client.stock_symbols("US", currency="USD", mic="XNYS", security_type="Common Stock")]
        # self.marker_list = self.marker_list[:5000] # limits stocks to 5000
        # put markers together with a space in between each to create the string
        self.marker_string = "" 
        for marker in self.marker_list:
            self.marker_string += marker + " "
        self.Info = Stock(self.marker_string, "Trader Info")


    # threshold values are given as a float representing a percent
    def identify_top_stocks(self, quantity=5, daily_gain_threshold=1, weekly_gain_threshold=5, positive_everyday=True, stock_price_threshold=0):
        top_list = []
        for marker in self.marker_list:
            if not self.Info.filter(marker):
                if _debug:
                    print(f"{marker} disqualified by filter parameters")
                continue
            if self.Info.current_value(marker) < stock_price_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching price threshold")
                continue
            if self.Info.weekly_avg_change(marker) < daily_gain_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching daily gain threshold")
                continue
            if self.Info.weekly_change(marker) < weekly_gain_threshold:
                if _debug:
                    print(f"{marker} disqualified for not reaching weekly gain threshold")
                continue
            if positive_everyday and not self.Info.is_change_positive_everyday(marker):
                if _debug:
                    print(f"{marker} disqualified for not having positive change everyday")
                continue
            top_list.append({
                    "marker": marker,
                    "daily gain": self.Info.weekly_avg_change(marker), 
                    "weekly gain": self.Info.weekly_change(marker), 
                    "positive everyday": self.Info.is_change_positive_everyday(marker)
                    })
            print(f"{marker} added to list")
        # sorts based on highest daily gain
        top_list = sorted(top_list, key=lambda stock: stock['daily gain'], reverse=True)
        return top_list[:quantity]


def main():
    api_key = "d1v6n69r01qj71gjpgegd1v6n69r01qj71gjpgf0"
    # get list of top stocks
    # iterate through list and find stocks with most gain in last 5d
    # invest in 5 different stocks with 1/5 of the current balance
    # sell at end of day 
    # make run automatically and keep csv file with current investments

    trader = Trader(finnhub_api_key=api_key)
    print(trader.identify_top_stocks(positive_everyday=True, quantity=10, daily_gain_threshold=1, weekly_gain_threshold=5, stock_price_threshold=2))


if __name__ == "__main__":
    main()