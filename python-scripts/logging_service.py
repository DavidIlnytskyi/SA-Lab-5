from util_functions import write_log
from urllib.parse import urlparse
from fastapi import FastAPI
from domain import *
import consul
import hazelcast
import uvicorn
import random
import uuid
import json
import sys
import os

app = FastAPI()

def register_service(service_name, service_id, service_ip, service_port, consul_ip, consul_port):
    consul_client.agent.service.register(
        name=service_name,
        service_id=service_id,
        address=service_ip,
        port=service_port,
        check=consul.Check.http(
            url=f"http://{service_ip}:{consul_ip}/health",
            interval="10s",
            timeout="1s",
            deregister="10m")
    )

@app.post("/")
def add_data(data: DataModel):
    write_log("Post request", host_port)
    write_log(f"Added key: {data.uuid} with value: {data.msg} by logging service: {host_url}", host_port)
    distributed_map.set(data.uuid, data.msg)

    return {"msg": "success"}

@app.get("/")
def get_data():
    write_log("Get request", host_port)

    messages = distributed_map.entry_set()
    return {"messages": messages}

@app.on_event("startup")
def startup_event():
    try:
        global distributed_map, client

        write_log("Connecting to Hazelcase client", host_port)
        client = hazelcast.HazelcastClient(cluster_members=[hazelcast_url])
        distributed_map = client.get_map("my-distributed-map").blocking()

        write_log("Connected to Hazelcase client", host_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)

    try:
        register_service(service_name, service_id, host_ip, host_port, consul_ip, consul_port)
    except Exception as e:
        write_log(f"Kafka Consumer Failed: {e}", host_port)
    return

@app.on_event("shutdown")
async def event_shutdown():
    consul_client = consul.Consul(host=consul_ip, port=consul_port)
    consul_client.agent.service.deregister(service_id)


if __name__ == "__main__":
    distributed_map = None
    client = None
    host_port = 2222
    try:
        host_url = urlparse(sys.argv[1])
        hazelcast_idx = int(sys.argv[2])

        consul_ip = sys.argv[3].strip()
        consul_port = int(sys.argv[4])

        consul_client = consul.Consul(host=consul_ip, port=consul_port)

        index, data = consul_client.kv.get("hazelcast_urls")
        hazelcast_nodes = json.loads(data['Value'])

        if hazelcast_idx < len(hazelcast_nodes):
            hazelcast_url = hazelcast_nodes[hazelcast_idx]
        elif len(hazelcast_nodes) > 0:
            hazelcast_url = hazelcast_nodes[random.randint(0, len(hazelcast_nodes) - 1)]

        service_name = os.path.basename(sys.argv[0])
        service_id = f"{service_name}-{str(uuid.uuid4())[:4]}"

        host_ip = host_url.hostname
        host_port = host_url.port
    except Exception as e:
        write_log(f"Exception {e}", host_port)

    write_log(f"Starting up server {host_ip}:{host_port}", host_port)
    uvicorn.run(app, host=host_ip, port=host_port)
