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

# Функция для создания ордера на Bybit
def place_order(symbol, side, qty):
    base_url = "https://api-demo.bybit.com"
    timestamp = str(int(time.time() * 1000))
    recv_window = "10000"

    body = {
        "category": "linear",
        "symbol": symbol,
        "side": side,
        "orderType": "Market",
        "qty": qty,
        "timeInForce": "GTC",
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

    response = requests.post(f"{base_url}/v5/order/create", headers=headers, data=json.dumps(body))
    return response.json()

# Обработчик вебхуков
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data["action"] == "buy":
        response = place_order("BTCUSDT", "Buy", "0.001")  # Открываем ордер на покупку
        return jsonify(response)
    elif data["action"] == "sell":
        response = place_order("BTCUSDT", "Sell", "0.001")  # Открываем ордер на продажу
        return jsonify(response)
    else:
        return jsonify({"message": "Unknown action"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
