import os
import time
import datetime
import csv
import requests
from decimal import Decimal, ROUND_DOWN, getcontext
from binance.client import Client
from binance.enums import *

getcontext().prec = 8

# 🔐 Variáveis de ambiente
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 🔗 Cliente Binance
client = Client(API_KEY, API_SECRET)

# 🧪 Configuração dos ativos
symbols = ['SOLUSDT', 'ETHUSDT', 'XRPUSDT']
timeframe = '1h'
short_ema = 9
long_ema = 21
trend_ema = 200
risk_per_trade = Decimal('1')  # 1 USDC
rr_ratio = Decimal('1.5')  # risco:recompensa
volume_multiplier = 1.2  # volume precisa estar 20% acima da média

# 📁 Arquivo de log
log_file = 'trades_log.csv'
if not os.path.exists(log_file):
    with open(log_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'symbol', 'mensagem'])

def log_trade(symbol, mensagem):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, symbol, mensagem])

def enviar_telegram(mensagem):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}
        requests.post(url, data=payload)
    except Exception as e:
        print("Erro ao enviar para o Telegram:", e)

def obter_dados(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    closes = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]
    highs = [float(k[2]) for k in klines]
    lows = [float(k[3]) for k in klines]
    return closes, volumes, highs, lows

def calcular_ema(lista, período):
    k = 2 / (período + 1)
    ema = [sum(lista[:período]) / período]
    for preço in lista[período:]:
        ema.append((preço - ema[-1]) * k + ema[-1])
    return ema

def candle_forte(closes, highs, lows):
    corpo = abs(closes[-1] - closes[-2])
    range_candle = highs[-1] - lows[-1]
    return corpo > 0.5 * range_candle

def calcular_volume_acima_media(volumes):
    média = sum(volumes[:-1]) / (len(volumes) - 1)
    return volumes[-1] > média * volume_multiplier

def calcular_quantidade(symbol, stop_prejuízo):
    preco = float(client.get_symbol_ticker(symbol=symbol)['price'])
    quantidade = (risk_per_trade / Decimal(stop_prejuízo)).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
    return float(quantidade)

def executar_bot():
    print("🤖 Bot iniciado com sucesso.")
    print("🌍 IP público:", requests.get("https://api.ipify.org").text)

    while True:
        agora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n📅 Execução às {agora}")
        for symbol in symbols:
            try:
                closes, volumes, highs, lows = obter_dados(symbol, timeframe)
                ema_curta = calcular_ema(closes, short_ema)
                ema_longa = calcular_ema(closes, long_ema)
                ema_tendencia = calcular_ema(closes, trend_ema)

                tendência_alta = closes[-1] > ema_tendencia[-1]
                cruzamento_alta = ema_curta[-2] < ema_longa[-2] and ema_curta[-1] > ema_longa[-1]
                candle_ok = candle_forte(closes, highs, lows)
                volume_ok = calcular_volume_acima_media(volumes)

                if tendência_alta and cruzamento_alta and candle_ok and volume_ok:
                    entrada = highs[-1]
                    stop = lows[-1]
                    alvo = entrada + (entrada - stop) * float(rr_ratio)
                    quantidade = calcular_quantidade(symbol, entrada - stop)

                    mensagem = f"📈 Sinal de compra em {symbol}\nEntrada: {entrada:.4f}\nStop: {stop:.4f}\nAlvo: {alvo:.4f}\nQtd: {quantidade}"
                    print(mensagem)
                    log_trade(symbol, mensagem)
                    enviar_telegram(mensagem)

                    # Aqui pode-se colocar a ordem real, se desejar
                    # client.futures_create_order(...)

                else:
                    print(f"{symbol}: volume abaixo da média.")
                    log_trade(symbol, "volume abaixo da média.")

            except Exception as e:
                erro_msg = f"{symbol}: Erro ao processar - {e}"
                print(erro_msg)
                log_trade(symbol, erro_msg)

        print("🕔 Aguardar 5 minutos...")
        time.sleep(300)

if __name__ == "__main__":
    executar_bot()
