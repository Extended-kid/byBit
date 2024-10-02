from flask import Flask, request, jsonify
import logging

app = Flask(__name__)

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

@app.route('/webhook', methods=['POST'])
def webhook():
    # Логируем полученные данные
    data = request.json
    logging.info(f"Received data: {data}")

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    # Проверяем наличие ключа "action"
    if "action" in data:
        action = data["action"]
        if action == "buy":
            logging.info("Buy action received")
            return jsonify({"message": "Buy action received!"}), 200
        elif action == "sell":
            logging.info("Sell action received")
            return jsonify({"message": "Sell action received!"}), 200
        else:
            logging.info("Unknown action")
            return jsonify({"error": "Unknown action"}), 400
    else:
        logging.info("Invalid JSON format")
        return jsonify({"error": "Invalid JSON format"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
