from fastapi import FastAPI
from urllib.parse import urlparse
from kafka import KafkaProducer
from util_functions import write_log
from random import shuffle
import requests
import sys
import uvicorn
import uuid
import json

messages_urls = []
logging_urls = []
kafka_urls = []

host_url = None
config_server_url = None
port = None

TOPIC_NAME = "messages"

app = FastAPI()


def get_service_ips(service_name):
    try:
        response = requests.get(f"{config_server_url}/services/{service_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving {service_name} IPs: {e}")
        return []

def send_message_to_queue(message):
    write_log(f"Writing message {message} to the queue", port)

    if not kafka_urls:
        print("Kafka service is unavailable")
        return
    
    producer = KafkaProducer(bootstrap_servers=kafka_urls)
    producer.send(TOPIC_NAME, bytes(message, "UTF-8"))
    producer.flush()

@app.post("/")
def add_data(message: dict):
    write_log("POST request", port)
    uuid_val = uuid.uuid4()
    message_value = message.get("msg", "")
    data = {"uuid": str(uuid_val), "msg": message_value}
    
    shuffled_urls = logging_urls[:]
    shuffle(shuffled_urls)
    
    for logging_service_url in shuffled_urls:
        try:
            response = requests.post(logging_service_url, json=data, timeout=3)
            if response.status_code == 200:
                write_log(f"Sending message {message_value} to the logging service", port)
                break
        except requests.exceptions.RequestException as e:
            return {"error": f"Error with logging service {logging_service_url}: {e}"}
        
    send_message_to_queue(message_value)
    
    return {"msg": "success"}

@app.get("/")
def get_data():
    write_log("GET request", port)
    shuffled_logging_urls = logging_urls[:]
    shuffled_messages_urls = messages_urls[:]
    
    shuffle(shuffled_logging_urls)
    shuffle(shuffled_messages_urls)
    
    logging_service_messages = {"error": "No logging service available"}
    messages_service_messages = {"error": "Messages service unavailable"}

    for logging_url in shuffled_logging_urls:
        try:
            write_log(f"Trying to connect to logging service: {logging_url}", port)
            logging_service_response = requests.get(logging_url, timeout=3)
            if logging_service_response.status_code == 200:
                logging_service_messages = json.loads(logging_service_response.content.decode("utf-8"))
                write_log(f"Connected successfully", port)
                break
        except requests.exceptions.RequestException as e:
            print({"err" : f"Error with logging service {logging_url}: {e}"})

    for messages_url in shuffled_messages_urls:
        try:
            write_log(f"Trying to connect to messages service: {messages_url}", port)
            messages_service_response = requests.get(messages_url, timeout=10)
            if messages_service_response.status_code == 200:
                messages_service_messages = json.loads(messages_service_response.content.decode("utf-8"))["msg"]
                write_log(f"Connected successfully", port)
                break
        except requests.exceptions.RequestException as e:
            print({"err": f"Error with messages service {messages_url}: {e}"})

    GET_request_response = {
        "logging_service_response": logging_service_messages,
        "messages_service_response": messages_service_messages
    }

    write_log(f"GET request response: {GET_request_response}", port)

    return GET_request_response

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: facade_service.py <host_url> <config_server_url>")
        sys.exit(1)
    
    host_url = urlparse(sys.argv[1])
    config_server_url = sys.argv[2]

    messages_urls = [msg.strip() for msg in get_service_ips("messages-services")]
    logging_urls = get_service_ips("logging-services")
    kafka_urls = get_service_ips("kafka-services")

    port = host_url.port

    write_log(f"Starting up server {host_url.hostname}:{port}", port)
    uvicorn.run(app, host=host_url.hostname, port=port)
