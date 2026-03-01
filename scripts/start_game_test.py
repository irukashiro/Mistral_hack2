import requests
import json
resp = requests.post('http://127.0.0.1:8000/api/game/start', json={'npc_count':4,'player_name':'テストプレイヤー','game_mode':'lite'})
print(resp.status_code)
try:
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False)[:8000])
except Exception:
    print(resp.text)
