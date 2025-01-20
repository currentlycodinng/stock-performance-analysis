import pandas as pd
import numpy as np 
import seaborn as sns
import matplotlib.pyplot as plt
import yfinance as yf
import os
import time  

class Reader:
    """
    class created to read a csv file 
    """
    
    @staticmethod
    def read_file(path):
        """
        method that reads a file
        return created data
        
        param: files path 
        """
        data = pd.read_csv(path)
        return data
    
    @staticmethod
    def new_data_set(data):
        """
        method takes data and iterate through it looking for
        shortname and symbols then it stores those string in the 
        dictionary and create new list out of them
        
        return new created dataset of dictionaries
        
        param: data -> represents a dataset 
        """
        new_data = []

        for _, row in data.iterrows():
            symbol = row['Symbol'] # stock symbol
            name = row['Shortname'] # short name
            new_data.append({'Name': name, 'Symbol': symbol})
        return new_data

    @staticmethod
    def stock_data(file_path: str) -> pd.DataFrame:
        """
        stock info from the file
        """

        # read the CSV file
        data = Reader.read_file(file_path)

        # stock tickers from the file - tickers are unique symbols assigned to publicly traded companies 
        # tolist converts a column from dataframe into a list 
        tickers = data['Symbol'].tolist()
        
        stock_metrics = [] # holds info abt the stocks

        # for some stocks yfinance lacks data, so error handling had to be done for program not to crash in the process 
        for ticker in tickers:
            try:
                # rate-limiting to avoid API blocking
                time.sleep(1)  # delay between requests - otherwise gives "Too Many Requests for url"
                
                # we use yfinance to extract data abt stocks from the file we have
                stock = yf.Ticker(ticker)

                # It returns a dataframe with columns like Open, High, Low, Close, Volume with dates.
                # dataframe contains daily stock price data for a year.
                history = stock.history(period="ytd") # 1 year history
                if history.empty:
                    print(f"No price history for {ticker}, skipping.")
                    continue

                # in the formula we calculate the price change through: closing price on the most recent day (last row) minus
                # closing price on the first day of the period (first row) all divided by closing price on the first day and multiplying by a hundred to get a percentage
                price_change = ((history['Close'].iloc[-1] - history['Close'].iloc[0]) / history['Close'].iloc[0]) * 100
                
                # financial info abt the companies - eg. total revenue and net income
                # stock is an instance of yf.Ticker
                financials = stock.financials

                if financials is None or financials.empty:
                    print(f"No financial data for {ticker}, skipping.")
                    revenue, net_income, profit_margin = None, None, None
                else:
                    # calculating revenue and net income
                    try:
                        # iloc() is a pandas method that allows to access data by row and column in a dataframe
                        # iloc[0] - value from the first column 
                        if 'Total Revenue' in financials.index:
                            revenue = financials.loc['Total Revenue'].iloc[0]  
                        else:
                            revenue = None

                        if 'Net Income' in financials.index:
                            net_income = financials.loc['Net Income'].iloc[0]
                        else:
                            net_income = None
                        
                        if revenue and net_income:
                            profit_margin = (net_income / revenue) * 100
                        else:
                            profit_margin = None

                    except KeyError:
                        revenue, profit_margin = None, None

                eps_trailing = stock.info.get('trailingEps', None)
                eps_forward = stock.info.get('forwardEps', None)

                if eps_trailing and eps_forward and eps_forward != 0:
                    eps_growth = ((eps_trailing - eps_forward) / abs(eps_forward)) * 100
                else:
                    eps_growth = None

                stock_metrics.append({
                    'Ticker': ticker,
                    'Price Change (%)': price_change,
                    'Revenue': revenue,
                    'Profit Margin (%)': profit_margin,
                    'EPS Growth (%)': eps_growth
                })
                
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")
        
        return pd.DataFrame(stock_metrics) # returns a table with information gotten


def get_user_preferences():
    """
    user preferences 
    """
    stock_type = input("Enter stock type (risky/not risky): ").strip()
    top = int(input("Enter the number of top stocks to recommend: ").strip())
    esg_importance = input("How important are ESG factors? (High/Medium/Low): ").strip().lower()
    
    return {
        "stock_type": stock_type,
        "top": top,
        "esg_importance": esg_importance
    }

def rank_stocks(stock_data: pd.DataFrame, user_preferences, top):
    """
    ranks based on data from stock_data attribute 
    """
    # fillna(0) - if the data is missing (NaN) in the dataframe - replaces with a 0
    stock_data['Price Change (%)'] = stock_data['Price Change (%)'].fillna(0)
    stock_data['Profit Margin (%)'] = stock_data['Profit Margin (%)'].fillna(0)
    stock_data['EPS Growth (%)'] = stock_data['EPS Growth (%)'].fillna(0)

    # overall ranking of stocks - by giving each thing a weight
    # weight of ESG growth depends on importance

    if user_preferences['esg_importance'] == 'high':
        esg_weight = 0.4 
        
        stock_data['Overall Score'] = (
        stock_data['Price Change (%)'] * 0.3 +
        stock_data['Profit Margin (%)'] * 0.3 +
        stock_data['EPS Growth (%)'] * esg_weight)

    elif user_preferences['esg_importance'] == 'medium':
        esg_weight = 0.2
        stock_data['Overall Score'] = (
        stock_data['Price Change (%)'] * 0.4 +
        stock_data['Profit Margin (%)'] * 0.4 +
        stock_data['EPS Growth (%)'] * 0.2)
        
    else:
        esg_weight = 0.1
        stock_data['Overall Score'] = (
        stock_data['Price Change (%)'] * 0.5 +
        stock_data['Profit Margin (%)'] * 0.4 +
        stock_data['EPS Growth (%)'] * 0.1)

    # head method returns top N rows from the table 
    ranked_stocks = stock_data.sort_values(by='Overall Score', ascending=False).head(top)
    return ranked_stocks

# main program 
csv_path = "sp500_companies.csv"

# stock data - printing for user to know its working, as it takes some time to fetch data 
print("Fetching stock performance data...")
performance_data = Reader.stock_data(csv_path)

# user preferences
user_preferences = get_user_preferences()

# rank stocks and get recommendations
print("Ranking stocks based on performance...")
recommendations = rank_stocks(performance_data, user_preferences, user_preferences['top'])

# output
print("\nTop Recommended Stocks:")
print(recommendations)