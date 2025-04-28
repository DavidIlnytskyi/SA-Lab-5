import consul
import sys
import uuid
import socket
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    SERVICE_NAME = sys.argv[0][:-3]
    SERVICE_ID = f"{SERVICE_NAME}-{str(uuid.uuid4())[:4]}"

    CONSUL_IP = "172.24.0.2"
    CONSUL_PORT = 8500

    SERVICE_IP = socket.gethostbyname(socket.gethostname())
    SERVICE_PORT = 5000

    c = consul.Consul(host=CONSUL_IP, port=CONSUL_PORT)

    c.agent.service.register(
        name=SERVICE_NAME,
        service_id=SERVICE_ID,
        address=SERVICE_IP,
        port=SERVICE_PORT,
        check=consul.Check.http(
            url=f"http://{SERVICE_IP}:{SERVICE_PORT}/health",
            interval="10s",
            timeout="1s",
            deregister="30m"))

    yield

    c.agent.service.deregister(SERVICE_ID)



app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}

@app.get('/health')
def health_check():
    return JSONResponse(content={"status": "healthy"}, status_code=200)
