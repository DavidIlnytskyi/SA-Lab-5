from fastapi.responses import JSONResponse
from util_functions import write_log
from urllib.parse import urlparse
from kafka import KafkaConsumer
from fastapi import FastAPI
import threading
import uvicorn
import sys
import time
import consul
import uuid
import json
import os

app = FastAPI()


def get_value(key, default=None, deserialize_json=False, cast_type=None):
    _, data = consul_client.kv.get(key)
    if not data or "Value" not in data:
        return default
    value = data["Value"]
    if deserialize_json:
        value = json.loads(value)
    if cast_type:
        value = cast_type(value)
    return value

def register_service(service_name, service_id, service_ip, service_port):
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=service_ip,
        port=service_port,
        check=consul.Check.http(
            url=f"http://{service_ip}:{service_port}/health",
            interval="10s",
            timeout="1s",
            deregister="10m")
    )

def consume_messages():
    global messages

    topic_name = get_value("topic_name").decode("utf-8")
    kafka_group_id = get_value("group_id").decode("utf-8")
    kafka_urls = get_value("kafka_urls", deserialize_json=True)
    auto_offset_reset_value = get_value("auto_offset_reset").decode("utf-8")
    enable_auto_commit_value = get_value("enable_auto_commit", deserialize_json=True)
    api_version = tuple(get_value("api_version", deserialize_json=True))
    request_timeout_ms = get_value("request_timeout_ms", cast_type=int)

    try:
        consumer = KafkaConsumer(
            topic_name,
            bootstrap_servers=kafka_urls,
            auto_offset_reset=auto_offset_reset_value,
            enable_auto_commit=enable_auto_commit_value,
            group_id=kafka_group_id,
            api_version=api_version,
            request_timeout_ms=request_timeout_ms
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
        register_service(service_name, service_id, host_ip, host_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)
        return

    thread = threading.Thread(target=consume_messages, daemon=True)
    thread.start()

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

        host_port = host_url.port
        host_ip = host_url.hostname

        consul_ip = sys.argv[4].strip()
        consul_port = int(sys.argv[5])

        consul_client = consul.Consul(host=consul_ip, port=consul_port)

        _, data = consul_client.kv.get("kafka_urls")
        kafka_services = json.loads(data['Value'])
        kafka_url = kafka_services[messages_service_idx]

        write_log(f"List Kafka: {kafka_services}", host_port)
        write_log(f"List Args: {sys.argv}", host_port)

    except Exception as e:
        write_log(f"Exception {e}", host_port)

    write_log(f"Starting up server: {host_ip}:{host_port}", host_port)
    uvicorn.run(app, host=host_ip, port=host_port)
