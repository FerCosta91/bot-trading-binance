# Usa uma imagem oficial com Python 3.10 (ou mais recente e estável)
FROM python:3.10-slim

# Define a pasta de trabalho
WORKDIR /app

# Copia os ficheiros do repositório para a imagem
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Comando para correr o bot
CMD ["python", "bot_trading_binance.py"]
