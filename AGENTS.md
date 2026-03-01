# AGENTS.md — Class Conflict: Millionaire (大富豪×人狼)
トランプの「大富豪」と「人狼ゲーム」を融合させたAI駆動型・正体隠匿アドベンチャーカードゲームです。
生成AIがプレイのたびにキャラクターの秘匿された「人物像」や「裏の勝利条件」を自動生成し、人狼ゲームを展開します。
最大の特徴は、貧民が下克上を狙う【イカサマ対決】。プレイヤーが自由なプロンプトで「ズルの手口」と「対策」を入力し、AIが成功判定を行います。カードと議論を武器に、論理と感情で動くNPCたちを説き伏せて勝利を目指せ


思考は英語で行い、最終的な出力は必ず日本語で提供してください。

---

## プロジェクト概要

Mistral AIハッカソン向けブラウザゲーム。**大富豪（カードゲーム）× 人狼（議論・投票）× AI生成キャラクター**の3要素を組み合わせた対話型ゲーム。

- **バージョン**: v4.1 (Lite mode only)
- **現在のブランチ**: `lite-only`
- **実行**: `cd backend && uvicorn main:app --reload` → `http://localhost:8000`
- **環境変数**: `MISTRAL_API_KEY` を `backend/.env` に設定

**ハッカソン向け方針**: Liteモードのみ提供。Hardモードのセットアップ画面は削除済み。

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│  ブラウザ (http://localhost:8000)                            │
│  frontend/index.html + app.js + style.css                   │
│  Vanilla JS、フレームワークなし、ビルドツールなし              │
└────────────────────────┬────────────────────────────────────┘
                         │ fetch (同一オリジン)
┌────────────────────────▼────────────────────────────────────┐
│  FastAPI (backend/main.py)                                   │
│  - 静的ファイル配信: /static → ../frontend/                   │
│  - APIエンドポイント: /api/game/*  (29エンドポイント)          │
│  - インメモリ状態管理: game_store: Dict[str, GameState]       │
├──────────────────────────────────────────────────────────────┤
│  backend/game_engine.py  │ 純粋関数: デッキ・役判定・ターン管理│
│  backend/ai_service.py   │ Mistral AI連携: 非同期関数群      │
│  backend/models.py       │ Pydantic v2: 20+クラス            │
└──────────────────────────────────────────────────────────────┘
                         │ Mistral API
                         ▼
              mistral-large-latest (生成・審判)
              mistral-small-latest (発言・投票・カード)
```

**重要な制約**:
- サーバー再起動でゲームデータ消失（DB永続化なし）
- 単一ゲーム想定（ハッカソン向け割り切り）
- CORS: `allow_origins=["*"]`（開発専用）
- インポートは絶対インポート（`from ai_service import ...`）— 相対インポート不可

---

## ファイルマップ

| ファイル | 行数 | 責務 |
|---------|------|------|
| `backend/main.py` | ~1680 | FastAPIアプリ本体。29エンドポイント定義、状態管理、情報隠蔽 |
| `backend/game_engine.py` | ~1065 | 純粋関数群。デッキ生成・配布・役判定・プレイ検証・ターン進行・勝利判定・チート効果適用 |
| `backend/ai_service.py` | ~2395 | Mistral AI連携。キャラ生成・NPC発言・投票・カードプレイ・イカサマ審判・Liteモード対応 |
| `backend/models.py` | ~401 | Pydantic v2モデル。`GameState`, `Character`, `Card`, `CheatEffect` 等 |
| `frontend/app.js` | ~2184 | Vanilla JS。ゲーム状態管理・全API呼び出し・DOM描画 |
| `frontend/index.html` | - | 3画面（セットアップ/ゲーム/リザルト）のHTMLシェル。モード選択なし（Lite固定） |
| `frontend/style.css` | ~2251 | 黒×金のダークゴシックテーマ（CSS Custom Properties） |

---

## Liteモード仕様

ハッカソン向けメインモード。

- **人数**: 5人固定（1 FUGO + 1 HINMIN + 3 HEIMIN）
- **キャラ生成**: 職業・性格・顔見知り1名のみ（軽量）
- **Detective**: 1名が探偵ロールを兼任 — 夜/昼に1回だけ調査可能
- **伏線NPC発言**: `generate_lite_npc_speeches()` — FUGOはカードの強さを遠回しに示唆、HINMINは富豪への疑惑を煽る
- **Hate投票**: `decide_npc_lite_vote()` — カード証拠・イカサマ露見・会議発言ベースで投票
- **陽動イカサマ**: `judge_lite_cheat_decoy()` — 【陽動】+【本命】2部入力、防御者は15文字/5秒制限
  - 陽動に引っかかる → `big_success`（カード強奪、バレない）
  - 本命ガード → `draw`（失敗、バレない）
  - 身体的制圧 → `big_fail`（露見）
- **オートデイ**: `POST /api/game/lite/auto-day` — 昼チャット・投票・処刑・夜移行を一括実行

---

## APIエンドポイント一覧

### ゲーム管理
| Method | パス | 機能 |
|--------|------|------|
| `GET` | `/` | index.html配信 |
| `GET` | `/api/game/state` | ゲーム状態取得（情報隠蔽あり） |
| `GET` | `/api/game/hints` | AI生成ヒント + 定型文（昼のみ） |
| `GET` | `/api/game/debug-state` | 神の目モード（全情報開示） |
| `GET` | `/api/game/result` | リザルト画面用全情報開示 |
| `GET` | `/api/game/list` | 稼働中ゲーム一覧（デバッグ） |
| `POST` | `/api/game/{game_id}/delete` | ゲーム削除 |

### Hardモード（セットアップ画面からは削除済み・バックエンドは残存）
| Method | パス | 機能 |
|--------|------|------|
| `POST` | `/api/game/start` | Hardモード開始 |
| `POST` | `/api/game/chat` | プレイヤー発言 → NPC応答 |
| `POST` | `/api/game/vote` | プレイヤー投票 |
| `POST` | `/api/game/npc-votes` | NPC全員投票 |
| `POST` | `/api/game/finalize-vote` | 処刑確定 → 夜移行 |
| `POST` | `/api/game/cheat-initiate` | 人間が仕掛ける |
| `POST` | `/api/game/cheat-defend` | 人間が防御する |
| `POST` | `/api/game/cheat-skip` | 人間がスキップ |
| `POST` | `/api/game/cheat-phase-complete` | フェーズ終了 → カードプレイ開始 |
| `POST` | `/api/game/play-cards` | カードを出す → NPC連鎖プレイ |
| `POST` | `/api/game/pass` | パス → NPC連鎖プレイ |
| `POST` | `/api/game/night-chat` | 夜チャット |
| `POST` | `/api/game/ghost-advance` | ゴーストモード: NPCターン強制進行 |
| `POST` | `/api/game/end-night` | 夜を手動終了 → 翌日へ |
| `POST` | `/api/game/auto-play` | オートプレイ |

### Liteモード
| Method | パス | 機能 |
|--------|------|------|
| `POST` | `/api/game/start-lite` | Liteモード開始 |
| `POST` | `/api/game/lite/chat` | 昼チャット（伏線付きNPC発言） |
| `POST` | `/api/game/lite/npc-votes` | Lite Hate投票 |
| `POST` | `/api/game/lite/cheat-decoy` | 陽動+本命入力 |
| `POST` | `/api/game/lite/cheat-react` | 防御者リアクション（15文字制限） |
| `POST` | `/api/game/lite/detective-investigate` | 探偵調査（昼/夜フェーズで使用可） |
| `POST` | `/api/game/lite/auto-day` | 昼フェーズ全自動実行 |

---

## Liteモード ゲームフロー

```
[セットアップ] プレイヤー名入力（モード選択なし — Lite固定）
    ↓ POST /api/game/start-lite
    ↓  1. generate_lite_characters() — mistral-large
    ↓  2. assign_roles_lite() + assign_detective_role_lite()
    ↓  3. initialize_game() — デッキ生成・配布・ターン順

[昼フェーズ] (auto-day で一括 or 手動)
    ├─ lite/chat → NPC発言（伏線・示唆含む）
    ├─ lite/npc-votes → Hate投票
    ├─ lite/detective-investigate → 探偵調査（任意）
    └─ 処刑 → 夜移行

[夜フェーズ]
    ├─ lite/cheat-decoy → 陽動+本命入力
    ├─ lite/cheat-react → 防御者リアクション（15文字/5秒）
    ├─ play-cards / pass → NPC連鎖ターン
    └─ 場が3回流れたら翌日へ

[勝利判定] check_instant_victories() — 処刑・上がり・革命時に毎回
```

---

## データモデル要点

### キャラクターステート (CharacterState)

| コード | 状態名 | 説明 |
|:---:|:------|:-----|
| 0 | 存在しない | スロットが空 |
| 1 | 亡き者 | 追放もしくは死亡 |
| 2 | カードゲーム中 | 通常プレイ |
| 3 | 被疑 | チートがバレた状態 |
| 4 | 追放 | イカサマがバレて追放 |
| 5 | 勝利終了 | カードゲームシーンで勝利 |
| 6 | 会議中 | 情報収集フェーズ |
| 7 | 攻撃 | 他者を疑っている |
| 8 | 擁護 | 他者を防衛している |
| 9 | 完全勝利 | キャラクター勝利条件達成 |

### 役割 (Role)
- `fugo` (富豪): 上流階級
- `heimin` (平民): 一般市民
- `hinmin` (貧民): 下層階級。**陽動イカサマ使用可能**

### 審判3段階 (judgment)
- `big_success`: 攻撃成功、効果発動（バレない）
- `draw`: 防がれたが正体不明（バレない）
- `big_fail`: 完全防御、正体バレ

### 勝利条件
- **表の条件** (VictoryCondition): `first_out`, `revolution`, `beat_target`, `help_target`
- **真の条件** (TrueWinCondition): `revenge_on`, `protect`, `climber`, `martyr`, `class_default`

---

## AIモデル使い分け

| 用途 | モデル | Temperature |
|------|--------|-------------|
| キャラクター生成（Lite） | `mistral-large-latest` | 0.9 |
| イカサマ審判 | `mistral-large-latest` | 0.8 |
| NPC発言（Lite） | `mistral-small-latest` | 0.85 |
| NPC投票判断 | `mistral-small-latest` | 0.8 |
| NPCカードプレイ | `mistral-small-latest` | 0.7 |
| 探偵調査結果 | `mistral-small-latest` | 0.8 |
| 夜の環境描写 | `mistral-small-latest` | 0.95 |

---

## 開発規約

### 実行・テスト
```bash
# サーバー起動
cd backend && uvicorn main:app --reload

# 依存インストール
pip install -r backend/requirements.txt
```

### 重要: インポートルール
`backend/` はパッケージではなくスタンドアロン実行のため、**必ず絶対インポートを使用**する。

```python
# ✅ 正しい
from ai_service import ...
from game_engine import ...
from models import ...

# ❌ 誤り（uvicorn起動時にImportError）
from .ai_service import ...
```

### Git運用
- コンベンショナルコミット: `feat:`, `fix:`, `refactor:`, `docs:`
- ブランチ: `lite-only` (ハッカソン提出用)

### コード品質
- `game_engine.py` は純粋関数を維持（テスタビリティ確保）
- `ai_service.py` は外部API呼び出し — 必ず例外ハンドリング
- `main.py` はオーケストレーション層 — ビジネスロジックを持たない

### セキュリティ
- `MISTRAL_API_KEY` は環境変数管理。`.env` をコミットしない
- XSS対策: `escHtml()` でユーザー入力をエスケープ

---

## 既知の問題・注意点

1. **Hardモードバックエンド残存**: フロントからは到達不可だが、エンドポイントは生きている
2. **インメモリ状態**: サーバー再起動でデータ消失
3. **NPC発言が同期的に直列処理**: 全NPCを並列化すれば高速化可能
4. **夜終了条件**: `table_clear_count >= 3` だが、UIでの翌日遷移が不安定な場合あり

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|:----------|:-----|:---------|
| v1.0 | - | 初期実装 |
| v2.2 | - | ワールド設定・記憶喪失・因縁ドラマ |
| v3.0 | - | Liteモード実装（陽動イカサマ・Hateシステム） |
| v4.1 | 2026-03-01 | 人狼ロジック計算・盤面サマリーUI・探偵ロール |
| v4.1+ | 2026-03-01 | ハッカソン向けLite専用化（Hardモードをセットアップ画面から削除） |
