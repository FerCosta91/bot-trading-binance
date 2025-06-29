import time
import datetime
import os
import requests

from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

client = Client(API_KEY, API_SECRET)
print("🚀 Bot de trading iniciado com sucesso.")
print("🌍 IP público da aplicação:", requests.get("https://api.ipify.org").text)

symbols = ['SOLUSDT', 'AVAXUSDT', 'LINKUSDT']
timeframe = '1h'
short_ma = 9
long_ma = 21
risk_usdc = 1
reward_usdc = 2

def get_klines(symbol, interval, limit=100):
    candles = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    return [float(x[4]) for x in candles]  # preÃ§o de fecho

def calculate_ma(prices, period):
    return sum(prices[-period:]) / period

def place_trade(symbol, direction):
    price = float(client.futures_mark_price(symbol=symbol)['markPrice'])
    quantity = round(risk_usdc / price, 3)

    side = SIDE_BUY if direction == 'buy' else SIDE_SELL
    opposite = SIDE_SELL if direction == 'buy' else SIDE_BUY

    order = client.futures_create_order(
        symbol=symbol,
        side=side,
        type=ORDER_TYPE_MARKET,
        quantity=quantity
    )

    # Tentativa de obter o preÃ§o de execuÃ§Ã£o real (nem sempre disponÃ­vel)
    fills = order.get('fills', [])
    if fills and 'price' in fills[0]:
        entry_price = float(fills[0]['price'])
    else:
        entry_price = price  # fallback para o mark price

    stop_price = entry_price - 1 if direction == 'buy' else entry_price + 1
    target_price = entry_price + 2 if direction == 'buy' else entry_price - 2

    client.futures_create_order(
        symbol=symbol,
        side=opposite,
        type=ORDER_TYPE_STOP_MARKET,
        stopPrice=round(stop_price, 2),
        closePosition=True
    )

    print(f"\n{symbol} -> {direction.upper()} | Entry: {entry_price:.2f}, SL: {stop_price:.2f}, TP: {target_price:.2f}")

while True:
    print(f"\nInÃ­cio da execuÃ§Ã£o Ã s {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    for symbol in symbols:
        try:
            prices = get_klines(symbol, timeframe)
            ma_short = calculate_ma(prices, short_ma)
            ma_long = calculate_ma(prices, long_ma)

            if abs(ma_short - ma_long) < 0.05:
                print(f"{symbol}: mercado lateral, sem entrada.")
                continue

            if ma_short > ma_long:
                place_trade(symbol, 'buy')
            elif ma_short < ma_long:
                place_trade(symbol, 'sell')
            else:
                print(f"{symbol}: sem sinal claro.")

        except Exception as e:
            print(f"Erro ao processar {symbol}: {e}")

    print("ExecuÃ§Ã£o completa. A aguardar 1 hora...\n")
    time.sleep(60 * 60)

