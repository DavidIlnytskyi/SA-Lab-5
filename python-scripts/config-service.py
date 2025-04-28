from fastapi import FastAPI, HTTPException
from configparser import ConfigParser
from typing import List
import uvicorn
from urllib.parse import urlparse
import sys

app = FastAPI()

def load_ips(file: str = "config.ini") -> dict:
    config = ConfigParser()
    config.read(file)
    ip_data = {}
    
    for section in config.sections():
        ip_data[section] = config.get(section, "ips").split(',')
    
    return ip_data

ip_registry = load_ips()

@app.get("/services/{service_name}", response_model=List[str])
def get_service_ips(service_name: str):
    if service_name in ip_registry:
        return ip_registry[service_name]
    raise HTTPException(status_code=404, detail="Service not found")

if __name__ == "__main__":
    host_url = urlparse(sys.argv[1])

    uvicorn.run(app, host=host_url.hostname, port=host_url.port)