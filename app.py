import logging
from flask import Flask, request, jsonify

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    action = data.get('action')
    pair = data.get('pair')
    
    if action == 'buy':
        # Логика для открытия длинной позиции (buy)
        return jsonify({"message": f"Long position opened for {pair}"}), 200
    elif action == 'sell':
        # Логика для закрытия позиции или открытия короткой позиции (sell)
        return jsonify({"message": f"Short position opened or closed for {pair}"}), 200
    else:
        return jsonify({"error": "Unknown action"}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
