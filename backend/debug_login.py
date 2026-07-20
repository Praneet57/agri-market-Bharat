import json
import urllib.request

URL = "http://localhost:8000/api/v1/auth/login"
DATA = {"phone": "9000000003", "password": "admin123"}

req = urllib.request.Request(
    URL,
    data=json.dumps(DATA).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(req) as resp:
    body = resp.read().decode("utf-8")
    print(resp.status)
    print(body)

