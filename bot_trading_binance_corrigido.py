import os
import time
import datetime
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

# ✅ Mensagem de confirmação ao iniciar
print("✅ Bot iniciado com sucesso.")

# 🔧 Configuração do bot
symbols = ['SOLUSDT', 'ETHUSDT', 'XRPUSDT']
timeframe = '1h'
short_ma = 9
long_ma = 21
risk_usdt = 1
rr = 1.5
leverage = 10

# 📁 Ficheiro de log
log_file = 'trades.csv'
if not os.path.exists(log_file):
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'side', 'entry_price', 'stop_loss', 'take_profit', 'quantity'])

# 🕐 Função para obter dados de candles
def get_klines(symbol, interval, limit=100):
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        return [{
            'open_time': datetime.datetime.fromtimestamp(k[0]/1000),
            'open': float(k[1]),
            'high': float(k[2]),
            'low': float(k[3]),
            'close': float(k[4]),
            'volume': float(k[5])
        } for k in klines]
    except Exception as e:
        print(f"Erro ao obter klines para {symbol}:", e)
        return []

# 🧠 Função de lógica da estratégia (simplificada)
def calculate_ma(candles, period):
    closes = [c['close'] for c in candles]
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period

# 🔄 Loop principal
def run_bot():
    while True:
        for symbol in symbols:
            candles = get_klines(symbol, timeframe)
            if not candles:
                continue

            ema_short = calculate_ma(candles, short_ma)
            ema_long = calculate_ma(candles, long_ma)

            if ema_short is None or ema_long is None:
                continue

            last_close = candles[-1]['close']
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
                print(f"{datetime.datetime.now()} | {symbol} | {direction} | Entry: {last_close:.3f} | SL: {stop_loss:.3f} | TP: {take_profit:.3f} | Qty: {quantity}")
                with open(log_file, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([datetime.datetime.now(), symbol, direction, last_close, stop_loss, take_profit, float(quantity)])
            except Exception as e:
                print("Erro ao registar trade:", e)

        time.sleep(300)  # Aguarda 5 minutos antes da próxima iteração

if __name__ == '__main__':
    run_bot()
