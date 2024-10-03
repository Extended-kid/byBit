from flask import Flask, request, jsonify
import hmac
import hashlib
import time
import requests
import json

app = Flask(__name__)

# Ваши ключи API для Bybit
api_key = 'TvPGXVmXup8QFuyYY4'
api_secret = 'Fa4yT9DFlxb0DEL1MHuKwXLFFy4OddQ7XKHR'

# Фиксированные значения для размера сделки и плеча
FIXED_AMOUNT_USD = 10
FIXED_LEVERAGE = 5

# Функция для получения текущей цены актива
def get_price(symbol):
    base_url = "https://api-demo.bybit.com"
    response = requests.get(f"{base_url}/v5/market/kline?category=linear&symbol={symbol}&interval=1&limit=1")
    
    if response.status_code == 200:
        data = response.json()
        # Цена закрытия последней свечи
        return float(data['result']['list'][0][4])
    else:
        return None

# Функция для получения количества десятичных знаков для символа
def get_precision(symbol):
    base_url = "https://api-demo.bybit.com"
    response = requests.get(f"{base_url}/v5/market/instruments-info?category=linear&symbol={symbol}")
    
    if response.status_code == 200:
        data = response.json()
        # Возвращаем количество десятичных знаков для количества (qtyStep)
        return int(data['result']['list'][0]['lotSizeFilter']['qtyStep'].rstrip('0').split('.')[-1])
    else:
        return None

# Функция для установки плеча
def set_leverage(symbol, leverage):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    # Тело запроса для установки плеча
    body = {
        "category": "linear",
        "symbol": symbol,
        "buyLeverage": str(leverage),
        "sellLeverage": str(leverage),
        "timestamp": timestamp,
        "recvWindow": recv_window
    }

    query_string = f'{timestamp}{api_key}{recv_window}{json.dumps(body)}'
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

    headers = {
        'X-BAPI-SIGN': signature,
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    # Отправляем запрос для установки плеча
    response = requests.post(f"{base_url}/v5/position/set-leverage", headers=headers, data=json.dumps(body))
    return response.json()

# Функция для создания ордера на Bybit
def place_order(symbol, side):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    # Получаем текущую цену актива
    price = get_price(symbol)
    if price is None:
        return {"error": "Failed to fetch price for the symbol."}
    
    # Получаем количество десятичных знаков для символа
    precision = get_precision(symbol)
    if precision is None:
        return {"error": "Failed to fetch precision for the symbol."}

    # Рассчитываем количество контрактов
    qty = (FIXED_AMOUNT_USD * FIXED_LEVERAGE) / price

    # Округляем количество контрактов в соответствии с precision
    qty = round(qty, precision)

    # Устанавливаем плечо
    set_leverage(symbol, FIXED_LEVERAGE)

    # Создаем тело запроса
    body = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(qty),  # Количество контрактов
        "timeInForce": "GTC",
        "timestamp": timestamp,
        "recvWindow": recv_window
    }

    # Создаем строку запроса для подписи
    query_string = f'{timestamp}{api_key}{recv_window}{json.dumps(body)}'
    signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

    # Устанавливаем заголовки
    headers = {
        'X-BAPI-SIGN': signature,
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-TIMESTAMP': timestamp,
        'X-BAPI-RECV-WINDOW': recv_window,
        'Content-Type': 'application/json'
    }

    # Отправляем запрос на создание ордера
    response = requests.post(f"{base_url}/v5/order/create", headers=headers, data=json.dumps(body))
    
    # Проверяем статус ответа
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to place order, status code: {response.status_code}", "details": response.text}

# Обработчик вебхуков
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Проверяем, что в вебхуке есть необходимые поля
    if "action" not in data or "pair" not in data:
        return jsonify({"error": "Missing required fields: 'action' or 'pair'"}), 400
    
    action = data["action"].lower()
    pair = data["pair"]

    # Выполняем ордер на покупку или продажу в зависимости от действия
    if action == "buy":
        response = place_order(pair, "Buy")  # Открываем ордер на покупку
        return jsonify(response)
    elif action == "sell":
        response = place_order(pair, "Sell")  # Открываем ордер на продажу
        return jsonify(response)
    else:
        return jsonify({"error": "Unknown action"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
