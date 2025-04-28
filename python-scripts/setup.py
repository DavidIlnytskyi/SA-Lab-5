import subprocess
import configparser
import os
import signal

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

    try:
        config_service_ip = config["config-service"].get("ips")
        if config_service_ip:
            process = start_service("Config Service", "config-service", config_service_ip)
            if process:
                processes.append(process)

        messages_service_ip = config["messages-services"].get("ips").split(", ")
        kafka_service_ip = config["kafka-services"].get("ips").split(", ")

        for idx, msg_ip in enumerate(messages_service_ip):
            process = start_service(f"Messages Service {idx+1}", "messages_service", msg_ip, config_service_ip, str(idx))
            if process:
                processes.append(process)

        logging_services = config["logging-services"].get("ips", "").split(", ")
        hazelcast_nodes = config["hazelcast"].get("ips", "").split(", ")
        
        for idx, (log_ip, hazel_ip) in enumerate(zip(logging_services, hazelcast_nodes)):
            process = start_service(f"Logging Service {idx+1}", "logging_service", log_ip, hazel_ip)
            if process:
                processes.append(process)

        facade_service_ip = config["facade-service"].get("ips")
        if messages_service_ip:
            process = start_service("Facade Service", "facade_service", facade_service_ip, config_service_ip)
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
