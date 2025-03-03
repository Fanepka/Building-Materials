import requests
import time
import base64
import logging


from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from os import getenv

if not load_dotenv('.env'):
    raise ImportError("Not found .env file")

app = Flask(__name__, static_url_path='/static')

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)

# Данные для ЮKassa
SHOP_ID = getenv("SHOP_ID")
SECRET_KEY = getenv("SECRET_KEY")
BASE_URL = "https://api.yookassa.ru/v3/"

# Корзина (временное хранилище)
cart = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cart')
def cart_page():
    return render_template('cart.html')

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    data = request.json
    cart.append(data)
    return jsonify({"status": "success"})

@app.route('/get_cart', methods=['GET'])
def get_cart():
    return jsonify(cart)

@app.route('/checkout', methods=['POST'])
def checkout():
    total = sum(item['price'] for item in cart)
    payment_data = {
        "amount": {
            "value": f"{total:.2f}",
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "http://localhost:5000/success"
        },
        "description": "Оплата стройматериалов",
        "capture": True  # Автоматическое подтверждение платежа
    }

    logging.debug(f"Payment data: {payment_data}")

    # Кодирование авторизации
    auth = base64.b64encode(f"{SHOP_ID}:{SECRET_KEY}".encode('utf-8')).decode('utf-8')
    headers = {
        "Authorization": f"Basic {auth}",
        "Idempotence-Key": str(int(time.time() * 1000)),  # Уникальный ключ на основе времени
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{BASE_URL}payments",
            json=payment_data,
            headers=headers
        )
        logging.debug(f"Response status code: {response.status_code}")
        logging.debug(f"Response content: {response.text}")

        # Проверка успешности запроса
        if response.status_code == 200:
            payment_response = response.json()
            if 'confirmation' in payment_response:
                payment_url = payment_response['confirmation']['confirmation_url']
                return jsonify({"paymentUrl": payment_url})
            else:
                logging.error(f"Unexpected response: {payment_response}")
                return jsonify({"error": "Ошибка: отсутствует подтверждение платежа"}), 500
        else:
            logging.error(f"Payment creation failed: {response.text}")
            return jsonify({"error": "Ошибка при создании платежа"}), 500
    except Exception as e:
        logging.error(f"Error during payment creation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    app.run(debug=True)