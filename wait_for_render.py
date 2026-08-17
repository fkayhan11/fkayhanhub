import requests
import time

url = "https://fkayhanhub.onrender.com/convert-md"
print("Waiting for Render to come up...")

while True:
    try:
        resp = requests.post(url, json={"text": "ping"}, timeout=15)
        if resp.status_code in [200, 404, 500, 422]:
            print("\nRENDER IS UP AND RESPONDING! Status:", resp.status_code)
            break
    except Exception as e:
        pass
    time.sleep(10)
