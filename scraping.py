from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import requests
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from user_agent import generate_user_agent
import nltk
from iexfinance.stocks import Stock, get_historical_data, get_historical_intraday
from datetime import datetime, timedelta
import base64
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import io
import re
import time 
import pandas as pd
import asyncio
import aiohttp



token = "Tpk_68eb4634611c4b09a0415877f28eaeda"

url = "https://finviz.com/quote.ashx?t="

def scrape(ticker):
    ticker_url = url + ticker
    req = Request(url=ticker_url, headers={'user-agent':generate_user_agent()})
    response = urlopen(req)

    soup = BeautifulSoup(response, features="lxml")
    return soup

def scrape_news(ticker):
    html = scrape(ticker)
    news_title_html = html.select("#news-table .news-link-left")
    news = []
    for i in range(len(news_title_html)):
        news.append(news_title_html[i].text)

    return news

def get_company_data(ticker):
    tick = Stock(ticker, token=token).get_quote()
    companyName = tick['companyName']
    latestPrice = tick['latestPrice']
    market = tick['primaryExchange']
    if(tick['isUSMarketOpen'] == False):
        isOpen = "Closed"
    else: 
        isOpen = "Open"

    return companyName, latestPrice, market, isOpen

def get_batch_data(tickers):
    batch = Stock(tickers,token=token)
    prices = batch.get_price()
    return prices

def get_historical_to_day(ticker):
    oneyear = datetime.now().date() - timedelta(days=365)
    return get_historical_data(ticker, start=oneyear, end=datetime.now().date(), output_format='pandas', token = token)

def plot_historical(ticker):
    data = get_historical_to_day(ticker)
    data_day = get_intraday(ticker)
    fig = Figure(figsize=(12,4))
    axis = fig.add_subplot(1, 2, 1)
    axis.set_title(ticker + " 1-year data")
    axis.set_xlabel("Date")
    axis.set_ylabel("Price")
    axis.grid()
    axis.plot(data['close'])
    axis.plot(data['close'])
    
    # Plotting day data

    axis1 = fig.add_subplot(1, 2, 2)
    axis1.set_title("Today's " +ticker+ " data")
    axis1.set_xlabel("Time")
    axis1.set_ylabel("Price")
    axis1.plot(data_day["Time"], data_day["Value"])
    axis1.get_xaxis().set_ticks([])

    pngImage = io.BytesIO()
    FigureCanvas(fig).print_png(pngImage)

    pngImageB64String = "data:image/png;base64,"
    pngImageB64String += base64.b64encode(pngImage.getvalue()).decode('utf8')

    return pngImageB64String

def get_intraday(ticker):
    data = get_historical_intraday(ticker, token=token)
    time = []
    value = []
    for i in range(len(data)):
        time.append(data[i]["label"])
        value.append(data[i]["close"])
    for i in range(len(time)): 
        pattern = r'^\d+\s\w\w'
        result = re.match(pattern, time[i])
        if result:
            result = result.group(0)
            if len(result) == 4:
                hour = result[0]
                ampm = result[2:]
            else:
                hour = result[0:2]
                ampm = result[3:]
            
            real=hour+':00 '+ampm
            time[i] = real
    data_frame = pd.DataFrame({"Time":time, "Value":value})
    data_frame["Time"] = pd.to_datetime(data_frame["Time"], format='%I:%M %p').dt.time
    data_frame['Time'] = data_frame['Time'].astype(str)

    return data_frame


