from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Логируем входящие данные для проверки
    logging.info(f"Received data: {data}")

    action = data.get('action')
    pair = data.get('pair')
    
    # Обработка данных
    if action == 'buy':
        logging.info(f"Opening long position for {pair}")
        # Логика для открытия длинной позиции (long)
        return jsonify({"message": f"Long position opened for {pair}"}), 200
    elif action == 'sell':
        logging.info(f"Closing position for {pair}")
        # Логика для закрытия позиции или открытия короткой позиции
        return jsonify({"message": f"Position closed or short opened for {pair}"}), 200
    else:
        logging.warning(f"Unknown action: {action}")
        return jsonify({"error": "Unknown action"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
