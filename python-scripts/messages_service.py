from fastapi import FastAPI
from util_functions import write_log
import uvicorn
import sys
from urllib.parse import urlparse
import requests
from kafka import KafkaConsumer
import time
import threading

app = FastAPI()

POLL_INTERVAL = 3
TOPIC_NAME = "messages"
KAFKA_GROUP_ID = "messages_group"
CONSUMER_POLL_TIME_OUT_MS = 1000

messages = []
consumer_running = True

def get_service_ips(service_name):
    try:
        response = requests.get(f"{config_server_url}/services/{service_name}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error retrieving {service_name} IPs: {e}")
        return []


def consume_messages():
    global messages

    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=kafka_url,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id=KAFKA_GROUP_ID,
            api_version=(2, 0, 2),
            request_timeout_ms=15000
        )
        write_log("Kafka Consumer Connected", port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", port)
        return

    while consumer_running:
        records = consumer.poll(timeout_ms=CONSUMER_POLL_TIME_OUT_MS)
        for tp, msgs in records.items():
            for msg in msgs:
                messages.append(msg.value.decode())
                write_log(f"New message received: {msg.value.decode()}", port)
        
        time.sleep(POLL_INTERVAL) 

@app.on_event("startup")
def start_consumer():
    thread = threading.Thread(target=consume_messages, daemon=True)
    thread.start()

@app.get("/")
def get_data():
    write_log("GET request", port)

    write_log(f"GET request response: {messages}", port)
    return {"msg": messages}

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: script.py <host_url> <config_server_url> <messages_service_idx>")
        sys.exit(1)
    port = None
    try:
        host_url = urlparse(sys.argv[1].strip())
        config_server_url = sys.argv[2].strip()
        messages_service_idx = int(sys.argv[3])

        kafka_services = get_service_ips("kafka-services")
        kafka_url = kafka_services[messages_service_idx]

        port = host_url.port
    except Exception as e:
        write_log(f"Exception {e}", )
    
    write_log(f"Starting up server: {host_url.hostname}:{port}", port)
    uvicorn.run(app, host=host_url.hostname, port=port)
