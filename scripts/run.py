import requests

with open(r"C:\Users\anand\Downloads\gum.mp4", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/v1/analyze", files=files)
print(response.status_code)
print(response.json())