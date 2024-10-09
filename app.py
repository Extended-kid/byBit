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
FIXED_LEVERAGE = 1

# Функция для создания подписи
def create_signature(query_string):
    return hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# Функция для получения текущей цены актива
def get_price(symbol):
    base_url = "https://api-demo.bybit.com"
    response = requests.get(f"{base_url}/v5/market/kline?category=linear&symbol={symbol}&interval=1&limit=1")
    
    if response.status_code == 200:
        data = response.json()
        # Проверяем наличие ключа 'list' в ответе
        if 'result' in data and 'list' in data['result']:
            # Цена закрытия последней свечи
            closing_price = float(data['result']['list'][0][4])  # Используем индекс 4 для закрытия свечи
            return closing_price
        else:
            print(f"Unexpected response format: {data}")
            return None
    else:
        print(f"Failed to fetch price for {symbol}, status code: {response.status_code}")
        return None


# Функция для получения количества десятичных знаков для символа и минимального количества контрактов
def get_precision_and_min_qty(symbol):
    base_url = "https://api-demo.bybit.com"
    response = requests.get(f"{base_url}/v5/market/instruments-info?category=linear&symbol={symbol}")
    
    if response.status_code == 200:
        data = response.json()
        # Получаем точность для количества контрактов
        qty_step = data['result']['list'][0]['lotSizeFilter']['qtyStep']
        if '.' in qty_step:
            precision = len(qty_step.split('.')[1])
        else:
            precision = 0

        # Получаем минимальное количество контрактов
        min_qty = float(data['result']['list'][0]['lotSizeFilter']['minOrderQty'])

        return precision, min_qty
    else:
        return None, None

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
    signature = create_signature(query_string)

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
def place_order(symbol, side, qty):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    # Получаем текущую цену актива
    price = get_price(symbol)
    if price is None:
        return {"error": "Failed to fetch price for the symbol."}
    
    # Получаем точность и минимальное количество контрактов
    precision, min_qty = get_precision_and_min_qty(symbol)
    if precision is None or min_qty is None:
        return {"error": "Failed to fetch precision or min qty for the symbol."}

    # Если рассчитанное количество контрактов меньше минимального, устанавливаем минимальное
    if qty < min_qty:
        qty = min_qty

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
    signature = create_signature(query_string)

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

# Функция для закрытия всех позиций по символу
def close_all_positions(symbol):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    while True:
        # Получаем количество открытых контрактов
        qty = get_open_position_qty(symbol)
        
        if qty == 0:
            return {"message": "All positions closed successfully."}

        # Округляем количество до минимального шага контракта
        precision = get_precision(symbol)
        qty = round(qty, precision)

        # Тело запроса для закрытия позиции
        body = {
            "category": "linear",
            "symbol": symbol,
            "side": "Sell",  # Закрываем длинные позиции
            "orderType": "Market",
            "qty": str(qty),  # Количество контрактов для закрытия
            "reduceOnly": True,  # Используем reduce_only для закрытия
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

        # Отправляем запрос на закрытие позиции
        response = requests.post(f"{base_url}/v5/order/create", headers=headers, data=json.dumps(body))
        
        # Проверяем статус ответа
        if response.status_code == 200:
            result = response.json()
            print(f"Position closed, result: {result}")
        else:
            return {"error": f"Failed to close positions, status code: {response.status_code}", "details": response.text}



@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Received webhook data: {data}")  # Отладка: выводим данные вебхука

    if "action" not in data or "pair" not in data:
        return jsonify({"error": "Missing required fields: 'action' or 'pair'"}), 400
    
    action = data["action"].lower()
    pair = data["pair"]
    qty = data["qty"]

    # Удаляем суффикс .P, если он присутствует
    if pair.endswith(".P"):
        pair = pair.replace(".P", "")

    # Выполняем ордер на покупку или продажу в зависимости от действия
    if action == "buy":
        response = place_order(pair, "Buy", qty)  # Открываем ордер на покупку
        return jsonify(response)
    else:
        return jsonify({"error": "Unknown action"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
