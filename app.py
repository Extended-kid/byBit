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
        if 'result' in data and 'list' in data['result']:
            closing_price = float(data['result']['list'][0][4])  # Цена закрытия последней свечи
            return closing_price
        else:
            print(f"Unexpected response format: {data}")
            return None
    else:
        print(f"Failed to fetch price for {symbol}, status code: {response.status_code}")
        return None

# Функция для получения количества десятичных знаков и минимального количества контрактов
def get_precision_and_min_qty(symbol):
    base_url = "https://api-demo.bybit.com"
    response = requests.get(f"{base_url}/v5/market/instruments-info?category=linear&symbol={symbol}")
    
    if response.status_code == 200:
        data = response.json()
        qty_step = data['result']['list'][0]['lotSizeFilter']['qtyStep']
        precision = len(qty_step.split('.')[1]) if '.' in qty_step else 0
        min_qty = float(data['result']['list'][0]['lotSizeFilter']['minOrderQty'])
        return precision, min_qty
    else:
        return None, None

# Функция для установки плеча
def set_leverage(symbol, leverage):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

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

    response = requests.post(f"{base_url}/v5/position/set-leverage", headers=headers, data=json.dumps(body))
    return response.json()

# Функция для создания ордера на покупку/продажу
def place_order(symbol, side, qty):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    qty = float(qty)
    price = get_price(symbol)
    if price is None:
        return {"error": "Failed to fetch price for the symbol."}
    
    precision, min_qty = get_precision_and_min_qty(symbol)
    if precision is None or min_qty is None:
        return {"error": "Failed to fetch precision or min qty for the symbol."}

    if qty < min_qty:
        qty = min_qty

    qty = round(qty, precision)
    set_leverage(symbol, FIXED_LEVERAGE)

    body = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": str(qty),
        "timeInForce": "GTC",
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

    response = requests.post(f"{base_url}/v5/order/create", headers=headers, data=json.dumps(body))
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to place order, status code: {response.status_code}", "details": response.text}

# Функция для закрытия всех позиций
def close_all_positions(symbol):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"
    qty = 9999999  # Большое число для закрытия всех позиций

    body = {
        "category": "linear",
        "symbol": symbol,
        "side": "Sell",
        "orderType": "Market",
        "qty": str(qty),
        "reduceOnly": True,
        "timeInForce": "GTC",
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

    response = requests.post(f"{base_url}/v5/order/create", headers=headers, data=json.dumps(body))
    
    if response.status_code == 200:
        result = response.json()
        print(f"Position closed, result: {result}")
    else:
        return {"error": f"Failed to close positions, status code: {response.status_code}", "details": response.text}

# Обработчик вебхуков
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print(f"Received webhook data: {data}")

    if "action" not in data or "pair" not in data:
        return jsonify({"error": "Missing required fields: 'action' or 'pair'"}), 400
    
    action = data["action"].lower()
    pair = data["pair"]
    qty = data.get("qty", None)

    if pair.endswith(".P"):
        pair = pair.replace(".P", "")

    if action == "buy":
        response = place_order(pair, "Buy", qty)  # Открываем ордер на покупку
        return jsonify(response)
    elif action == "sell":
        response = close_all_positions(pair)  # Закрываем позицию
        return jsonify(response)
    else:
        return jsonify({"error": "Unknown action"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
