# AGENTS.md — Class Conflict: Millionaire (大富豪×人狼)

思考は英語で行い、最終的な出力は必ず日本語で提供してください。

---

## プロジェクト概要

Mistral AIハッカソン向けブラウザゲーム。**大富豪（カードゲーム）× 人狼（議論・投票）× AI生成キャラクター**の3要素を組み合わせた対話型ゲーム。プレイヤーは「記憶喪失の人物」として、AIが生成した世界で昼は人狼スタイルの議論・投票、夜は大富豪スタイルのカード対戦を行う。

- **バージョン**: v2.2
- **実行**: `cd backend && uvicorn main:app --reload` → `http://localhost:8000`
- **環境変数**: `MISTRAL_API_KEY` を `backend/.env` に設定

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
│  - APIエンドポイント: /api/game/*                              │
│  - インメモリ状態管理: game_store: Dict[str, GameState]       │
├──────────────────────────────────────────────────────────────┤
│  backend/game_engine.py  │ 純粋関数: デッキ・役判定・ターン管理│
│  backend/ai_service.py   │ Mistral AI連携: 16個の非同期関数  │
│  backend/models.py       │ Pydantic v2: 18クラス             │
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

---

## ファイルマップ

| ファイル | 行数 | 責務 |
|---------|------|------|
| `backend/main.py` | ~860 | FastAPIアプリ本体。20エンドポイント定義、状態管理、情報隠蔽 |
| `backend/game_engine.py` | ~640 | 純粋関数群。デッキ生成・配布・役判定・プレイ検証・ターン進行・勝利判定・チート効果適用 |
| `backend/ai_service.py` | ~1190 | Mistral AI連携。16個の非同期関数。キャラ生成・NPC発言・投票・カードプレイ・イカサマ審判 |
| `backend/models.py` | ~265 | Pydantic v2モデル。`GameState`, `Character`, `Card`, `CheatEffect` 等18クラス |
| `frontend/app.js` | ~1155 | Vanilla JS。ゲーム状態管理・全API呼び出し・DOM描画 |
| `frontend/index.html` | - | 3画面（セットアップ/ゲーム/リザルト）のHTMLシェル |
| `frontend/style.css` | ~1370 | 黒×金のダークゴシックテーマ（CSS Custom Properties） |

---

## APIエンドポイント一覧

### ゲーム管理
| Method | パス | 機能 | リクエスト型 |
|--------|------|------|-------------|
| `POST` | `/api/game/start` | ゲーム開始 | `StartGameRequest` |
| `GET` | `/api/game/state` | ゲーム状態取得（情報隠蔽あり） | query: game_id, player_id |
| `GET` | `/api/game/result` | リザルト画面用全情報開示 | query: game_id |
| `GET` | `/api/game/debug-state` | 神の目モード（全情報開示） | query: game_id |
| `GET` | `/api/game/list` | 稼働中ゲーム一覧（デバッグ） | - |
| `POST` | `/api/game/{game_id}/delete` | ゲーム削除 | - |

### 昼フェーズ（人狼パート）
| Method | パス | 機能 |
|--------|------|------|
| `POST` | `/api/game/chat` | プレイヤー発言 → NPC応答 + 捜査メモ + 記憶断片 |
| `GET` | `/api/game/hints` | AI生成ヒント + 定型文（昼のみ） |
| `POST` | `/api/game/vote` | プレイヤー投票 |
| `POST` | `/api/game/npc-votes` | NPC全員の投票を一括実行 |
| `POST` | `/api/game/finalize-vote` | 処刑確定 → 夜移行 → イカサマフェーズ開始 |

### イカサマフェーズ
| Method | パス | 機能 |
|--------|------|------|
| `POST` | `/api/game/cheat-initiate` | 人間が仕掛ける |
| `POST` | `/api/game/cheat-defend` | 人間が防御する |
| `POST` | `/api/game/cheat-skip` | 人間がスキップ |
| `POST` | `/api/game/cheat-phase-complete` | フェーズ終了 → NPCカードプレイ開始 |

### 夜フェーズ（大富豪パート）
| Method | パス | 機能 |
|--------|------|------|
| `POST` | `/api/game/play-cards` | カードを出す → NPC連鎖プレイ |
| `POST` | `/api/game/pass` | パス → NPC連鎖プレイ |
| `POST` | `/api/game/ghost-advance` | ゴーストモード: NPCターン強制進行 |
| `POST` | `/api/game/end-night` | 夜を手動終了 → 翌日へ |

---

## ゲームフロー

```
[セットアップ] プレイヤー名・NPC人数入力
    ↓ POST /api/game/start
    ↓  1. generate_world_setting() — mistral-large
    ↓  2. generate_characters() — mistral-large
    ↓  3. generate_human_relationships() — mistral-small
    ↓  4. initialize_game() — デッキ生成・配布・ターン順

[昼フェーズ]
    ├─ chat → NPC応答 + 捜査メモ自動抽出 + 40%で記憶断片解放
    ├─ vote → プレイヤー投票 + NPC投票
    └─ finalize-vote → 処刑 → 瞬間勝利チェック → 夜移行

[イカサマフェーズ] (夜移行直後)
    ├─ NPCのイカサマ処理（NPC同士は自動解決）
    ├─ 人間がターゲット → defend パネル表示
    ├─ 人間が仕掛ける → cheat-initiate
    └─ cheat-phase-complete → カードプレイ開始

[夜フェーズ]
    ├─ play-cards / pass → NPC連鎖ターン
    ├─ 8切り・革命チェック
    ├─ 場が3回流れたら翌日へ (_check_night_end)
    └─ ゴーストモード: 処刑済みプレイヤーは観戦（2秒自動更新）

[勝利判定] check_instant_victories() — 処刑・上がり・革命時に毎回
    - martyr: 自分が処刑される
    - revenge_on: ターゲットが処刑/先に上がり
    - beat_target: ターゲットより先に上がる
    - first_out: 最初に上がる
    - climber: 最初に上がる（true_win版）
    - help_target: ターゲットが最初に上がる
    - protect: ターゲットが生存かつ最初に上がる
    - revolution: 革命発動
    - class_default: 最終フォールバック（生存者全員勝利）
```

---

## データモデル要点

### キャラクターステート (CharacterState)

登場人物は 3〜6名。各キャラクターは以下のステートコードを持つ:

| コード | 状態名 | 説明 |
|:---:|:------|:-----|
| 0 | 存在しない | スロットが空（最大人数未満の場合） |
| 1 | 亡き者 | 追放もしくは死亡によるゲーム参加禁止 |
| 2 | カードゲーム中 | 通常プレイ |
| 3 | 被疑 | チートがバレた状態 |
| 4 | 追放 | イカサマがバレて追放 → ステート1へ |
| 5 | 勝利終了 | カードゲームシーンで勝利 |
| 6 | 会議中 | 情報収集フェーズ |
| 7 | 攻撃 | 他者を疑っている |
| 8 | 擁護 | 他者を防衛している |
| 9 | 完全勝利 | キャラクター勝利条件達成 |

### 関係性マトリクス (Relationship Matrix)

N×N マトリクスでキャラクター間の関係を管理する。

```
     A    B    C    D    E    F
A  [ -   友好  中立  敵対  ?    0  ]
B  [友好  -   信頼  中立  敵対  0  ]
C  [中立 信頼  -   秘密  中立  0  ]
D  [敵対 中立  秘密  -   友好  0  ]
E  [ ?  敵対  中立  友好  -    0  ]
F  [ 0   0    0    0    0    -  ]  ← 存在しない
```

- `IsFriend(A, B)`: A→B の友好度を判定する関数
- マトリクスは非対称（A→B と B→A は異なりうる）
- ゲーム進行に応じて動的更新される

### 役割 (Role)
- `fugo` (富豪): 上流階級
- `heimin` (平民): 一般市民
- `hinmin` (貧民): 下層階級。**イカサマ使用可能**

### イカサマ効果 (CheatEffectType)
- `reveal_hand`: 手札全公開
- `peek_hand`: 仕掛け人のみ閲覧
- `steal_card`: 1枚奪取
- `swap_card`: 1枚交換
- `skip_turn`: 次ターンスキップ
- `no_effect`: 失敗

### 審判3段階 (judgment)
- `big_success`: 攻撃成功、効果発動
- `draw`: 防がれたが正体不明
- `big_fail`: 完全防御、正体バレ

### 勝利条件
- **表の条件** (VictoryCondition): `first_out`, `revolution`, `beat_target`, `help_target`
- **真の条件** (TrueWinCondition): `revenge_on`, `protect`, `climber`, `martyr`, `class_default`

---

## AIモデル使い分け

| 用途 | モデル | Temperature |
|------|--------|-------------|
| ワールド設定生成 | `mistral-large-latest` | 0.95 |
| キャラクター生成 | `mistral-large-latest` | 0.9 |
| イカサマ審判 | `mistral-large-latest` | 0.8 |
| NPC発言 | `mistral-small-latest` | 0.85 |
| NPC投票判断 | `mistral-small-latest` | 0.8 |
| NPCカードプレイ | `mistral-small-latest` | 0.7 |
| ヒント・捜査メモ | `mistral-small-latest` | 0.7-0.85 |
| 記憶断片生成 | `mistral-small-latest` | 0.85 |
| 夜の環境描写 | `mistral-small-latest` | 0.95 |

---

## フロントエンド ↔ バックエンド 通信パターン

### app.js の状態管理
- `gameId`: ゲームID（UUIDv4）
- `playerId`: 常に `"player_human"`
- `gameState`: サーバーから返却された最新状態
- `selectedCards`: Set — 夜フェーズで選択中のカードインデックス
- `godEyeMode`: localStorage で永続化される神の目モード
- `lastBatonMap`: NPC発言のバトン情報キャッシュ

### 情報隠蔽ロジック (`_state_to_dict`)
- 自分以外のNPCの`role`, `hand`は非表示（処刑済みを除く）
- `include_hidden=True` で全情報開示（debug-state, ゴーストモード）
- `_debug_role`, `_debug_backstory`, `_debug_true_win` は hiddenモード専用

---

## 開発規約

### 実行・テスト
```bash
# サーバー起動
cd backend && uvicorn main:app --reload

# 依存インストール
pip install -r backend/requirements.txt

# API テスト（Mistral接続確認）
python test_mistral.py
```

### Git運用
- コンベンショナルコミット: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- コミットメッセージは日本語OK

### コード品質
- `game_engine.py` は純粋関数を維持（テスタビリティ確保）
- `ai_service.py` は外部API呼び出し — 必ず例外ハンドリング
- `models.py` はPydantic v2 — バリデーション活用
- `main.py` はオーケストレーション層 — ビジネスロジックを持たない

### セキュリティ
- `MISTRAL_API_KEY` は環境変数管理。`.env` をコミットしない
- `.env.example` にサンプルキーが平文記載されている（要修正）
- XSS対策: `escHtml()` でユーザー入力をエスケープ

---

## クライアント↔サーバー対応表

### app.js → main.py fetch呼び出し（14箇所、全対応確認済み）
| app.js 関数 | エンドポイント | リクエスト型 |
|------------|--------------|-------------|
| `startGame()` | `POST /api/game/start` | `StartGameRequest` (Pydantic) |
| `sendChat()` | `POST /api/game/chat` | dict (⚠ ChatRequest未使用) |
| `castVote()` | `POST /api/game/vote` | `VoteRequest` (Pydantic) |
| `collectNpcVotes()` | `POST /api/game/npc-votes` | dict |
| `finalizeVote()` | `POST /api/game/finalize-vote` | dict (⚠ FinalizeVoteResponse未使用) |
| `playCards()` | `POST /api/game/play-cards` | `PlayCardsRequest` (Pydantic) |
| `passTurn()` | `POST /api/game/pass` | `PassRequest` (Pydantic) |
| `cheat-submit-btn` | `POST /api/game/cheat-initiate` | dict |
| `cheat-skip-btn` | `POST /api/game/cheat-skip` | dict |
| `defense-submit-btn` | `POST /api/game/cheat-defend` | dict |
| `completeCheatPhase()` | `POST /api/game/cheat-phase-complete` | dict |
| `fetchAndApplyDebugState()` | `GET /api/game/debug-state` | query params |
| `fetchHints()` | `GET /api/game/hints` | query params |
| `renderGameOver()` | `GET /api/game/result` | query params |
| `startGhostAutoAdvance()` | `POST /api/game/ghost-advance` | dict |

### サーバーのみ（フロントから未使用）
| エンドポイント | 状態 | 理由 |
|--------------|------|------|
| `GET /api/game/state` | 未使用 | 状態は各レスポンスにインライン返却 |
| `POST /api/game/end-night` | 未使用 | 夜→昼遷移は `_check_night_end` で自動実行 |
| `GET /api/game/list` | デバッグ専用 | |
| `POST /api/game/{game_id}/delete` | デバッグ専用 | |

### 型の不整合
- `models.py` に `ChatRequest` が定義されているが、`/api/game/chat` は `dict` を受け取る
- `models.py` に `FinalizeVoteResponse` が定義されているが `response_model` として使われていない
- 8つのPOSTエンドポイントが型なし `dict` で受け取っている

---

## 既知の問題・注意点

1. **README との差異**: READMEの `DELETE /api/game/{game_id}` は実装上 `POST /api/game/{game_id}/delete`
2. **README との差異**: READMEの `/api/game/full-reveal` は実装上 `/api/game/result`
3. **`.env.example` にAPIキー平文**: セキュリティリスク
4. **インメモリ状態**: サーバー再起動でデータ消失
5. **ゲームロジックのユニットテスト**: 未作成
6. **`run_npc_turns` 内の循環import**: `from game_engine import apply_pass, apply_play` をループ内で実行
7. **NPC発言が同期的に直列処理**: 全NPCを並列化すれば高速化可能
8. **夜終了条件**: `table_clear_count >= 3` だが、UIでの翌日遷移が不安定な場合あり
9. **未使用のPydanticモデル**: `ChatRequest`, `FinalizeVoteResponse` が定義されているがエンドポイントで未使用
10. **未使用エンドポイント**: `GET /api/game/state`, `POST /api/game/end-night` がフロントから呼ばれていない

---

## プロジェクト固有知見

（AIエージェントが開発中に追記するセクション）

---

## 変更履歴

| バージョン | 日付 | 変更内容 |
|:----------|:-----|:---------|
| v1.0 | - | 初期実装（ハッカソン提出版） |
| v1.1 | - | イカサマシステム追加、夜終了条件修正 |
| v2.2 | - | リザルト画面ルーティング修正、デバッグログ追加 |
| v2.3 | - | AI判断理由保存・表示、勝利理由テキスト、キャラクターステート仕様追加 |
