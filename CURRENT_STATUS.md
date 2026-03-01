# プロジェクト現状サマリ

以下はローカルリポジトリ（Mistral_hack2）の現状まとめです。実装者向けの短い参照用ドキュメントとして作成しました。

## 概要
- プロジェクト: 大富豪 × 人狼 × AI（ブラウザゲーム）
- バックエンド: FastAPI（backend/main.py）
- フロントエンド: Vanilla JS（frontend/app.js, frontend/index.html）
- AI: Mistral（backend/ai_service.py が連携）

## 実行方法（開発）
1. 仮想環境を有効化
   ```powershell
   & .venv\Scripts\Activate.ps1
   ```
2. 依存インストール
   ```bash
   pip install -r backend/requirements.txt
   ```
3. サーバ起動
   ```bash
   cd backend
   uvicorn main:app --reload
   # ブラウザで http://localhost:8000 を開く
   ```
4. 環境変数: MISTRAL_API_KEY を backend/.env に設定

## 主要構成と責務（要点）
- backend/main.py: FastAPI アプリ本体、APIエンドポイントとインメモリ状態管理
- backend/game_engine.py: 純粋関数群（デッキ/配布/勝利判定など）
- backend/ai_service.py: Mistral 呼び出しラッパー（非同期）
- backend/models.py: Pydantic v2 モデル群
- frontend/app.js: UI と API 呼び出しのハブ

## 重要な制約・注意点
- ゲーム状態はインメモリ（サーバ再起動で消失）
- CORS: 開発用に allow_origins=["*"] が有効
- .env.example に平文の API キーが含まれている（セキュリティリスク）

## API 概要（代表）
- ゲーム開始: POST /api/game/start
- 昼フェーズ: POST /api/game/chat, POST /api/game/vote, POST /api/game/finalize-vote
- イカサマ: POST /api/game/cheat-initiate, cheat-defend, cheat-skip, cheat-phase-complete
- 夜フェーズ: POST /api/game/play-cards, POST /api/game/pass, POST /api/game/ghost-advance
- デバッグ: GET /api/game/debug-state, GET /api/game/result

## 現在の既知の問題（優先度付き）
1. .env.example に API キー平文（セキュリティ、優先度: 高）
2. インメモリ状態 → 再起動でデータ消失（優先度: 中）
3. run_npc_turns 内での循環 import（設計改善余地）
4. フロントが GET /api/game/state を使っていない（型の不整合）
5. 単体テストが不足（特に game_engine.py）

## 今できる短期アクション（推奨）
- .env.example から平文キーを除去し、README にシークレット設定手順を明記
- 重要ロジック（game_engine.py）の単体テストを追加（backend/tests/test_game_engine.py を拡張）
- ai_service.py の例外処理と非同期呼び出しの並列化検討
- 永続化の検討（軽量: SQLite / dev-only ファイルベース）

## 参考ファイル
- プロジェクト概要: [AGENTS.md](AGENTS.md)
- サーバ実行: [backend/main.py](backend/main.py)
- AI連携: [backend/ai_service.py](backend/ai_service.py)

---
作成日: 2026-03-01
