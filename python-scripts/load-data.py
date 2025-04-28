import requests

URL = "http://127.0.0.1:5004"

for i in range(10):
    message = {"msg": f"I am message {i}"}
    try:
        response = requests.post(URL, json=message, timeout=3)
        print(f"Sent: {message}, Response: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending message {i}: {e}")
