from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Render!"

# Маршрут для вебхуков, который принимает POST-запросы
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # Здесь можно обработать входящие данные
    return jsonify({"message": "Webhook received!"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
