"""
Mistral API テストスクリプト
各種サンプリングパラメータの動作確認用
"""

import os
import sys
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from mistralai import Mistral

# .env から API キーを読み込む
load_dotenv("backend/.env")
api_key = os.environ.get("MISTRAL_API_KEY")

if not api_key:
    raise ValueError("MISTRAL_API_KEY が設定されていません。backend/.env を確認してください。")

client = Mistral(api_key=api_key)
model = "ministral-3b-latest"

# ----------------------------------------------------------------
# 1. 基本的なチャット
# ----------------------------------------------------------------
print("=" * 50)
print("1. 基本チャット")
print("=" * 50)

response = client.chat.complete(
    model=model,
    messages=[
        {"role": "user", "content": "こんにちは！自己紹介を一言でお願いします。"}
    ],
)
print(response.choices[0].message.content)

# ----------------------------------------------------------------
# 2. Temperature の比較 (低 vs 高)
# ----------------------------------------------------------------
print("\n" + "=" * 50)
print("2. Temperature 比較 (同じ質問を3回)")
print("=" * 50)

question = "最強の神話上の生き物を一言で答えてください。"

for temp, label in [(0.1, "低 (0.1)"), (1.0, "高 (1.0)")]:
    print(f"\n--- Temperature {label} ---")
    resp = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": question}],
        temperature=temp,
        n=3,
    )
    for i, choice in enumerate(resp.choices):
        print(f"  [{i+1}] {choice.message.content}")

# ----------------------------------------------------------------
# 3. Top P の効果
# ----------------------------------------------------------------
print("\n" + "=" * 50)
print("3. Top P サンプリング (temperature=1, top_p=0.5)")
print("=" * 50)

resp = client.chat.complete(
    model=model,
    messages=[{"role": "user", "content": question}],
    temperature=1,
    top_p=0.5,
    n=5,
)
for i, choice in enumerate(resp.choices):
    print(f"  [{i+1}] {choice.message.content}")

# ----------------------------------------------------------------
# 4. Presence / Frequency Penalty の比較
# ----------------------------------------------------------------
print("\n" + "=" * 50)
print("4. Penalty 比較 (ファンタジー本タイトル5個)")
print("=" * 50)

prompt = "ファンタジー小説のタイトルを5つリストアップしてください。リストのみ出力。"

for penalty_type, kwargs, label in [
    ("なし",              {},                          "ペナルティなし"),
    ("presence_penalty", {"presence_penalty": 2},     "Presence Penalty=2"),
    ("frequency_penalty",{"frequency_penalty": 2},    "Frequency Penalty=2"),
]:
    print(f"\n--- {label} ---")
    resp = client.chat.complete(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        **kwargs,
    )
    print(resp.choices[0].message.content)

print("\n✅ テスト完了")
