import requests, json
r = requests.get('http://127.0.0.1:8000/api/game/list')
print(r.status_code)
print(r.text)
