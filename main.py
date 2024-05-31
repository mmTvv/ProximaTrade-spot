from config import api, secret, telegram, channel_id, max_pos, tp, sl, timeframe, mode, leverage, qty
from pybit.unified_trading import HTTP
import pandas as pd
import ta
import telebot
from time import sleep


session = HTTP(
    api_key=api,
    api_secret=secret,
    testnet=False
)


bot = telebot.TeleBot(telegram)

# Getting balance on Bybit Derivatrives Asset (in USDT)
def get_balance():
    try:
        resp = session.get_wallet_balance(accountType="CONTRACT", coin="USDT")['result']['list'][0]['coin'][0]['walletBalance']
        resp = float(resp)
        return resp
    except Exception as err:
        print(err)

print(f'Your balance: {get_balance()} USDT')


# Getting all available symbols from Derivatives market (like 'BTCUSDT', 'XRPUSDT', etc)
def get_tickers():
    try:
        resp = session.get_tickers(category="spot")['result']['list']
        symbols = []
        for elem in resp:
            if 'USDT' in elem['symbol'] and not 'USDC' in elem['symbol']:
                symbols.append(elem['symbol'])
        return symbols
    except Exception as err:
        print(err)


# Klines is the candles of some symbol (up to 1500 candles). Dataframe, last elem has [-1] index
def klines(symbol):
    try:
        resp = session.get_kline(
            category='linear',
            symbol=symbol,
            interval=timeframe,
            limit=500
        )['result']['list']
        resp = pd.DataFrame(resp)
        resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover']
        resp = resp.set_index('Time')
        resp = resp.astype(float)
        resp = resp[::-1]
        return resp
    except Exception as err:
        print(err)





# Placing order with Market price. Placing TP and SL as well
def place_order_market(symbol, side):
    mark_price = session.get_tickers(
        category='spot',
        symbol=symbol
    )['result']['list'][0]['markPrice']
    mark_price = float(mark_price)
    print(f'Placing {side} order for {symbol}. Mark price: {mark_price}')


    order_qty = round(qty/mark_price, qty_precision)
    sleep(2)
    if side == 'buy':
        try:
            resp = session.place_order(
                category='spot',
                symbol=symbol,
                side='Buy',
                orderType='Market',
                qty=order_qty,
            )
            print(resp)
            print('-----------------------------------')
        except Exception as err:
            print(err)


# Some RSI strategy. Make your own using this example
def rsi_signal(symbol):
    kl = klines(symbol)
    ema = ta.trend.ema_indicator(kl.Close, window=200)
    rsi = ta.momentum.RSIIndicator(kl.Close).rsi()
    if rsi.iloc[-3] < 30 and rsi.iloc[-2] < 30 and rsi.iloc[-1] > 30:
        return 'up'
    if rsi.iloc[-3] > 70 and rsi.iloc[-2] > 70 and rsi.iloc[-1] < 70:
        return 'down'
    else:
        return 'none'

# William %R signal
def williamsR(symbol):
    kl = klines(symbol)
    w = ta.momentum.WilliamsRIndicator(kl.High, kl.Low, kl.Close, lbp=24).williams_r()
    ema_w = ta.trend.ema_indicator(w, window=24)
    if w.iloc[-1] < -99.5:
        return 'up'
    elif w.iloc[-1] > -0.5:
        return 'down'
    elif w.iloc[-1] < -75 and w.iloc[-2] < -75 and w.iloc[-2] < ema_w.iloc[-2] and w.iloc[-1] > ema_w.iloc[-1]:
        return 'up'
    elif w.iloc[-1] > -25 and w.iloc[-2] > -25 and w.iloc[-2] > ema_w.iloc[-2] and w.iloc[-1] < ema_w.iloc[-1]:
        return 'down'
    else:
        return 'none'

    

   # Max current orders
symbols = get_tickers()     # getting all symbols from the Bybit Derivatives

# Infinite loop
while True:
    balance = get_balance()
    if balance != None:
        balance = float(balance)
        print(f'Balance: {balance}')
        for elem in symbols:
            pos = get_positions()
            if len(pos) >= max_pos and elem in pos:
                break
            # Signal to buy or sell
            signal = williamsR(elem)
            if signal == 'up':
                print(f'Found BUY signal for {elem}')
                bot.send_message(channel_id, elem + ' - buy')
                sleep(5)
            if signal == 'down':
                print(f'Found SELL signal for {elem}')
                place_order_market(elem, 'sell')
                bot.send_message(channel_id, elem+' - buy')
                sleep(5)
    print('Waiting 2.5 hours')
    sleep(2.5 * 60 * 60)
