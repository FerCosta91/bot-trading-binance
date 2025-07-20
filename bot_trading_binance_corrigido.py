import time
import datetime
import os
import requests
from decimal import Decimal, ROUND_DOWN, getcontext
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET

ORDER_TYPE_STOP_MARKET = 'STOP_MARKET'
ORDER_TYPE_LIMIT = 'LIMIT'

getcontext().prec = 8

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
client = Client(API_KEY, API_SECRET)

print("🤖 Bot iniciado com sucesso.")
print("🌍 IP público:", requests.get("https://api.ipify.org").text)

symbols = ['SOLUSDT', 'ETHUSDT', 'XRPUSDT']
timeframe = '1h'
short_ma = 9
long_ma = 21
trend_ma = 200
risk_usdc = Decimal('1')
rr = Decimal('1.5')

symbol_specs = {
    'SOLUSDT': {'precision': 2, 'min_notional': Decimal('5')},
    'ETHUSDT': {'precision': 3, 'min_notional': Decimal('20')},
    'XRPUSDT': {'precision': 1, 'min_notional': Decimal('5')}
}

def log(msg):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f"[{timestamp}] {msg}"
    with open("logs.txt", "a") as f:
        f.write(linha + "\n")
    print(linha)

def get_klines(symbol, interval, limit=200):
    return client.futures_klines(symbol=symbol, interval=interval, limit=limit)

def calculate_ma(prices, period):
    return sum(prices[-period:]) / period

def round_quantity(qty, decimals):
    return qty.quantize(Decimal('1.' + '0'*decimals), rounding=ROUND_DOWN)

def is_trending(prices, ma200, threshold=0.3):  # antes 0.5%
    return abs(prices[-1] - ma200) / ma200 > (threshold / 100)

def volume_ok(volumes):
    return float(volumes[-1]) >= 0.75 * (sum(map(float, volumes[-20:-1])) / 19)  # antes 0.9

def is_position_open(symbol):
    positions = client.futures_position_information(symbol=symbol)
    for pos in positions:
        if float(pos['positionAmt']) != 0:
            return True
    return False

def place_trade(symbol, direction, entry_price, stop_price):
    spec = symbol_specs[symbol]
    precision = spec['precision']
    min_notional = spec['min_notional']

    stop_diff = abs(entry_price - stop_price)
    quantity = round_quantity(risk_usdc / Decimal(stop_diff), precision)
    notional = quantity * Decimal(entry_price)

    if notional < min_notional:
        log(f"⚠️ Ordem ignorada em {symbol}: notional={notional:.2f} < mínimo {min_notional}")
        return

    side = SIDE_BUY if direction == 'buy' else SIDE_SELL
    opposite = SIDE_SELL if direction == 'buy' else SIDE_BUY
    target_price = entry_price + stop_diff * rr if direction == 'buy' else entry_price - stop_diff * rr

    try:
        client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=float(quantity)
        )

        client.futures_create_order(
            symbol=symbol,
            side=opposite,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=float(stop_price),
            closePosition=True,
            reduceOnly=True
        )

        client.futures_create_order(
            symbol=symbol,
            side=opposite,
            type=ORDER_TYPE_LIMIT,
            price=float(target_price),
            timeInForce='GTC',
            closePosition=True,
            reduceOnly=True
        )

        log(f"✅ {symbol} -> {direction.upper()} | Entrada: {entry_price:.2f}, SL: {stop_price:.2f}, TP: {target_price:.2f}")

    except Exception as e:
        log(f"❌ Erro ao executar ordens em {symbol}: {e}")

def main():
    while True:
        log(f"\n⏳ Execução às {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        for symbol in symbols:
            try:
                candles = get_klines(symbol, timeframe)
                closes = [float(c[4]) for c in candles]
                volumes = [float(c[5]) for c in candles]
                last_candle = candles[-2]
                prev_candle = candles[-3]

                ma_short = calculate_ma(closes, short_ma)
                ma_long = calculate_ma(closes, long_ma)
                ma_200 = calculate_ma(closes, trend_ma)

                if not is_trending(closes, ma_200):
                    log(f"{symbol}: mercado lateral.")
                    continue

                if not volume_ok(volumes):
                    log(f"{symbol}: volume abaixo da média.")
                    continue

                if is_position_open(symbol):
                    log(f"{symbol}: já existe posição aberta. Ignorado.")
                    continue

                mark_price = float(client.futures_mark_price(symbol=symbol)['markPrice'])
                high = float(last_candle[2])
                low = float(last_candle[3])
                prev_high = float(prev_candle[2])
                prev_low = float(prev_candle[3])

                if ma_short > ma_long and mark_price > high:
                    stop = Decimal(prev_low) - Decimal('0.01')
                    place_trade(symbol, 'buy', Decimal(mark_price), stop)

                elif ma_short < ma_long and mark_price < low:
                    stop = Decimal(prev_high) + Decimal('0.01')
                    place_trade(symbol, 'sell', Decimal(mark_price), stop)

                else:
                    log(f"{symbol}: sem sinal claro.")

            except Exception as e:
                log(f"❌ Erro em {symbol}: {e}")

        log("⏲️ Aguardar 5 minutos...\n")
        time.sleep(300)

if __name__ == '__main__':
    main()
