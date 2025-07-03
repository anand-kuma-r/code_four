import time
import requests
import json

# ——— CONFIG ———
BASE_URL = "http://localhost:8000"   # adjust if your API is hosted elsewhere
JOB_ID   = "024d8b77-9d82-4c9d-b3c3-fa8fbe0bb16d"
INTERVAL = 5   # seconds between polls
# ————————

def check_status():
    url = f"{BASE_URL}/v1/analyze/status/{JOB_ID}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
        return None

    data = resp.json()
    print(json.dumps(data, indent=2))
    return data.get("status")

def main():
    print(f"Polling job {JOB_ID} every {INTERVAL}s…\n")
    while True:
        status = check_status()
        if status in ("COMPLETE", "FAILED"):
            print(f"\nJob {JOB_ID} finished with status: {status}")
            break
        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
