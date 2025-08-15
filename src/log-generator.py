import json
import random
import uuid
from datetime import datetime, timedelta
from faker import Faker
import sys
import os
import time

fake = Faker()

applications = [f"app{i}" for i in range(1, 11)]
namespaces = [f"namespace-{i}" for i in range(1, 6)]
log_levels = ["INFO", "WARN", "ERROR", "DEBUG"]

node_actions = ["ScaledUp", "ScaledDown"]
pod_events = ["PodDeleted", "PodCrashLoopBackOff", "OOMKilled"]

# Burst state tracking
current_burst = None
burst_end_time = None

def start_burst(timestamp):
    """Start a burst pattern."""
    global current_burst, burst_end_time
    burst_type = random.choice(["pod_crash", "scale_up"])
    duration_minutes = random.randint(2, 5)
    burst_end_time = timestamp + timedelta(minutes=duration_minutes)
    current_burst = burst_type
    return burst_type

def end_burst():
    """End the current burst."""
    global current_burst, burst_end_time
    current_burst = None
    burst_end_time = None

def generate_event(timestamp):
    """Generate either a normal log or a special event, with burst simulation."""
    global current_burst, burst_end_time

    # Randomly start bursts
    if current_burst is None and random.random() < 0.01:  # ~1% chance to start a burst
        start_burst(timestamp)

    # End burst if time passed
    if current_burst and timestamp > burst_end_time:
        end_burst()

    app = random.choice(applications)
    namespace = random.choice(namespaces)
    pod = f"{app}-pod-{random.randint(1,5)}"
    container = f"{app}-container"

    log = {
        "timestamp": timestamp.isoformat() + "Z",
        "namespace": namespace,
        "pod": pod,
        "container": container,
        "application": app,
        "cluster": "aks-demo-cluster",
        "node": f"aks-nodepool-{random.randint(1,3)}",
        "hostIP": fake.ipv4(),
        "podIP": fake.ipv4_private(),
        "traceId": str(uuid.uuid4()),
    }

    # Default metrics
    log["cpuUsage"] = round(random.uniform(0.1, 2.5), 2)  # in cores
    log["memoryUsageMB"] = random.randint(50, 1500)       # in MB

    # If in burst mode, generate specific events
    if current_burst == "pod_crash":
        log["cpuUsage"] = round(random.uniform(1.5, 3.0), 2)
        log["memoryUsageMB"] = random.randint(1000, 3000)
        event = random.choice(["PodCrashLoopBackOff", "OOMKilled"])
        log["eventType"] = event
        log["level"] = "ERROR"
        log["message"] = f"{event} occurred for pod {pod} in namespace {namespace}"
        return log

    if current_burst == "scale_up":
        # First half of burst: scale up
        if timestamp < burst_end_time - timedelta(minutes=1):
            log["eventType"] = "NodeScaledUp"
            log["level"] = "INFO"
            log["message"] = f"Node scaled up in cluster aks-demo-cluster"
        else:
            log["eventType"] = "NodeScaledDown"
            log["level"] = "INFO"
            log["message"] = f"Node scaled down in cluster aks-demo-cluster"
        return log

    # If not in burst: mostly normal logs, occasional pod/node events
    event_type = random.choices(
        ["normal", "pod_event", "node_event"],
        weights=[85, 10, 5]
    )[0]

    if event_type == "normal":
        log["level"] = random.choice(log_levels)
        log["message"] = fake.sentence(nb_words=random.randint(6, 12))
    elif event_type == "pod_event":
        event = random.choice(pod_events)
        log["level"] = "WARN" if event != "OOMKilled" else "ERROR"
        log["eventType"] = event
        log["message"] = f"{event} occurred for pod {pod} in namespace {namespace}"
    else:  # node_event
        action = random.choice(node_actions)
        log["level"] = "INFO"
        log["eventType"] = f"Node{action}"
        log["message"] = f"Node {action} in cluster aks-demo-cluster"

    return log

def generate_logs_for_day(date_str, num_logs=2000, output_dir="input-logs"):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    logs = []
    os.makedirs(output_dir, exist_ok=True)

    for i in range(num_logs):
        seconds_offset = int((86400 / num_logs) * i)
        log_time = date + timedelta(seconds=seconds_offset)
        logs.append(generate_event(log_time))

    file_path = os.path.join(output_dir, f"aks_logs_{date_str}.json")
    with open(file_path, "w") as f:
        json.dump(logs, f, indent=2)

    print(f"Generated {len(logs)} logs for {date_str} → {file_path}")

def stream_logs(interval_seconds=2):
    """Continuously generate logs in real time."""
    while True:
        log = generate_event(datetime.utcnow())
        print(json.dumps(log))
        time.sleep(interval_seconds)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python aks_log_generator.py YYYY-MM-DD [num_logs]")
        print("  python aks_log_generator.py stream [interval_seconds]")
        sys.exit(1)

    if sys.argv[1] == "stream":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 2
        stream_logs(interval)
    else:
        date_str = sys.argv[1]
        num_logs = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
        generate_logs_for_day(date_str, num_logs)
