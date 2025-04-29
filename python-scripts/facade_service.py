from fastapi.responses import JSONResponse
from util_functions import write_log
from urllib.parse import urlparse
from kafka import KafkaProducer
from fastapi import FastAPI
from random import shuffle
import requests
import uvicorn
import consul
import uuid
import json
import time
import sys
import os

app = FastAPI()

def get_service_ips_consul(service_name: str):
    consul_client = consul.Consul(host=consul_ip, port=consul_port)

    services = consul_client.agent.services()

    service_name = service_name.replace("-", "_")
    result_ips = []

    for service_id, service_info in services.items():
        if service_name == service_info["Service"][:-3]:
            result_ips.append(f"{service_info['Address']}:{service_info['Port']}")

    return result_ips

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

@app.on_event("startup")
def start_consumer():
    try:
        register_service(service_name, service_id, host_ip, host_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)
        return

@app.on_event("shutdown")
async def event_shutdown():
    consul_client.agent.service.deregister(service_id)

def send_message_to_queue(message):
    write_log(f"Writing message {message} to the queue", host_port)
    
    producer = KafkaProducer(bootstrap_servers=kafka_urls)
    producer.send(TOPIC_NAME, bytes(message, "UTF-8"))
    producer.flush()

@app.post("/")
def add_data(message: dict):
    write_log("POST request", host_port)

    uuid_val = uuid.uuid4()
    message_value = message.get("msg", "")
    data = {"uuid": str(uuid_val), "msg": message_value}
    shuffled_urls = logging_urls[:]

    shuffle(shuffled_urls)

    for logging_service_url in shuffled_urls:
        try:
            logging_service_url = "http://" + logging_service_url
            response = requests.post(logging_service_url, json=data, timeout=3)
            if response.status_code == 200:
                write_log(f"Sending message {message_value} to the logging service", host_port)
                break
        except requests.exceptions.RequestException as e:
            return {"error": f"Error with logging service {logging_service_url}: {e}"}
        
    send_message_to_queue(message_value)
    
    return {"msg": "success"}

@app.get('/health')
def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)

@app.get("/")
def get_data():
    write_log("GET request", host_port)
    shuffled_logging_urls = logging_urls[:]
    shuffled_messages_urls = messages_urls[:]
    
    shuffle(shuffled_logging_urls)
    shuffle(shuffled_messages_urls)
    
    logging_service_messages = {"error": "No logging service available"}
    messages_service_messages = {"error": "Messages service unavailable"}
    write_log(f"Shuffled logging service: {shuffled_logging_urls}", host_port)
    write_log(f"Shuffled logging service: {shuffled_messages_urls}", host_port)

    for logging_url in shuffled_logging_urls:
        try:
            logging_url = "http://" + logging_url
            write_log(f"Trying to connect to logging service: {logging_url}", host_port)
            logging_service_response = requests.get(logging_url, timeout=3)
            if logging_service_response.status_code == 200:
                logging_service_messages = json.loads(logging_service_response.content.decode("utf-8"))
                write_log(f"Connected successfully", host_port)
                break
        except requests.exceptions.RequestException as e:
            print({"err" : f"Error with logging service {logging_url}: {e}"})

    for messages_url in shuffled_messages_urls:
        try:
            write_log(f"Trying to connect to messages service: {messages_url}", host_port)
            messages_service_response = requests.get(messages_url, timeout=10)
            if messages_service_response.status_code == 200:
                messages_service_messages = json.loads(messages_service_response.content.decode("utf-8"))["msg"]
                write_log(f"Connected successfully", host_port)
                break
        except requests.exceptions.RequestException as e:
            print({"err": f"Error with messages service {messages_url}: {e}"})

    GET_request_response = {
        "logging_service_response": logging_service_messages,
        "messages_service_response": messages_service_messages}

    write_log(f"GET request response: {GET_request_response}", host_port)

    return GET_request_response

if __name__ == "__main__":
    TOPIC_NAME = "messages"

    host_url = urlparse(sys.argv[1])
    config_server_url = sys.argv[2]

    consul_ip = sys.argv[3].strip()
    consul_port = int(sys.argv[4])

    host_ip = host_url.hostname
    host_port = host_url.port

    service_name = os.path.basename(sys.argv[0])
    service_id = f"{service_name}-{str(uuid.uuid4())[:4]}"

    time.sleep(10)

    messages_urls = get_service_ips_consul("messages-service")
    logging_urls = get_service_ips_consul("logging-service")

    consul_client = consul.Consul(host=consul_ip, port=consul_port)

    _, data = consul_client.kv.get("kafka_urls")
    kafka_urls = json.loads(data['Value'])

    write_log(f"Messages urls from consul: {messages_urls}", host_port)
    write_log(f"Logging urls from consul: {logging_urls}", host_port)

    write_log(f"Starting up server {host_ip}:{host_port}", host_port)
    uvicorn.run(app, host=host_ip, port=host_port)
