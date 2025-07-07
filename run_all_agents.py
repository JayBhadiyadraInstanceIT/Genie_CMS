import subprocess
import time
from constants import (
    REMOTE_1_AGENT_NAME,
    REMOTE_1_AGENT_PORT,
)

AGENTS = [
    (REMOTE_1_AGENT_NAME, "cms_agent_adk", REMOTE_1_AGENT_PORT),
]


def start_agents():
    processes = []
    for name, path, port in AGENTS:
        print(f"Starting {name} on port {port}...")
        proc = subprocess.Popen(["python", path])
        processes.append(proc)
        time.sleep(1)  # Small delay to help avoid port race conditions
    return processes


if __name__ == "__main__":
    try:
        procs = start_agents()
        print("✅ All agents launched. Keep this window open.")
        print("➡ Now open another terminal and run the host agent")
        for p in procs:
            p.wait()
    except KeyboardInterrupt:
        print("🛑 Stopping all agents...")
        for p in procs:
            p.terminate()
