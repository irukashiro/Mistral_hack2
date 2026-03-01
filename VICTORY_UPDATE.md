# NPC 勝利条件割当の更新 (2026-03-01)

実施内容:
- `backend/ai_service.py` の `generate_characters` にて、全NPCに対して多様な `victory_condition`（陣営勝利）と `true_win`（個人勝利）を割り当てるロジックを実装しました。
  - `victory_condition` は `first_out`, `revolution`, `beat_target`, `help_target` から割当。
  - `true_win` は `revenge_on`, `protect`, `climber`, `martyr`, `class_default` から割当。
  - ターゲットを必要とするタイプ（例: `beat_target`, `revenge_on`, `protect`）は、生成後に有効なターゲットID（他のNPCか `player_human`）が自動設定されます。

- Liteモード初期化 (`/api/game/start-lite`) においても、NPCへランダムな `true_win` を割当てるようにしました。

影響:
- APIで返されるプレイヤー情報に `victory_condition` と `true_win` が含まれるため、フロントエンドはスマート端末・リザルト画面・デバッグ表示でこれらを利用できます。

確認方法:
1. サーバを起動し、ゲームを開始する
2. ヘッダの `📱 端末` を開く（自分の `SECRET MISSION` を確認）
3. `👁`（神の目モード）をオンにすると、NPCの `true_win` がデバッグパネルに表示されます

備考:
- 後続作業として、AIが生成する `victory_condition` / `true_win` のプロンプト設計を改善して、より一貫した目標と行動傾向を出すことを推奨します。
