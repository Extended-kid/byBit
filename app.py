from flask import Flask, request, jsonify

app = Flask(__name__)

# Маршрут для вебхуков
@app.route('/webhook', methods=['POST'])
def webhook():
    # Попробуем получить JSON из запроса
    data = request.json
    if not data:
        return jsonify({"error": "No JSON received"}), 400

    # Проверим наличие ключа "action"
    if "action" in data:
        action = data["action"]
        if action == "buy":
            return jsonify({"message": "Buy action received!"}), 200
        elif action == "sell":
            return jsonify({"message": "Sell action received!"}), 200
        else:
            return jsonify({"error": "Unknown action"}), 400
    else:
        return jsonify({"error": "Invalid JSON format"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
