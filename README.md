# Class Conflict: Millionaire
### 大富豪 × 人狼 × AI生成キャラクター　— v2.2

Mistral AI を使ったハッカソン作品。
AI が生成した共有世界設定・キャラクター・関係図を土台に、大富豪（カードゲーム）と人狼を融合したブラウザゲーム。

---

## ゲーム概要

プレイヤーは**記憶喪失の人物**として、AI が生成した世界に放り込まれる。
過去の事件に関わっていたはずだが、何も思い出せない——NPCとの会話の中で、少しずつ真実が明かされる。

| フェーズ | 内容 |
|:--------|:-----|
| **昼（人狼）** | チャットで議論 → 投票 → 処刑。NPCはそれぞれの戦略で動く |
| **イカサマフェーズ** | 夜移行直前。貧民は不正を仕掛け、ターゲットは感覚で防ぐ |
| **夜（大富豪）** | 全員でカードプレイ。3回場が流れると翌日へ |

---

## 実装機能一覧

### AI 生成コンテンツ

| 機能 | モデル | 内容 |
|:----|:-------|:-----|
| **ワールド設定生成** | mistral-large | 舞台・事件・派閥・1000字以上の事件全貌・プレイヤーの秘密の素性を生成 |
| **キャラクター生成** | mistral-large | 世界設定を参照したバックストーリー（3〜5文・固有名詞必須）、関係（最低2つ・種類+エピソード形式） |
| **人間プレイヤーの関係生成** | mistral-small | 世界設定を踏まえた具体的な共有エピソード付き関係を生成。NPCへの逆参照も注入 |
| **NPC 昼発言** | mistral-small | 議論スタイル・世界設定・関係を参照した戦略的発言。バトン（次発言者指定）付き |
| **NPC 投票判断** | mistral-small | 勝利条件・会話履歴を踏まえた投票先決定 |
| **NPC カードプレイ判断** | mistral-small | 手役・勝利条件を踏まえたプレイ選択。ひとことコメント付き |
| **イカサマ審判** | mistral-large | 手口 vs 対策の3段階判定（大成功/引き分け/大失敗）。過剰防衛ペナルティあり |
| **記憶の断片生成** | mistral-small | NPC発言からプレイヤーの真の素性を暗示する断片を抽出（40%確率） |
| **夜の状況テキスト** | mistral-small | 夜移行時の雰囲気描写（1〜2文） |
| **ヒント生成** | mistral-small | プレイヤーへの戦略ヒント3件 + 発言テンプレート3件 |
| **捜査メモ抽出** | mistral-small | NPC発言から推理に使える事実を自動抽出 |

---

### ゲームロジック（大富豪）

| 機能 | 内容 |
|:----|:-----|
| 54枚デッキ | トランプ52枚 + ジョーカー2枚 |
| カードの強さ | 3（弱）〜 2（強）。スート: ♠ > ♥ > ♦ > ♣ |
| 手役 | シングル / ペア / トリプル / クアッド / シーケンス（同スート3枚以上連続） |
| 8切り | 8を出すと場をリセット |
| 革命 | クアッドで強弱逆転 |
| ジョーカー | ワイルドカード兼最強 |
| 夜終了条件 | 場が3回流れたら翌日へ |

---

### 勝利条件システム

**公開勝利条件**（`victory_condition`）

| タイプ | 発動条件 |
|:------|:--------|
| `first_out` | 最初に手札を出し切る |
| `revolution` | 革命が発生する |
| `beat_target` | 指定相手が処刑または自分より後に上がる |
| `help_target` | 指定相手が最初に上がる |

**隠れ勝利条件**（`true_win`）

| タイプ | 発動条件 |
|:------|:--------|
| `revenge_on` | 指定相手が処刑または自分より後に上がる |
| `protect` | 指定相手が最初に上がる |
| `climber` | 自分が最初に上がる |
| `martyr` | 自分が処刑される |
| `class_default` | 通常の勝利条件に従う |

**瞬間勝利判定**（`check_instant_victories`）
以下のイベントで即座にチェック → 達成したら即リザルト遷移：
- 処刑直後 → `martyr` / `revenge_on` / `beat_target`
- 誰かが上がった直後 → `first_out` / `climber` / `help_target` / `protect`
- 革命発動時 → `revolution`

---

### UI 機能

| 機能 | 内容 |
|:----|:-----|
| **神の目モード（👁）** | NPC の役職・バックストーリー・真の目標をオーバーレイ表示。localStorage で状態保存 |
| **ヒントパネル** | 💡ボタンで展開。戦略ヒント + 発言テンプレートボタン |
| **捜査メモ帳** | NPC発言から自動抽出した推理ヒントを蓄積 |
| **記憶の断片パネル** | 🌀 会話中にプレイヤーの真の素性に関する断片が解放される。新断片で自動展開 |
| **ゴーストモード** | 処刑されたプレイヤーが観戦継続。2秒ごとにNPCターンを自動進行 |
| **夜バナー** | 革命バナー / 夜状況バナー / ゴーストモードバナー |
| **夜ログ** | NPC のひとこと + カードプレイ履歴を表示 |
| **イカサマパネル** | 手口自由入力 / 警戒カテゴリ選択（視覚/聴覚/触覚/場/背後） / 結果表示 |

---

### リザルト画面

ゲーム終了時（勝利条件達成 or 自然終了）に全真相を開示：

1. **世界設定 · 真相** — タイトル・舞台・過去の出来事・派閥 + 事件全貌テキスト（1000字以上）
2. **あなたの真の素性** — `player_secret_backstory` の全開示 + 収集した記憶の断片一覧
3. **キャラクター一覧** — 役職・バックストーリー・議論スタイル・真の目標
4. **関係図** — 全キャラクター間の関係をフラットリストで表示
5. **イカサマ記録** — 成功/引き分け/大失敗の判定 + ナレーション

---

## データモデル

### `GameState` フィールド

| フィールド | 型 | 説明 |
|:----------|:---|:-----|
| `game_id` | str | UUID |
| `phase` | "day" \| "night" | 現フェーズ |
| `day_number` | int | 日数 |
| `players` | List[Character] | 全プレイヤー |
| `table` | List[Card] | 場のカード |
| `turn_order` | List[str] | ターン順（ID） |
| `current_turn` | str | 現在のターン |
| `votes` | Dict[str, str] | voter_id → target_id |
| `chat_history` | List[ChatMessage] | チャット履歴 |
| `revolution_active` | bool | 革命状態 |
| `out_order` | List[str] | 上がり順（ID） |
| `table_clear_count` | int | この夜の場流れ回数（3で夜終了） |
| `pending_cheat` | PendingCheat? | 人間への未解決イカサマ |
| `cheat_log` | List[CheatEffect] | イカサマ記録 |
| `night_situation` | str | 夜の状況テキスト |
| `investigation_notes` | List[str] | 捜査メモ（最大20件） |
| `world_setting` | dict | ワールド設定（full_incident・factions等） |
| `amnesia_clues` | List[str] | 記憶の断片（最大15件） |

### `Character` 主要フィールド

| フィールド | 型 | 説明 |
|:----------|:---|:-----|
| `role` | fugo \| heimin \| hinmin | 役職 |
| `backstory` | str | 3〜5文・固有名詞入り |
| `relationships` | List[Relationship] | 最低2つ・種類+エピソード形式 |
| `argument_style` | str | 慎重派/扇動者/論理派/便乗派/狂信者 |
| `victory_condition` | VictoryCondition | 公開勝利条件 |
| `true_win` | TrueWinCondition? | 隠れ勝利条件 |
| `hand_revealed` | bool | イカサマで手札が全公開中 |
| `skip_next_turn` | bool | 次ターンスキップ中 |

---

## API エンドポイント

| Method | Path | 説明 |
|:-------|:-----|:-----|
| POST | `/api/game/start` | ワールド設定生成 → キャラ生成 → カード配布 |
| GET  | `/api/game/state` | ゲーム状態取得（ゴーストモード時は全情報開示） |
| GET  | `/api/game/hints` | 戦略ヒント + 発言テンプレート生成（昼のみ） |
| GET  | `/api/game/debug-state` | 神の目モード用：全情報開示 |
| GET  | `/api/game/full-reveal` | リザルト用：世界設定・全キャラ・関係図・イカサマ記録 |
| POST | `/api/game/chat` | 発言 → NPC応答 + 捜査メモ更新 + 記憶断片解放 |
| POST | `/api/game/vote` | 投票記録 |
| POST | `/api/game/npc-votes` | NPC 投票実行 |
| POST | `/api/game/finalize-vote` | 処刑 → 瞬間勝利チェック → 夜移行 |
| POST | `/api/game/cheat-initiate` | 人間がNPCにイカサマ仕掛け |
| POST | `/api/game/cheat-defend` | 人間がNPCのイカサマを防御 |
| POST | `/api/game/cheat-skip` | イカサマをスキップ |
| POST | `/api/game/cheat-phase-complete` | イカサマフェーズ終了 → NPCターン開始 |
| POST | `/api/game/play-cards` | 夜：カードプレイ → NPCターン連鎖 |
| POST | `/api/game/pass` | 夜：パス → NPCターン連鎖 |
| POST | `/api/game/ghost-advance` | ゴーストモード：NPCターンを強制進行 |
| POST | `/api/game/end-night` | 夜フェーズを手動終了 |
| GET  | `/api/game/list` | 稼働中ゲーム一覧（デバッグ） |
| DELETE | `/api/game/{game_id}` | ゲーム削除 |

---

## ディレクトリ構成

```
Mistral_hack2/
├── backend/
│   ├── main.py          # FastAPI エンドポイント（全15本）
│   ├── game_engine.py   # 大富豪ロジック（純粋関数）+ 勝利判定
│   ├── ai_service.py    # Mistral AI 連携（関数16本）
│   ├── models.py        # Pydantic モデル（クラス18個）
│   └── requirements.txt
├── frontend/
│   ├── index.html       # ゲーム画面（セットアップ / ゲーム / リザルト）
│   ├── style.css        # ダークゴシックテーマ（黒×金）
│   └── app.js           # Vanilla JS フロントエンド
├── .env.example
├── README.md
└── AGENTS.md
```

---

## セットアップ

```bash
cd backend
pip install -r requirements.txt

# .env.example をコピーして MISTRAL_API_KEY を設定
cp ../.env.example .env

uvicorn main:app --reload
```

ブラウザで `http://localhost:8000` を開く。

---

## バージョン履歴

| バージョン | 追加内容 |
|:----------|:--------|
| v1.0 | 初期実装（大富豪 + 人狼基本フロー） |
| v1.1 | イカサマシステム + 夜終了条件 |
| v1.2 | 3段階イカサマ判定 / バトン / TrueWin / NightSituation / argument_style |
| v2.0 | 神の目 / ヒントパネル / 捜査メモ / ゴーストモード / 夜ログ発言 / リッチリザルト |
| v2.1 | ワールド設定生成 / キャラバックストーリー強化 / 関係エピソード化 / NPC発言に世界設定注入 |
| v2.2 | 記憶喪失プレイヤー / 記憶の断片パネル / 事件全貌1000字生成 / 瞬間勝利判定 / リザルト全真相開示 |
