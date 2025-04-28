import subprocess
import configparser
import signal
import consul
import json
import os

config = configparser.ConfigParser()
config.read('./config.ini')

def start_service(service_name, script_name, *args):
    print(f"Starting {service_name}...")
    
    try:
        request = ["python3", f"./python-scripts/{script_name}.py", *args]
        print(request)
        return subprocess.Popen(request, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
    except Exception as e:
        print(f"Error starting {service_name}: {e}")
        return None

if __name__ == "__main__":
    processes = []

    import json

    TOPIC_NAME = "messages"
    KAFKA_GROUP_ID = "messages_group"
    kafka_url = ["localhost:9092", "localhost:9093"]  # Assuming list
    auto_offset_reset = "latest"
    enable_auto_commit = True
    api_version = (2, 0, 2)
    request_timeout_ms = 15000


    try:
        consul_service_url = config["consul-service"].get("ips")
        consul_service_ip = consul_service_url[:consul_service_url.find(":")]
        consul_service_port = consul_service_url[consul_service_url.find(":")+1:]

        config_service_ip = config["config-service"].get("ips")
        if config_service_ip:
            process = start_service("Config Service", "config-service", config_service_ip)
            if process:
                processes.append(process)

        messages_service_ip = config["messages-services"].get("ips").split(", ")
        kafka_service_ip = config["kafka-services"].get("ips").split(", ")

        for idx, msg_ip in enumerate(messages_service_ip):
            process = start_service(f"Messages Service {idx+1}", "messages_service", msg_ip, config_service_ip, str(idx), consul_service_ip, consul_service_port)
            if process:
                processes.append(process)

        logging_services = config["logging-services"].get("ips", "").split(", ")
        hazelcast_nodes = config["hazelcast"].get("ips", "").split(", ")

        consul_client = consul.Consul(host="127.0.0.1", port=8500)

        hazelcast_nodes_json = json.dumps(hazelcast_nodes)

        consul_client.kv.put("hazelcast_urls", hazelcast_nodes_json)
        consul_client.kv.put("topic_name", TOPIC_NAME)
        consul_client.kv.put("group_id", KAFKA_GROUP_ID)
        consul_client.kv.put("kafka_urls", json.dumps(kafka_url))
        consul_client.kv.put("auto_offset_reset", auto_offset_reset)
        consul_client.kv.put("enable_auto_commit", json.dumps(enable_auto_commit))
        consul_client.kv.put("api_version", json.dumps(api_version))
        consul_client.kv.put("request_timeout_ms", str(request_timeout_ms))



        hazel_idx = 0
        for idx, (log_ip, hazel_ip) in enumerate(zip(logging_services, hazelcast_nodes)):
            process = start_service(f"Logging Service {idx+1}", "logging_service", log_ip, str(hazel_idx), consul_service_ip, consul_service_port)
            if process:
                processes.append(process)
                hazel_idx += 1

        facade_service_ip = config["facade-service"].get("ips")
        if messages_service_ip:
            process = start_service("Facade Service", "facade_service", facade_service_ip, config_service_ip, consul_service_ip, consul_service_port)
            if process:
                processes.append(process)

        while True:
            pass
    
    except KeyboardInterrupt:
        print("\nShutting down all servers...")

        for process in processes:
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        print("All servers stopped.")
