import alpaca_trade_api as tradeapi
import pandas as pd
import dotenv
from dotenv import load_dotenv
import os
import datetime
import time
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
import sys
load_dotenv()

os.environ["TZ"] = "America/New_York"
time.tzset()


proxy_client = TwilioHttpClient()
proxy_client.session.proxies = {'https': os.environ['https_proxy']}

account_sid = os.getenv("twilio_account_sid")
auth_token = os.getenv("twilio_auth_token")


alpaca_api_key = os.getenv("ALPACA_API_KEY")
alpaca_secret_key = os.getenv("ALPACA_SECRET_KEY")



client = Client(account_sid, auth_token, http_client=proxy_client)
number = os.getenv("number")

api = tradeapi.REST(key_id=alpaca_api_key,
                    secret_key=alpaca_secret_key,
                    api_version="v2",
                    base_url='https://paper-api.alpaca.markets')

account = api.get_account()

SP500 = 'SPY'

def send_message(qty,pct_gain,cash):
    try:
        body = f'Sold {qty} shares of SPY for {pct_gain}% profit \n new account value: {cash}'
        print(body)
        message = client.messages \
                    .create(
                         body=body,
                         from_='+14432513064',
                         to=number
                     )
    except Exception as e:
        print(e)
        error_message('send_message',e)

def error_message(function,error):
    body = f"ERROR with {function} function \n {error}"
    message = client.messages \
                .create(
                    to=number,
                    from_='+14432513064',
                    body=body,
                 )
    
def closing(event=None,context=None):
    try:
        if api.get_clock().is_open:
            sp500_market_price = api.get_barset(symbols='SPY',timeframe='1Min')[SP500][-1].c
            cash = float(account.cash)
            qty = int((cash*.95)/sp500_market_price)

            api.submit_order(
                symbol=SP500,
                qty=qty,
                side='buy',
                type='market',
            )

            body = f"Bought {qty} shares of SPY for {sp500_market_price*qty} \n waiting for market open..."
            message = client.messages \
                .create(
                     body=body,
                     from_='+14432513064',
                     to='+14019652503'
                 )

            wait_for_open()
        else:
            print('Market Closed')
            wait_for_open()
    except Exception as e:
        print(e)
        error_message('closing',e)


def opening():
    try:
        if api.get_clock().is_open:
            #Sell all
            positions_list = api.list_positions()
            for pos in range(len(positions_list)):
                qty = positions_list[pos].qty
                symbol = positions_list[pos].symbol
                api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='market',
                )
                last_close = api.get_barset(symbols=SP500,timeframe='1D',limit=2)[SP500][-2].c
                today_open = api.get_barset(symbols=SP500,timeframe='1D',limit=2)[SP500][-1].o
                pct_gain = pct_change(last_close,today_open)
                cash = float(account.cash)
                send_message(qty,pct_gain,cash)

                wait_for_close()
        else:
            wait_for_open()
    except Exception as e:
        print(e)
        error_message('opening',e)

def wait_for_open():
    try:
        clock = api.get_clock()
        n_open = clock.next_open.replace(tzinfo=None)
        now = datetime.datetime.now()
        print(f'Next open: {n_open} current time: {now}')
        seconds_to_next_open = (n_open - now).total_seconds()
        seconds_to_next_open = int(seconds_to_next_open+30)
        time.sleep(seconds_to_next_open)
        opening()
    except Exception as e:
        print(e)
        error_message('wait_for_open',e)

def wait_for_close():
    #sleeps until 3 minutes before market close
    try:
        clock = api.get_clock()
        n_close = clock.next_close.replace(tzinfo=None)
        now = datetime.datetime.now()
        print(f'Next close: {n_close} current time: {now}')
        seconds_to_next_close = (n_close - now).total_seconds()
        seconds_to_next_close = int(seconds_to_next_close-180)d
        time.sleep(seconds_to_next_close)
        closing()
    except Exception as e:
        print(e)
        error_message('wait_for_close',e)

def pct_change(first,second):
    try:
        return ((second-first)/first)*100
    except Exception as e:
        print(e)
        error_message('pct_change',e)

def init():
    if api.get_clock().is_open:
        wait_for_close()
    elif api.get_clock().is_open == False:
        wait_for_open()
        
init()