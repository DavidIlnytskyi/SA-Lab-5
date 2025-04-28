from fastapi import FastAPI
from util_functions import write_log
import uvicorn
from fastapi.responses import JSONResponse
import sys
from urllib.parse import urlparse
import requests
from kafka import KafkaConsumer
import time
import threading
import consul
import uuid
import os

app = FastAPI()

def register_service(service_name, service_id, service_ip, service_port, consul_ip, consul_port):
    consul_client = consul.Consul(host=consul_ip, port=consul_port)

    consul_client.agent.service.register(
    name=service_name,
    service_id=service_id,
    address=service_ip,
    port=service_port,
    check=consul.Check.http(
        url=f"http://{service_ip}:{consul_ip}/health",
        interval="10s",
        timeout="1s",
        deregister="10m"
    )
)

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
        write_log("Kafka Consumer Connected", host_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)
        return

    while consumer_running:
        records = consumer.poll(timeout_ms=CONSUMER_POLL_TIME_OUT_MS)
        for tp, msgs in records.items():
            for msg in msgs:
                messages.append(msg.value.decode())
                write_log(f"New message received: {msg.value.decode()}", host_port)
        
        time.sleep(POLL_INTERVAL) 

@app.on_event("startup")
def start_consumer():
    try:
        register_service(service_name, service_id, host_ip, host_port, consul_ip, consul_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)
        return


    thread = threading.Thread(target=consume_messages, daemon=True)
    thread.start()



# Handle the startup event
@app.on_event("shutdown")
async def event_shutdown():
    consul_client = consul.Consul(host=consul_ip, port=consul_port)
    consul_client.agent.service.deregister(service_id)

@app.get('/health')
def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)

@app.get("/")
def get_data():
    write_log("GET request", host_port)

    write_log(f"GET request response: {messages}", host_port)
    return {"msg": messages}

if __name__ == "__main__":
    POLL_INTERVAL = 3
    TOPIC_NAME = "messages"
    KAFKA_GROUP_ID = "messages_group"
    CONSUMER_POLL_TIME_OUT_MS = 1000

    messages = []
    consumer_running = True
    host_port = 1111

    try:
        service_name = os.path.basename(sys.argv[0])
        service_id = f"{service_name}-{str(uuid.uuid4())[:4]}"

        host_url = urlparse(sys.argv[1].strip())
        config_server_url = sys.argv[2].strip()
        messages_service_idx = int(sys.argv[3])

        kafka_services = get_service_ips("kafka-services")
        write_log(f"List: {kafka_services}", host_port)

        kafka_url = kafka_services[messages_service_idx]

        host_port = host_url.port
        host_ip = host_url.hostname

        consul_ip = sys.argv[4].strip()
        consul_port = int(sys.argv[5])
        write_log(f"List: {sys.argv}", host_port)

    except Exception as e:
        write_log(f"Exception {e}", host_port)
    


    write_log(f"Starting up server: {host_url.hostname}:{host_port}", host_port)
    uvicorn.run(app, host=host_ip, port=host_port)
