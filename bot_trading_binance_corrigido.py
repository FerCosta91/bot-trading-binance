import time
import datetime
import os
import csv
from decimal import Decimal, ROUND_DOWN, getcontext
from binance.client import Client
from binance.enums import *

getcontext().prec = 8

# 🔐 Variáveis de ambiente
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

# 🔗 Cliente Binance
client = Client(API_KEY, API_SECRET)

# ✅ Confirmação de funcionamento
print("🤖 Bot iniciado com sucesso.")

# ⚙️ Configurações
symbols = ['SOLUSDT', 'ETHUSDT', 'XRPUSDT']
timeframe = '1h'
short_ma = 9
long_ma = 21
risk_usdt = 1
rr = 1.5
leverage = 10
log_file = 'trades.csv'

if not os.path.exists(log_file):
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['datetime', 'symbol', 'direction', 'entry', 'stop_loss', 'take_profit', 'qty'])

def get_klines(symbol, interval, limit=100):
    try:
        klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        return klines
    except Exception as e:
        print(f"Erro ao buscar dados de {symbol}: {e}")
        return None

def calculate_ema(data, period):
    ema = []
    k = 2 / (period + 1)
    for i in range(len(data)):
        if i < period - 1:
            ema.append(None)
        elif i == period - 1:
            sma = sum(data[:period]) / period
            ema.append(sma)
        else:
            ema_value = data[i] * k + ema[i-1] * (1 - k)
            ema.append(ema_value)
    return ema

def run_bot():
    for symbol in symbols:
        print(f"🔍 A verificar sinal para {symbol}...")
        klines = get_klines(symbol, timeframe)
        if not klines:
            continue

        closes = [float(k[4]) for k in klines]
        ema_short = calculate_ema(closes, short_ma)[-1]
        ema_long = calculate_ema(closes, long_ma)[-1]
        last_close = closes[-1]

        if not ema_short or not ema_long:
            continue

        direction = None
        if ema_short > ema_long:
            direction = 'BUY'
        elif ema_short < ema_long:
            direction = 'SELL'
        else:
            continue

        stop_loss = last_close * (0.99 if direction == 'BUY' else 1.01)
        take_profit = last_close * (1 + rr * 0.01 if direction == 'BUY' else 1 - rr * 0.01)
        quantity = Decimal(risk_usdt / abs(last_close - stop_loss)).quantize(Decimal('.0001'), rounding=ROUND_DOWN)

        try:
            # ✅ Alavancagem
            client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            # ✅ Criar ordem
            order = client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY if direction == 'BUY' else SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=float(quantity)
            )

            print(f"✅ Ordem executada: {order['side']} {symbol} - Qty: {quantity}")

            # ✅ Salvar no log
            with open(log_file, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.datetime.now(), symbol, direction, last_close, stop_loss, take_profit, quantity])

        except Exception as e:
            print("❌ Erro ao registrar trade:", e)

    print("⏳ Aguardar 5 minutos antes da próxima iteração")
    time.sleep(300)

if __name__ == "__main__":
    while True:
        run_bot()
