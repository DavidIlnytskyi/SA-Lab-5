from util_functions import write_log
from urllib.parse import urlparse
from fastapi import FastAPI
from domain import *
import hazelcast
import uvicorn
import sys

app = FastAPI()

distributed_map = None
client = None
host_url = None
port = None

@app.post("/")
def add_data(data: DataModel):
    write_log("Post request", port)
    write_log(f"Added key: {data.uuid} with value: {data.msg} by logging service: {host_url}", port)
    distributed_map.set(data.uuid, data.msg)
    return {"msg": "success"}

@app.get("/")
def get_data():
    write_log("Get request", port)

    messages = distributed_map.entry_set()
    return {"messages": messages}

@app.on_event("startup")
def startup_event():

    global distributed_map, client, host_url, port

    if len(sys.argv) < 3:
        print("Usage: python main.py <host_url> <hazelcast_url>")
        sys.exit(1)

    host_url = sys.argv[1]
    hazelcast_url = sys.argv[2]

    parsed_url = urlparse(host_url)
    port = parsed_url.port

    write_log("Connecting to Hazelcase client", port)
    client = hazelcast.HazelcastClient(cluster_members=[hazelcast_url])
    distributed_map = client.get_map("my-distributed-map").blocking()

    write_log("Connected to Hazelcase client", port)

if __name__ == "__main__":
    parsed_url = urlparse(sys.argv[1])

    port = parsed_url.port
    
    write_log(f"Starting up server {parsed_url.hostname}:{port}", port)
    uvicorn.run(app, host=parsed_url.hostname, port=port)
