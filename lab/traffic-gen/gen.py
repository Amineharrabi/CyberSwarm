"""
Legitimate-user simulator. Produces the "normal" traffic class and the availability metric:
if these requests start failing, the webapp is down (Blue over-blocked or Red broke it).
"""
import os
import time
import random
import requests

TARGET = os.environ.get("TARGET", "http://10.10.2.10:5000")
USERS = [("alice", "password123"), ("bob", "hunter2")]
SEARCHES = ["Widget", "Gadget", "Cog", "Sprocket", ""]


def one_cycle():
    try:
        requests.get(f"{TARGET}/", timeout=5)
        requests.get(f"{TARGET}/products", params={"q": random.choice(SEARCHES)}, timeout=5)
        u, p = random.choice(USERS)
        requests.post(f"{TARGET}/login", data={"username": u, "password": p}, timeout=5)
        requests.get(f"{TARGET}/download", params={"file": "readme.txt"}, timeout=5)
        print("[traffic] legit cycle ok", flush=True)
    except Exception as e:
        print(f"[traffic] request failed: {e}", flush=True)


if __name__ == "__main__":
    print(f"[traffic] generating legit load against {TARGET}", flush=True)
    while True:
        one_cycle()
        time.sleep(random.uniform(1.5, 4.0))   # randomised so flows look human
