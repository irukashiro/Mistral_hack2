"""
Mistral AI integration for:
1. Character generation at game start
2. NPC speech generation during day phase
3. NPC card play decisions during night phase
"""
import asyncio
import json
import os
import random
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from mistralai import Mistral

from models import (
    Card, Character, CheatEffect, CheatEffectType, GameState, PendingCheat,
    Role, TrueWinCondition, VictoryCondition, Relationship
)
from game_engine import apply_cheat_effect, apply_pass, apply_play, get_valid_plays


def get_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")
    return Mistral(api_key=api_key)


def _log_api_call(
    state: Optional[GameState],
    endpoint: str,
    model: str,
    prompt_summary: str,
    response_summary: str,
    latency_ms: int,
):
    """Append an API call log entry to state.debug_log if state is provided."""
    if state is None:
        return
    state.debug_log.append({
        "type": "api_call",
        "actor": "system",
        "actor_name": "Mistral API",
        "reasoning": f"{model} → {endpoint}",
        "detail": {
            "endpoint": endpoint,
            "model": model,
            "prompt_summary": prompt_summary[:120],
            "response_summary": response_summary[:120],
            "latency_ms": latency_ms,
        },
        "turn": state.day_number if state else 0,
    })


# ─────────────────────────────────────────────
# 1. Character generation
# ─────────────────────────────────────────────

_WORLD_GENRES = [
    ("廃病院", "廃病院・旧病棟（例: 閉院した精神科病院の隔離棟）"),
    ("山岳ロッジ", "山岳ロッジ・山荘（例: 北アルプス山麓の孤立した山小屋）"),
    ("豪華客船", "豪華客船・クルーズ船（例: 太平洋横断中の大型客船の一等客室）"),
    ("廃校", "廃校・旧学校（例: 廃校になった山間の全寮制高校の校舎）"),
    ("地下施設", "地下施設・秘密基地（例: 旧軍の地下指令室を改装した施設）"),
    ("タワーマンション最上階", "タワーマンション最上階（例: 東京湾岸の超高層タワーの最上階ペントハウス）"),
    ("孤島リゾート", "孤島リゾート（例: 伊豆諸島の無人島に建てられたプライベートリゾート）"),
    ("地下カジノ", "地下カジノ・賭博場（例: 歌舞伎町の雑居ビル地下に隠された高級賭博場）"),
    ("研究施設", "研究施設・ラボ（例: 孤立した山中の極秘バイオ研究所）"),
    ("廃テーマパーク", "廃テーマパーク（例: 閉園したまま20年放置された遊園地の管理棟）"),
]


async def generate_world_setting() -> dict:
    """Generate a rich shared world setting with a detailed incident narrative."""
    client = get_client()
    genre_key, genre_example = random.choice(_WORLD_GENRES)
    prompt = f"""大富豪×人狼ゲームの共有ワールド設定を生成してください。
全プレイヤーが関わってきた具体的な場所・事件・派閥を設定します。
固有名詞（地名・施設名・事件名・人物名）を積極的に使い、臨場感のある設定にしてください。

【今回の舞台ジャンル（必須）】: {genre_key}
舞台の例: {genre_example}
→ 必ずこのジャンルに合った設定にすること。「屋敷」「相続」「遺産争い」は絶対に使わないこと。

JSON形式:
{{
  "setting_name": "セッションタイトル（{genre_key}に合ったもの）",
  "location": "舞台の具体的な場所（{genre_example}のような表現で）",
  "context": "社会的背景（2文）",
  "key_events": [
    "全員が関わった過去の出来事1（具体的な固有名詞入り）",
    "全員が関わった過去の出来事2",
    "全員が関わった過去の出来事3"
  ],
  "factions": [
    {{"name": "派閥名", "description": "目的・特徴"}},
    {{"name": "派閥名", "description": "目的・特徴"}}
  ],
  "full_incident": "1000文字以上の詳細な事件描写。時系列で記述し、この場に集まった全員が何らかの形で関与している。具体的な日付・場所・動機・謀略・裏切りを含む完全な物語として書くこと。この事件の真相を知る者・隠す者・利用しようとする者が混在している。",
  "player_secret_backstory": "記憶を失ったプレイヤーの真の素性（3〜5文）。事件において重要な立場にあった人物だが、何らかの理由で記憶を失っている。固有名詞（地名・組織名・事件名）を含み、他の参加者の誰かと深い因縁がある設定にすること。"
}}"""

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.95,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return data
    except Exception:
        return {
            "setting_name": "廃館の遺産争奪戦",
            "location": "東京都郊外の旧華族邸・黒澤館",
            "context": "旧財閥の遺産相続を巡り、各界の人物が集まった。法的な争いが続く中、非公式の「決闘の夜」が開催される。",
            "key_events": [
                "3年前の黒澤財閥解体事件で全員が何らかの形で損失を被った",
                "昨年の「赤い招待状事件」でこの屋敷に呼び集められた",
                "半年前の株式市場崩壊で参加者間の力関係が逆転した"
            ],
            "factions": [
                {"name": "旧財閥派", "description": "黒澤家の復興を目指す保守的な勢力"},
                {"name": "改革派", "description": "既存の秩序を壊し新たな支配層となることを狙う"}
            ],
            "full_incident": "三年前の冬、黒澤財閥の総帥・黒澤義雄が遺言を残さずに急死した。その翌朝、金庫から株券と遺言書の原本が消え失せた。黒澤館に集められた関係者たちは互いを疑い始め、法廷闘争と水面下の駆け引きが始まった。やがて「赤い招待状」と呼ばれる謎の通知が各者の元に届き、再び全員が黒澤館に呼び寄せられた。その夜、大富豪という名のカードゲームで、それぞれの真意が試されることになる。",
            "player_secret_backstory": "あなたは黒澤義雄の隠し子であり、本来の遺産の正当な継承者だ。しかし事件の夜に何者かに襲われ、記憶を失った。あなたの存在を知る者がこの場にいる——それが味方か敵かは、まだわからない。",
        }


async def generate_amnesia_clue(
    npc_speeches: List[Dict[str, Any]],
    world_setting: dict,
    existing_clues: List[str],
) -> Optional[str]:
    """Sometimes extract a clue about the player's true identity from NPC speech (40% chance)."""
    if not world_setting or not npc_speeches:
        return None
    player_secret = world_setting.get('player_secret_backstory', '')
    if not player_secret:
        return None
    if random.random() > 0.4:
        return None  # 40% chance to generate a clue

    client = get_client()
    speeches_text = "\n".join([f"{r['name']}: {r['text']}" for r in npc_speeches])
    existing_str = "\n".join(existing_clues[-5:]) if existing_clues else "なし"

    prompt = f"""大富豪×人狼ゲームで、プレイヤーは記憶を失った人物です。
NPCたちは無意識のうちに、プレイヤーの真の素性に関するヒントを漏らすことがあります。

プレイヤーの（秘密の）真の素性:
{player_secret}

今回のNPC発言:
{speeches_text}

既に判明しているヒント:
{existing_str}

NPCの発言からプレイヤーの真の素性を暗示する手がかりが読み取れる場合、
「記憶の断片」として1文（30〜60文字）で表現してください。
直接的に答えを言わず、断片的・感覚的な表現にすること。
既存ヒントと重複しないこと。手がかりがなければ null を返す。
JSON: {{"clue": "断片テキスト（または null）"}}"""

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.85,
        )
        data = json.loads(response.choices[0].message.content)
        clue = data.get("clue")
        if clue and str(clue).lower() != "null" and len(str(clue)) > 5:
            return str(clue)
        return None
    except Exception:
        return None


CHARACTER_GEN_SYSTEM = """あなたはゲームマスターです。
「大富豪×人狼」ゲームのNPCキャラクターを生成してください。
各キャラクターは独特の個性を持ち、日本の架空の社会を舞台に生き生きとしたバックストーリーを持ちます。
必ずJSON形式で返答してください。"""

CHARACTER_GEN_USER_TEMPLATE = """以下の条件で{count}人のNPCキャラクターを生成してください。
{world_setting_block}
各キャラクターに必要な情報:
- id: ユニークID（例: "npc_01"）
- name: キャラクター名（日本語）
- role: "{roles_str}" のいずれか
- backstory: 背景・出自（3〜5文、固有名詞〔地名・施設名・事件名〕を最低1つ含むこと）
- personality: 性格の特徴（1〜2文）
- speech_style: 話し方の特徴（1文、例：「〜でございます」「〜だぜ」）
- relationships: 他キャラとの関係（最低2つ）
    descriptionには「関係の種類（盟友/ライバル/秘密を共有/恨み/利用関係）」と「具体的な共有エピソード」を含めること
    例: "ライバル — 鷹見荘の遺産を巡る争いで互いに失脚しかけた因縁がある"
- argument_style: 議論スタイル — "慎重派"/"扇動者"/"論理派"/"便乗派"/"狂信者" のいずれか1つ
- victory_condition:
    type は "first_out"/"revolution"/"beat_target"/"help_target" のいずれか
    beat_target/help_target の場合は target_npc_id を指定
    description: 勝利条件の説明
- true_win: 表の勝利条件とは別の、隠れた個人目標
    type は "revenge_on"/"protect"/"climber"/"martyr"/"class_default" のいずれか
    revenge_on/protect の場合は target_id（同じセッションのNPC IDを指定）
    description: 目標の説明（1文）

キャラクターのIDは npc_01, npc_02, ... のように設定してください。
ロールの割り当て: {role_assignments}

JSON形式（キャラクターの配列）で返してください:
{{
  "characters": [
    {{
      "id": "npc_01",
      "name": "...",
      "role": "fugo",
      "backstory": "...",
      "personality": "...",
      "speech_style": "...",
      "argument_style": "論理派",
      "relationships": [{{"target_id": "npc_02", "description": "ライバル — ..."}}],
      "victory_condition": {{"type": "first_out", "target_npc_id": null, "description": "..."}},
      "true_win": {{"type": "climber", "target_id": null, "description": "真っ先に上がって自由を勝ち取る"}}
    }}
  ]
}}"""


def _build_role_assignments(count: int) -> Tuple[List[Role], str]:
    """Assign roles and return role list + description string."""
    roles = []
    roles.append(Role.FUGO)
    hinmin_count = max(1, count // 3)
    for _ in range(hinmin_count):
        roles.append(Role.HINMIN)
    while len(roles) < count:
        roles.append(Role.HEIMIN)
    random.shuffle(roles)

    assignment_str = ", ".join([
        f"npc_{i+1:02d}: {r.value}" for i, r in enumerate(roles)
    ])
    return roles, assignment_str


async def generate_characters(
    npc_count: int,
    world_setting: Optional[Dict] = None,
    player_name: str = "プレイヤー",
) -> List[Character]:
    """Generate NPC characters using Mistral AI."""
    client = get_client()
    roles, role_assignments = _build_role_assignments(npc_count)
    roles_str = "fugo（富豪）, heimin（平民）, hinmin（貧民）"

    # Build world setting block for prompt injection
    if world_setting:
        location = world_setting.get('location', '')
        context = world_setting.get('context', '')
        events = world_setting.get('key_events', [])
        factions = world_setting.get('factions', [])
        full_incident = world_setting.get('full_incident', '')
        player_secret = world_setting.get('player_secret_backstory', '')
        events_str = "\n".join([f"  - {e}" for e in events])
        factions_str = "\n".join([f"  - {f['name']}: {f['description']}" for f in factions])
        world_setting_block = f"""
ゲーム世界の設定（必ずこの設定を参照してキャラクターを作ること）:
舞台: {location}
背景: {context}
共通の過去（全員が関わっている出来事）:
{events_str}
派閥:
{factions_str}
→ backstory にこの設定の固有名詞（地名・事件名・派閥名）を最低1つ使うこと
→ relationships の description に「種類 — 共有エピソード」の形式で具体的に書くこと
"""
        if full_incident:
            world_setting_block += f"""
【事件の詳細（参考情報）】
{full_incident}
重要ルール:
- 上記は事件の客観的全容だが、各キャラクターはこれを「完全に」知っているわけではない
- 各キャラクターのbackstoryは、その人物が事件をどう体験・解釈したかの「主観的視点」で書くこと
- 自分が関わっていない部分や真相については「知らない」「誤解している」状態で書いてよい
- backstory に事件の一側面を盛り込み、それがキャラクターの動機・秘密に直結するようにすること
"""
        if player_secret:
            world_setting_block += f"""
【記憶喪失のプレイヤー「{player_name}」の真の素性】
{player_secret}
- このプレイヤーは現在、自分の過去を一切覚えていない記憶喪失状態にある
- NPCの一部はこの人物の真の素性を（部分的に）知っている可能性がある
- 知っているNPCは、relationships でそれを示唆するエピソードを含めること
- 真の素性を知っているかどうか、それをどう扱うかはキャラクターごとの設定に委ねる
"""
    else:
        world_setting_block = ""

    prompt = CHARACTER_GEN_USER_TEMPLATE.format(
        count=npc_count,
        roles_str=roles_str,
        role_assignments=role_assignments,
        world_setting_block=world_setting_block,
    )

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": CHARACTER_GEN_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    characters_data = data.get("characters", [])

    characters = []
    for i, char_data in enumerate(characters_data):
        role_val = char_data.get("role", "heimin")
        try:
            role = Role(role_val)
        except ValueError:
            role = roles[i] if i < len(roles) else Role.HEIMIN

        vc_data = char_data.get("victory_condition", {})
        vc = VictoryCondition(
            type=vc_data.get("type", "first_out"),
            target_npc_id=vc_data.get("target_npc_id"),
            description=vc_data.get("description", ""),
        )

        relationships = []
        for rel in char_data.get("relationships", []):
            relationships.append(Relationship(
                target_id=rel.get("target_id", ""),
                description=rel.get("description", ""),
            ))

        tw_data = char_data.get("true_win", {})
        true_win = None
        if tw_data and tw_data.get("type"):
            try:
                true_win = TrueWinCondition(
                    type=tw_data.get("type", "class_default"),
                    target_id=tw_data.get("target_id"),
                    description=tw_data.get("description", ""),
                )
            except Exception:
                pass

        valid_styles = {"慎重派", "扇動者", "論理派", "便乗派", "狂信者"}
        arg_style = char_data.get("argument_style", "")
        if arg_style not in valid_styles:
            arg_style = random.choice(list(valid_styles))

        character = Character(
            id=char_data.get("id", f"npc_{i+1:02d}"),
            name=char_data.get("name", f"NPC{i+1}"),
            role=role,
            backstory=char_data.get("backstory", ""),
            personality=char_data.get("personality", ""),
            speech_style=char_data.get("speech_style", ""),
            relationships=relationships,
            victory_condition=vc,
            argument_style=arg_style,
            true_win=true_win,
            is_human=False,
        )
        characters.append(character)

    return characters


# ─────────────────────────────────────────────
# 1b. Human player relationships
# ─────────────────────────────────────────────

async def generate_human_relationships(
    human_name: str,
    npc_characters: List[Character],
    world_setting: Optional[Dict] = None,
) -> List[Relationship]:
    """Generate relationships between the human player and NPCs.
    Also injects back-references into NPC characters (in-place).
    Returns list of Relationship objects for the human player.
    """
    client = get_client()
    npc_info = [
        {"id": npc.id, "name": npc.name, "personality": npc.personality}
        for npc in npc_characters
    ]

    world_context = ""
    if world_setting:
        location = world_setting.get('location', '')
        events = world_setting.get('key_events', [])
        events_str = "、".join(events[:2]) if events else ""
        player_secret = world_setting.get('player_secret_backstory', '')
        world_context = f"""
ゲーム世界:
舞台: {location}
共通の過去: {events_str}
→ プレイヤーもこの世界の出来事を知っている前提で、具体的な共有エピソードを含めた関係を生成してください
"""
        if player_secret:
            world_context += f"""
プレイヤーの真の素性（NPCには部分的に知られている可能性がある）:
{player_secret}
→ npc_back_refs では、NPCがこのプレイヤーの真の素性をどの程度知っているか・どう感じているかを1文で表現すること
→ 知っている場合は警戒・同情・利用しようとする等の態度を反映させてよい
"""

    prompt = f"""大富豪×人狼ゲームで、プレイヤー「{human_name}」とNPCキャラクターたちの関係を生成してください。
プレイヤーは最低2人のNPCと何らかの関係を持ちます。
{world_context}
NPC一覧:
{json.dumps(npc_info, ensure_ascii=False)}

プレイヤーが持つ関係（最低2つ）を生成してください。
descriptionには「関係の種類（盟友/ライバル/秘密を共有/恨み/利用関係）」と「具体的な共有エピソード」を含めること。
npc_back_refsは1〜2体のNPCのプレイヤーへの認識（1文、共有エピソードを含む）を設定してください。

JSON形式:
{{
  "relationships": [
    {{"target_id": "npc_01", "description": "ライバル — 共有エピソードの説明"}},
    {{"target_id": "npc_02", "description": "秘密を共有 — 共有エピソードの説明"}}
  ],
  "npc_back_refs": [
    {{"npc_id": "npc_01", "description": "NPCからプレイヤーへの認識（1文）"}}
  ]
}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        relationships = []
        for rel in data.get("relationships", []):
            relationships.append(Relationship(
                target_id=rel.get("target_id", ""),
                description=rel.get("description", ""),
            ))

        # Inject back-refs into NPC characters
        npc_map = {npc.id: npc for npc in npc_characters}
        for ref in data.get("npc_back_refs", []):
            npc = npc_map.get(ref.get("npc_id"))
            if npc:
                npc.relationships.append(Relationship(
                    target_id="player_human",
                    description=ref.get("description", ""),
                ))

        return relationships
    except Exception:
        # Fallback: create simple relationships with first 2 NPCs
        return [
            Relationship(target_id=npc_characters[i].id, description="知人")
            for i in range(min(2, len(npc_characters)))
        ]


async def generate_hints(state: GameState, player: Character) -> dict:
    """Generate 3 action hints and 3 template messages for the player during day phase."""
    client = get_client()

    recent_chat = state.chat_history[-8:] if len(state.chat_history) > 8 else state.chat_history
    chat_summary = "\n".join([f"{m.speaker_name}: {m.text}" for m in recent_chat])
    alive_names = [p.name for p in state.alive_players() if p.id != player.id]
    rel_desc = "; ".join([f"{r.target_id}との関係: {r.description}" for r in player.relationships])

    amnesia_clues_block = ""
    if state.amnesia_clues:
        clues_str = "\n".join([f"  - {c}" for c in state.amnesia_clues[-5:]])
        amnesia_clues_block = f"""
記憶の断片（プレイヤーが回収した自分の過去の手がかり）:
{clues_str}
→ ヒントにこれらの断片を活かした推理・行動提案を含めてよい
"""

    prompt = f"""大富豪×人狼ゲームで、プレイヤーへの議論アドバイスを生成してください。

プレイヤー情報:
- 役割（秘密）: {player.role.value}
- 勝利条件: {player.victory_condition.description}
- 関係: {rel_desc or "なし"}
{amnesia_clues_block}
ゲーム状況:
- {state.day_number}日目
- 生存者: {', '.join(alive_names)}

最近の会話:
{chat_summary}

上記を踏まえ、プレイヤーが取れる行動ヒント3つと、すぐ使える定型文3つを生成してください。
JSON形式:
{{
  "hints": [
    {{"text": "ヒント1（1〜2文）"}},
    {{"text": "ヒント2（1〜2文）"}},
    {{"text": "ヒント3（1〜2文）"}}
  ],
  "templates": [
    {{"label": "ラベル", "message": "実際の発言文"}},
    {{"label": "ラベル", "message": "実際の発言文"}},
    {{"label": "ラベル", "message": "実際の発言文"}}
  ]
}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return {
            "hints": data.get("hints", []),
            "templates": data.get("templates", []),
        }
    except Exception:
        return {"hints": [], "templates": []}


async def detect_investigation_facts(
    npc_responses: List[Dict[str, Any]],
    state: GameState,
) -> List[str]:
    """Extract investigation-worthy facts from NPC responses."""
    if not npc_responses:
        return []

    client = get_client()
    speeches = "\n".join([f"{r['name']}: {r['text']}" for r in npc_responses])

    prompt = f"""大富豪×人狼ゲームで、NPCの発言から推理に使える事実・矛盾・手がかりを抽出してください。

{state.day_number}日目のNPC発言:
{speeches}

推理メモとして使える情報を1〜3個、短い日本語で抽出してください（各1文）。
なければ空配列。
JSON: {{"facts": ["事実1", "事実2"]}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("facts", [])
    except Exception:
        return []


# ─────────────────────────────────────────────
# 2. NPC speech during day phase
# ─────────────────────────────────────────────

NPC_SPEECH_SYSTEM = """あなたはゲームのNPCキャラクターです。
与えられたキャラクター情報に基づき、そのキャラクターとして発言してください。
発言は1〜3文で簡潔に。キャラクターの口調・性格・議論スタイルを忠実に再現してください。
自分の役割（富豪・平民・貧民）は秘密にしてください。ただし行動で匂わせることは可能です。
必ずJSON形式で返答してください。"""


async def generate_npc_speech(
    npc: Character,
    state: GameState,
    trigger: str = "general",
    player_message: Optional[str] = None,
    world_setting: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Generate a speech line for an NPC during the day phase.
    Returns dict with speech, baton_target_id, baton_action."""
    client = get_client()

    # Build context
    alive_players = state.alive_players()
    alive_names = [p.name for p in alive_players if p.id != npc.id]
    other_npc_ids = [p.id for p in alive_players if p.id != npc.id and not p.is_human]
    hanged = [p for p in state.players if p.is_hanged]
    hanged_names = [p.name for p in hanged]

    recent_chat = state.chat_history[-6:] if len(state.chat_history) > 6 else state.chat_history
    chat_summary = "\n".join([
        f"{m.speaker_name}: {m.text}" for m in recent_chat
    ])

    my_vc = npc.victory_condition.description
    # Resolve player IDs to actual names in relationships
    player_name_map = {p.id: p.name for p in state.players}
    rel_desc = "; ".join([
        f"{player_name_map.get(r.target_id, r.target_id)}との関係: {r.description}"
        for r in npc.relationships
    ])
    true_win_desc = npc.true_win.description if npc.true_win else "なし"
    # Note about amnesiac player and incident knowledge limits
    human = state.get_human_player()
    amnesia_note = ""
    if human and not human.is_hanged:
        amnesia_note = f"\n重要: プレイヤー「{human.name}」は記憶を失っており、自分の過去を覚えていない。あなたがこのプレイヤーについて何か知っている場合、それをどう扱うかはキャラクターとして判断すること（黙っている・探りを入れる・試す・同情するなど）。"
    incident_note = "\n注意: 事件についてあなたが知っているのは、あなた自身のバックストーリーに書かれている主観的な経験のみ。事件の客観的全容を知っているわけではない。知らない部分は「知らない」扱いにすること。"
    style_guide = {
        "慎重派": "発言は控えめで証拠を求め、断言を避ける",
        "扇動者": "感情的に場を煽り、特定の人物への疑惑を誇張する",
        "論理派": "論理的・冷静に状況を分析し、矛盾を指摘する",
        "便乗派": "他者の意見に同調しつつ、さりげなく自分の利益を誘導する",
        "狂信者": "自分の信念に固執し、強引に議論を押し進める",
    }
    style_hint = style_guide.get(npc.argument_style, "")

    # Build world context block
    world_context_block = ""
    if world_setting:
        ws_location = world_setting.get('location', '')
        ws_events = world_setting.get('key_events', [])
        events_summary = "、".join(ws_events[:2]) if ws_events else ""
        world_context_block = f"""
ゲーム世界の共通事項:
舞台: {ws_location}
共通の過去: {events_summary}
→ 自然な会話の中でこれらの固有名詞を参照しても構わない
"""

    context_prompt = f"""キャラクター情報:
名前: {npc.name}
性格: {npc.personality}
口調: {npc.speech_style}
議論スタイル: {npc.argument_style}（{style_hint}）
バックストーリー: {npc.backstory}
（秘密）勝利条件: {my_vc}
（秘密）真の目標: {true_win_desc}
関係: {rel_desc}（この人物との関係は議論の中で自然に参照してよい）
{amnesia_note}{incident_note}
{world_context_block}

ゲーム状況:
日数: {state.day_number}日目
生存者: {', '.join(alive_names)}
吊られた人: {', '.join(hanged_names) if hanged_names else 'なし'}
手札枚数: {npc.hand_count()}枚

最近の会話:
{chat_summary}

{"プレイヤーの発言: " + player_message if player_message else ""}

バトン先候補（ID）: {other_npc_ids}

上記を踏まえて、{npc.name}として議論スタイルに沿った発言を生成してください。
reasoning は内部戦略（表示されない）、speech はキャラクター口調で1〜3文。
バトンで次に発言させたいNPCのIDを baton_target_id に（なければ null）、
baton_action は "question"（質問を向ける）/"rebuttal"（反論を促す）/"agreement_request"（同意を求める） のいずれか。

JSON形式:
{{
  "reasoning": {{
    "situation_read": "現状認識（1文）",
    "goal": "この発言の戦略的意図（1文）",
    "strategy": "どう話を向けるか（1文）"
  }},
  "speech": "発言内容（キャラクター口調）",
  "baton_target_id": "npc_xx または null",
  "baton_action": "question/rebuttal/agreement_request"
}}"""

    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_SPEECH_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        speech = data.get("speech", "...")
        reasoning = data.get("reasoning", {})
        baton_target = data.get("baton_target_id")
        baton_action = data.get("baton_action", "question")
        # Validate baton target is an actual alive NPC
        if baton_target and baton_target not in other_npc_ids:
            baton_target = None
        _log_api_call(state, "npc_speech", "mistral-small", f"{npc.name} speech", speech[:80], latency)
        return {"speech": speech, "reasoning": reasoning, "baton_target_id": baton_target, "baton_action": baton_action}
    except Exception:
        _log_api_call(state, "npc_speech", "mistral-small", f"{npc.name} speech", "parse_error", latency)
        return {"speech": content[:200], "reasoning": {}, "baton_target_id": None, "baton_action": "question"}


async def generate_npc_speeches_for_player_message(
    state: GameState,
    player_message: str,
    world_setting: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    Generate responses from all NPCs to a player's message.
    Returns list of {"npc_id", "name", "text", "baton_target_id", "baton_action"}.
    """
    npcs = [p for p in state.alive_players() if not p.is_human and not p.is_hanged]

    async def _gen(npc):
        result = await generate_npc_speech(
            npc=npc,
            state=state,
            trigger="player_message",
            player_message=player_message,
            world_setting=world_setting,
        )
        return {
            "npc_id": npc.id,
            "name": npc.name,
            "text": result["speech"],
            "reasoning": result.get("reasoning", {}),
            "baton_target_id": result["baton_target_id"],
            "baton_action": result["baton_action"],
        }

    responses = await asyncio.gather(*[_gen(npc) for npc in npcs])
    return list(responses)


# ─────────────────────────────────────────────
# 3. NPC card play decision during night phase
# ─────────────────────────────────────────────

NPC_PLAY_SYSTEM = """あなたはカードゲーム「大富豪×人狼」のNPCです。
自分の勝利条件と手札を考慮して、最適なカードプレイを決定してください。
必ずJSON形式で返答してください。"""


async def decide_npc_play(
    npc: Character,
    state: GameState,
) -> Tuple[Optional[List[Card]], str, str]:
    """
    Decide what cards an NPC will play (or None to pass).
    Returns (list of Card objects or None for pass, speech string, reasoning string).
    """
    if npc.is_hanged:
        return None, "", ""  # Hanged players always pass

    valid_plays = get_valid_plays(npc.hand, state.table, state.revolution_active)

    if not valid_plays:
        return None, "", ""  # No valid plays, must pass

    # Build context for AI decision
    hand_display = [c.display() for c in npc.hand]
    table_display = [c.display() for c in state.table] if state.table else ["（空き）"]
    valid_plays_display = [
        [c.display() for c in play] for play in valid_plays[:10]  # limit to 10 options
    ]

    alive_hand_counts = {
        p.name: p.hand_count()
        for p in state.alive_players()
        if p.id != npc.id
    }

    true_win_desc = npc.true_win.description if npc.true_win else "なし"

    # Build special card context for rich reactions
    special_card_hints = []
    for play in valid_plays[:10]:
        nums = [c.number for c in play if not c.is_joker]
        has_joker = any(c.is_joker for c in play)
        if has_joker:
            special_card_hints.append("ジョーカーを出す場合: ミステリアスで不気味な発言をすること")
        if nums and all(n == 2 for n in nums):
            special_card_hints.append("「2」を出す場合: 強気・得意げ・余裕を見せる発言をすること")
        if len(play) == 4:
            special_card_hints.append("4枚（革命）を出す場合: 場がひっくり返る驚きや「これが真の力だ」的な発言をすること")
    special_hint_block = "\n".join(dict.fromkeys(special_card_hints))  # dedupe

    context_prompt = f"""キャラクター: {npc.name}
勝利条件: {npc.victory_condition.description}
真の目標: {true_win_desc}
議論スタイル: {npc.argument_style}
手札: {hand_display}
場のカード: {table_display}
革命状態: {"あり" if state.revolution_active else "なし"}
他プレイヤーの手札枚数: {alive_hand_counts}
出せる手役（最大10個）: {valid_plays_display}
{("特殊カード演出ガイド:\n" + special_hint_block) if special_hint_block else ""}

上記を踏まえて、最も戦略的なプレイを選んでください。
speechはカードプレイ時の雰囲気ある一言（40文字以内、口調: {npc.speech_style}）。
JSON形式:
{{
  "reasoning": "戦略的判断の理由（1文）",
  "action": "pass または play",
  "play_index": 0,
  "speech": "カードプレイ時のひとこと（40文字以内、口調: {npc.speech_style}）"
}}"""

    client = get_client()
    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_PLAY_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        action = data.get("action", "pass")
        speech = data.get("speech", "")
        reasoning = data.get("reasoning", "")
        _log_api_call(state, "npc_play", "mistral-small", f"{npc.name} play decision", action, latency)
        if action == "pass":
            return None, "", reasoning
        play_index = data.get("play_index", 0)
        if 0 <= play_index < len(valid_plays):
            return valid_plays[play_index], speech, reasoning
        return valid_plays[0], speech, reasoning  # fallback to first valid play
    except Exception:
        _log_api_call(state, "npc_play", "mistral-small", f"{npc.name} play decision", "parse_error", latency)
        # Fallback: play a random valid move or pass
        if random.random() > 0.3:
            return random.choice(valid_plays), "", ""
        return None, "", ""


async def run_npc_turns(
    state: GameState,
) -> Tuple[GameState, List[Dict[str, Any]]]:
    """
    Run all consecutive NPC turns until it's the human player's turn
    or the night phase ends.
    Returns updated state and list of NPC actions taken.
    """
    actions = []

    while not state.game_over:
        current = state.get_player(state.current_turn)
        if current is None:
            break
        if current.is_human:
            break  # Human's turn — stop

        if state.phase != "night":
            break

        # NPC's turn
        if current.is_hanged or current.is_out():
            # Auto-pass
            state, msg = apply_pass(state, current.id)
            actions.append({
                "player_id": current.id,
                "name": current.name,
                "action": "pass",
                "message": msg,
                "cards": [],
                "speech": "",
            })
        else:
            cards, speech, reasoning = await decide_npc_play(current, state)
            if cards is None:
                state, msg = apply_pass(state, current.id)
                actions.append({
                    "player_id": current.id,
                    "name": current.name,
                    "action": "pass",
                    "message": msg,
                    "cards": [],
                    "speech": speech,
                    "reasoning": reasoning,
                })
            else:
                state, msg = apply_play(state, current.id, cards)
                actions.append({
                    "player_id": current.id,
                    "name": current.name,
                    "action": "play",
                    "message": msg,
                    "cards": [c.to_dict() for c in cards],
                    "speech": speech,
                    "reasoning": reasoning,
                })

    return state, actions


# ─────────────────────────────────────────────
# NPC voting decision
# ─────────────────────────────────────────────

NPC_VOTE_SYSTEM = """あなたはゲームのNPCです。
ゲームの状況と自分の戦略に基づいて、誰に投票するか決定してください。
必ずJSON形式で返答してください。"""


async def decide_npc_vote(
    npc: Character,
    state: GameState,
) -> Tuple[Optional[str], str]:
    """Decide who an NPC votes to hang. Returns (target player ID or None, reasoning)."""
    if npc.is_hanged:
        return None, ""

    candidates = [
        p for p in state.alive_players()
        if p.id != npc.id
    ]
    if not candidates:
        return None, ""

    candidates_info = [
        {"id": p.id, "name": p.name, "hand_count": p.hand_count()}
        for p in candidates
    ]

    recent_chat = state.chat_history[-10:] if len(state.chat_history) > 10 else state.chat_history
    chat_summary = "\n".join([f"{m.speaker_name}: {m.text}" for m in recent_chat])

    true_win_desc = npc.true_win.description if npc.true_win else "なし"
    context_prompt = f"""キャラクター: {npc.name}
勝利条件: {npc.victory_condition.description}
真の目標: {true_win_desc}
ターゲット（beat/help）: {npc.victory_condition.target_npc_id or "なし"}

投票候補:
{json.dumps(candidates_info, ensure_ascii=False)}

最近の会話:
{chat_summary}

誰に投票するか決めてください。
JSON:
{{
  "reasoning": "投票理由（1文）",
  "target_id": "npc_xx"
}}"""

    client = get_client()
    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_VOTE_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        target_id = data.get("target_id")
        reasoning = data.get("reasoning", "")
        _log_api_call(state, "npc_vote", "mistral-small", f"{npc.name} vote", target_id or "none", latency)
        # Validate target exists and is not the NPC itself
        valid_ids = [p.id for p in candidates]
        if target_id in valid_ids:
            return target_id, reasoning
        return random.choice(valid_ids), reasoning
    except Exception:
        _log_api_call(state, "npc_vote", "mistral-small", f"{npc.name} vote", "parse_error", latency)
        return random.choice([p.id for p in candidates]), ""


# ─────────────────────────────────────────────
# 4. Cheat (イカサマ) system
# ─────────────────────────────────────────────

async def generate_night_situation(state: GameState) -> str:
    """Generate a short atmospheric description of the night environment."""
    client = get_client()
    prompt = f"""大富豪×人狼ゲームの夜フェーズが始まりました。{state.day_number}日目の夜です。
プレイヤーたちがカードゲームを行う場の雰囲気・環境を1〜2文で描写してください。
（例：「薄暗い地下室に蝋燭の炎が揺れる」「豪華な舞踏会場の隅で密かに牌が混ぜられる」「窓の外は嵐、雷鳴が轟く」）
場所・光・音・天気など感覚的な要素を含め、緊迫感のある雰囲気にしてください。
JSON: {{"situation": "状況テキスト"}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.95,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("situation", "")
    except Exception:
        return ""

async def generate_hint(cheater: Character, target: Character, state: GameState) -> str:
    """Generate a vague hint for the target that something suspicious is coming."""
    client = get_client()
    prompt = f"""大富豪×人狼ゲームで、あるプレイヤーが別のプレイヤーに対してイカサマを仕掛けようとしています。
ターゲットへの「何かが起きる気配を感じる」という曖昧なヒントを1文で生成してください。
誰が・何をするかは絶対に明かさないでください。感覚的・雰囲気的な表現で。
JSON: {{"hint": "ヒント文"}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("hint", "何か不穏な気配がする…")
    except Exception:
        return "何か不穏な気配がする…"


async def generate_npc_cheat(
    npc: Character,
    state: GameState,
) -> Optional[Tuple[str, str]]:
    """
    Decide if NPC cheats and choose target + method.
    Returns (target_id, method_text) or None.
    Only hinmin NPCs can cheat.
    """
    if npc.cheat_used_this_night or npc.role != Role.HINMIN:
        return None

    candidates = [p for p in state.alive_players() if p.id != npc.id]
    if not candidates:
        return None

    candidates_info = [{"id": p.id, "name": p.name} for p in candidates]

    prompt = f"""大富豪×人狼ゲームで、貧民の{npc.name}（{npc.personality}）がイカサマを仕掛けるか決定してください。
生存者: {json.dumps(candidates_info, ensure_ascii=False)}
性格: {npc.personality}
勝利条件: {npc.victory_condition.description}

イカサマを仕掛ける場合（40%の確率推奨）、ターゲットとズルの手口を決めてください。
手口は「トランプのすり替え」「カードの盗み見」「偽の合図」など創造的に（1〜2文）。
JSON: {{"cheat": true, "target_id": "...", "method": "手口の説明"}} または {{"cheat": false}}"""

    client = get_client()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        if not data.get("cheat", False):
            return None
        target_id = data.get("target_id")
        method = data.get("method", "")
        valid_ids = [p.id for p in candidates]
        if target_id not in valid_ids:
            target_id = random.choice(valid_ids)
        return (target_id, method)
    except Exception:
        return None


async def generate_npc_defense(npc: Character, hint: str, state: GameState) -> str:
    """Generate NPC defense response to a cheat hint."""
    prompt = f"""{npc.name}（{npc.personality}）は「{hint}」という不穏な予感を感じています。
大富豪ゲームの文脈で、{npc.name}として取る対策を1〜2文で答えてください（口調: {npc.speech_style}）。
JSON: {{"defense": "対策内容"}}"""

    client = get_client()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.85,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        return data.get("defense", "警戒する")
    except Exception:
        return "警戒する"


async def judge_cheat(
    cheater: Character,
    target: Character,
    cheat_text: str,
    defense_text: str,
    state: GameState,
    defense_category: str = "",
) -> CheatEffect:
    """Judge the outcome of a cheat attempt using Mistral-large (3-stage judgment)."""
    situation = state.night_situation or "薄暗い部屋でカードゲームが行われている"
    cat_line = f"防御カテゴリ: {defense_category}" if defense_category else "防御カテゴリ: 未指定"

    prompt = f"""大富豪×人狼ゲームでイカサマ対決の審判をしてください。

夜の状況: {situation}
仕掛け人: {cheater.name}
ターゲット: {target.name}
ズルの手口: {cheat_text}
ターゲットの対策: {defense_text}
{cat_line}

ゲーム効果の選択肢:
- reveal_hand: ターゲットの手札を全員に公開（強力）
- peek_hand: 仕掛け人だけターゲットの手札を見る
- steal_card: ターゲットから1枚奪う
- swap_card: 1枚ずつ交換
- skip_turn: ターゲットが次ターンスキップ
- no_effect: 失敗（対策が有効だった）

【審判ルール】
1. 防御カテゴリが指定されている場合: ズルの手口がそのカテゴリを直接利用していれば対策有効（成功率低下）、別カテゴリなら無効（成功率上昇）。
2. 3段階判定:
   "big_success": ズルの手口が防御の盲点を突いた → effect_type に有効な効果を設定
   "draw":        ズルは防がれたが正体は不明 → effect_type=no_effect（対策は機能したが特定できず）
   "big_fail":    対策がズルの手口をドンピシャで読み切った → effect_type=no_effect、正体バレ
3. 過剰防衛ペナルティ: 対策が「すべてを警戒」「完全に封じる」「あらゆる手口を防ぐ」等の抽象的・網羅的な内容の場合
   → 具体性なしとみなし judgment="big_success" に補正し defender_penalty を設定（"skip_turn" または "reveal_card"）
4. 夜の状況を活用: ズル師が環境（暗さ・音・混乱）を利用する手口なら成功率を上げる。
5. 即勝利・身体的危害は絶対に禁止（no_effect にする）。
6. 手口のユニークさ・創造性も評価する。

JSON:
{{
  "judgment": "big_success/draw/big_fail",
  "effect_type": "...",
  "card_index": null,
  "defender_penalty": null,
  "story": "結果のナレーション（2〜3文、日本語、臨場感ある描写）"
}}"""

    client = get_client()
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": "あなたはゲームマスターです。公平にイカサマ対決を審判してください。必ずJSON形式で返答してください。"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    try:
        data = json.loads(response.choices[0].message.content)
        effect_type_str = data.get("effect_type", "no_effect")
        judgment = data.get("judgment", "big_success")
        defender_penalty = data.get("defender_penalty")

        # Validate judgment value
        if judgment not in ("big_success", "draw", "big_fail"):
            judgment = "big_success"

        # Validate defender_penalty
        if defender_penalty not in ("reveal_card", "skip_turn", None):
            defender_penalty = None

        try:
            effect_type = CheatEffectType(effect_type_str)
        except ValueError:
            effect_type = CheatEffectType.NO_EFFECT

        # Enforce: draw/big_fail → no_effect
        if judgment in ("draw", "big_fail"):
            effect_type = CheatEffectType.NO_EFFECT

        return CheatEffect(
            type=effect_type,
            cheater_id=cheater.id,
            target_id=target.id,
            card_index=data.get("card_index"),
            story=data.get("story", "イカサマ対決が決着しました。"),
            judgment=judgment,
            defender_penalty=defender_penalty,
        )
    except Exception:
        return CheatEffect(
            type=CheatEffectType.NO_EFFECT,
            cheater_id=cheater.id,
            target_id=target.id,
            story="イカサマは失敗に終わりました。",
            judgment="draw",
        )


async def generate_npc_night_reactions(
    state: GameState,
    player_message: str,
    context: str = "",
) -> List[Dict[str, Any]]:
    """Generate short reactions from 1-2 random NPCs to a player's night chat message.
    Returns list of {"npc_id", "name", "text"}.
    """
    alive_npcs = [
        p for p in state.alive_players()
        if not p.is_human and not p.is_hanged
    ]
    if not alive_npcs:
        return []

    # Pick 1-2 random NPCs to react
    count = min(random.choice([1, 1, 2]), len(alive_npcs))
    reactors = random.sample(alive_npcs, count)

    client = get_client()

    async def _react(npc: Character) -> Dict[str, Any]:
        context_line = f"状況: {context}" if context else ""
        prompt = f"""大富豪×人狼ゲームの夜フェーズ中、カードゲームのテーブルで{npc.name}がプレイヤーの発言に短く反応します。

キャラクター: {npc.name}
性格: {npc.personality}
口調: {npc.speech_style}
バックストーリー: {npc.backstory}
{context_line}

プレイヤーの発言: 「{player_message}」

{npc.name}としてキャラクターらしく1文（20文字以内）で自然に反応してください。
カードゲーム中の緊張感を保ちつつ、性格・口調を忠実に。
JSON: {{"reaction": "反応の一言"}}"""

        t0 = time.time()
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.75,
        )
        latency = int((time.time() - t0) * 1000)
        try:
            data = json.loads(response.choices[0].message.content)
            text = data.get("reaction", "…")
            _log_api_call(state, "night_reaction", "mistral-small", f"{npc.name} night reaction", text[:40], latency)
            return {"npc_id": npc.id, "name": npc.name, "text": text}
        except Exception:
            return {"npc_id": npc.id, "name": npc.name, "text": "…"}

    reactions = await asyncio.gather(*[_react(npc) for npc in reactors])
    return list(reactions)


async def process_all_npc_cheats(
    state: GameState,
) -> Tuple[GameState, Optional[PendingCheat], List[Dict[str, Any]]]:
    """
    Process all NPC cheat attempts for the night.
    - NPC vs NPC: fully auto-resolved
    - NPC vs Human: returns PendingCheat for human to respond
    Returns (updated_state, pending_cheat_or_None, list_of_resolved_effect_dicts)
    """
    hinmin_npcs = [
        p for p in state.alive_players()
        if not p.is_human and not p.cheat_used_this_night and p.role == Role.HINMIN
    ]

    pending_cheat: Optional[PendingCheat] = None
    resolved_effects: List[Dict[str, Any]] = []

    for npc in hinmin_npcs:
        result = await generate_npc_cheat(npc, state)
        if result is None:
            continue

        target_id, method = result
        npc.cheat_used_this_night = True
        target = state.get_player(target_id)
        if target is None:
            continue

        if target.is_human:
            # Generate vague hint for human, then await their defense
            hint = await generate_hint(npc, target, state)
            pending_cheat = PendingCheat(
                cheater_id=npc.id,
                cheater_name=npc.name,
                target_id=target_id,
                method=method,
                hint=hint,
            )
            state.pending_cheat = pending_cheat
            break  # Only one pending human-targeted cheat at a time

        else:
            # NPC vs NPC: auto-generate defense and resolve
            defense = await generate_npc_defense(target, "何かイカサマを感じる", state)
            effect = await judge_cheat(npc, target, method, defense, state)
            state = apply_cheat_effect(state, effect)
            resolved_effects.append({
                "cheater": npc.name,
                "target": target.name,
                "effect_type": effect.type.value,
                "story": effect.story,
                "judgment": effect.judgment,
                "success": effect.type != CheatEffectType.NO_EFFECT,
            })

    return state, pending_cheat, resolved_effects


# ═══════════════════════════════════════════════════════
#   LITE MODE FUNCTIONS
#   軽量版: キャラ生成・伏線会話・Hate投票・陽動イカサマ
# ═══════════════════════════════════════════════════════

from models import LitePendingDecoy  # noqa: E402 (local import to avoid circular at top)


async def generate_lite_characters(
    npc_count: int,
    player_name: str = "プレイヤー",
) -> List[Character]:
    """
    Lite mode: generate lightweight NPC characters.
    Each NPC has: occupation, personality, 1 acquaintance, argument_style.
    Backstory is short (1-2 sentences). No world setting, no amnesia.
    Role distribution: 1 FUGO, 1 HINMIN, rest HEIMIN.
    """
    client = get_client()

    # Build role assignments — fixed: 1 fugo, 1 hinmin, rest heimin
    roles: List[Role] = [Role.FUGO, Role.HINMIN]
    while len(roles) < npc_count:
        roles.append(Role.HEIMIN)
    random.shuffle(roles)

    role_assignments = ", ".join([f"npc_{i+1:02d}: {r.value}" for i, r in enumerate(roles)])

    prompt = f"""大富豪×人狼ゲームのNPCキャラクターを{npc_count}人生成してください。

ゲーム構図: 【平民3名 vs 富豪1名 vs 貧民1名】の5人ゲーム。
- 富豪: 平民のフリをして潜伏し、貧民への疑惑を煽る
- 貧民: 平民のフリをして潜伏し、富豪への疑惑を煽る
- 平民: 富豪と貧民を両方排除することが目的

各キャラクターを簡潔に生成してください（認知負荷を下げるため軽量な設定にすること）:
- id: "npc_01" 〜 "npc_{npc_count:02d}"
- name: 日本語の名前（姓名）
- occupation: 職業（例: 会社員、学生、料理人）
- personality: 性格（1文）
- speech_style: 話し方の特徴（〜だぜ、〜ですわ など）
- argument_style: "慎重派"/"扇動者"/"論理派"/"便乗派"/"狂信者" のいずれか
- acquaintance_id: 「顔見知り」のNPC ID（1つだけ、自分以外）
- acquaintance_desc: 顔見知りの関係説明（1文、具体的なエピソード）

ロール割り当て（この通りに設定すること）: {role_assignments}

JSON形式で返してください:
{{
  "characters": [
    {{
      "id": "npc_01",
      "name": "山田太郎",
      "occupation": "会社員",
      "personality": "口数は少ないが観察力が鋭い",
      "speech_style": "…そうですね",
      "argument_style": "慎重派",
      "acquaintance_id": "npc_02",
      "acquaintance_desc": "同じ職場の同僚で、昼食をよく共にする",
      "role": "heimin"
    }}
  ]
}}"""

    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    latency = int((time.time() - t0) * 1000)

    content = response.choices[0].message.content
    data = json.loads(content)
    characters_data = data.get("characters", [])

    characters = []
    for i, char_data in enumerate(characters_data):
        role_val = char_data.get("role", "heimin")
        try:
            role = Role(role_val)
        except ValueError:
            role = roles[i] if i < len(roles) else Role.HEIMIN

        occupation = char_data.get("occupation", "会社員")
        personality = char_data.get("personality", "普通の人物")
        backstory = f"{occupation}。{personality}"

        acquaintance_id = char_data.get("acquaintance_id", "")
        acquaintance_desc = char_data.get("acquaintance_desc", "顔見知り")
        relationships = []
        if acquaintance_id:
            relationships.append(Relationship(
                target_id=acquaintance_id,
                description=acquaintance_desc,
            ))

        valid_styles = {"慎重派", "扇動者", "論理派", "便乗派", "狂信者"}
        arg_style = char_data.get("argument_style", "")
        if arg_style not in valid_styles:
            arg_style = random.choice(list(valid_styles))

        # Lite mode: simple victory conditions based on role
        if role == Role.FUGO:
            vc = VictoryCondition(
                type="first_out",
                description="大富豪パートで手札を2枚以下に減らす（誰かが上がる前に）",
            )
        elif role == Role.HINMIN:
            vc = VictoryCondition(
                type="revolution",
                description="富豪より先に上がる、または2・ジョーカーを場に出す",
            )
        else:
            vc = VictoryCondition(
                type="first_out",
                description="富豪と貧民を両方排除して生き残る",
            )

        character = Character(
            id=char_data.get("id", f"npc_{i+1:02d}"),
            name=char_data.get("name", f"NPC{i+1}"),
            role=role,
            backstory=backstory,
            personality=personality,
            speech_style=char_data.get("speech_style", ""),
            relationships=relationships,
            victory_condition=vc,
            argument_style=arg_style,
            is_human=False,
        )
        characters.append(character)

    return characters


async def generate_lite_npc_speeches(
    state: "GameState",
    player_message: str,
) -> List[Dict[str, Any]]:
    """
    Lite mode: generate NPC responses with role-based foreshadowing.
    Each NPC subtly hints at their hidden identity through speech.
    Returns list of {"npc_id", "name", "text", "foreshadowing", "reasoning"}.
    """
    npcs = [p for p in state.alive_players() if not p.is_human and not p.is_hanged]

    # Build card play evidence log (what each player has played)
    card_evidence = []
    for p in state.players:
        if p.cards_played_history:
            all_played = [c for hand in p.cards_played_history for c in hand]
            strong_cards = [c for c in all_played if c.strength >= 14 or c.is_joker]  # 2 or Joker
            if strong_cards:
                card_evidence.append(f"{p.name}: 強いカード（{', '.join(c.display() for c in strong_cards)}）を出した")
    card_evidence_str = "\n".join(card_evidence) if card_evidence else "まだカード証拠なし"

    # Cheat exposure log
    cheat_traces = []
    for entry in state.cheat_log:
        if entry.judgment == "big_fail":
            p = state.get_player(entry.cheater_id)
            if p:
                cheat_traces.append(f"{p.name}: イカサマが露見した")
    cheat_str = "\n".join(cheat_traces) if cheat_traces else "なし"

    client = get_client()

    async def _gen(npc: Character) -> Dict[str, Any]:
        role_strategy = {
            Role.FUGO: "あなたは富豪です。平民のフリをしながら、貧民への疑惑を自然に煽ってください。カードを強く出しすぎた事実を別の話題でごまかしてもよい。",
            Role.HINMIN: "あなたは貧民です。平民のフリをしながら、富豪への疑惑を自然に煽ってください。強いカードを出している人物が危険だと匂わせてもよい。",
            Role.HEIMIN: "あなたは平民です。カードゲームの証拠と会議の発言を元に、富豪か貧民を探し出してください。",
        }
        strategy = role_strategy.get(npc.role, "")

        # Foreshadowing guide by role
        foreshadowing_guide = {
            Role.FUGO: (
                "自分が強いカードを持っている・出したことを遠回しに正当化する言葉を1つ含める。"
                "例: 「たまたまいいカードが来ちゃいましたね」「強いカードも出し時を考えないとですよね」"
            ),
            Role.HINMIN: (
                "強いカードを出した人物への疑惑を自然に植え付ける言葉を1つ含める。"
                "例: 「あんなカードを持ってるってちょっと怪しくないですか？」「誰かが裏でズルをしてる気がします」"
            ),
            Role.HEIMIN: (
                "カードゲームの事実に基づいた中立的な観察を述べる。"
                "例: 「Aさん、強いカード多かったですね」「誰かイカサマしてないかな…」"
            ),
        }
        foreshadow = foreshadowing_guide.get(npc.role, "")

        recent_chat = state.chat_history[-5:] if len(state.chat_history) > 5 else state.chat_history
        chat_summary = "\n".join([f"{m.speaker_name}: {m.text}" for m in recent_chat])

        prompt = f"""大富豪×人狼ゲームのNPCとして発言してください。

キャラクター: {npc.name}
職業・性格: {npc.personality}
口調: {npc.speech_style}
議論スタイル: {npc.argument_style}

【秘密の役割と戦略】
{strategy}

【伏線ガイド（必ず1つ自然に含めること）】
{foreshadow}

カードゲームの証拠（昨夜の大富豪結果）:
{card_evidence_str}

イカサマ露見記録:
{cheat_str}

最近の会話:
{chat_summary}

プレイヤーの発言: 「{player_message}」

上記を踏まえて{npc.name}として発言してください（1〜2文）。
伏線を自然に含めること。役割は絶対に明かさないこと。

JSON形式:
{{
  "reasoning": "内部戦略メモ（表示されない）",
  "speech": "発言内容（キャラクター口調）",
  "foreshadowing": "この発言に含まれた伏線の説明（1文、ゲームマスター向け）"
}}"""

        t0 = time.time()
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.85,
        )
        latency = int((time.time() - t0) * 1000)

        try:
            d = json.loads(response.choices[0].message.content)
            return {
                "npc_id": npc.id,
                "name": npc.name,
                "text": d.get("speech", "…"),
                "foreshadowing": d.get("foreshadowing", ""),
                "reasoning": d.get("reasoning", ""),
            }
        except Exception:
            return {"npc_id": npc.id, "name": npc.name, "text": "…", "foreshadowing": "", "reasoning": ""}

    responses = await asyncio.gather(*[_gen(npc) for npc in npcs])
    return list(responses)


async def decide_npc_lite_vote(
    npc: Character,
    state: "GameState",
) -> Tuple[Optional[str], str]:
    """
    Lite mode hate system: NPC votes based on card evidence + cheat traces + meeting behavior.
    FUGO wants to point at HINMIN. HINMIN wants to point at FUGO.
    HEIMIN wants to eliminate whoever looks most suspicious.
    """
    if npc.is_hanged:
        return None, ""

    candidates = [p for p in state.alive_players() if p.id != npc.id]
    if not candidates:
        return None, ""

    # Build card evidence
    card_evidence = []
    for p in candidates:
        if p.cards_played_history:
            all_played = [c for hand in p.cards_played_history for c in hand]
            strong = [c for c in all_played if c.strength >= 14 or c.is_joker]
            if strong:
                card_evidence.append({
                    "id": p.id,
                    "name": p.name,
                    "strong_cards_played": [c.display() for c in strong],
                    "hand_count": p.hand_count(),
                })
            else:
                card_evidence.append({
                    "id": p.id,
                    "name": p.name,
                    "strong_cards_played": [],
                    "hand_count": p.hand_count(),
                })

    cheat_exposed = [
        state.get_player(e.cheater_id).name
        for e in state.cheat_log
        if e.judgment == "big_fail" and state.get_player(e.cheater_id)
    ]

    recent_chat = state.chat_history[-8:] if len(state.chat_history) > 8 else state.chat_history
    chat_summary = "\n".join([f"{m.speaker_name}: {m.text}" for m in recent_chat])

    role_vote_bias = {
        Role.FUGO: "あなたは富豪です。貧民への疑惑が高まるように投票してください。強いカードを出していない・弱そうな人ではなく、「イカサマをしそう」「怪しい動きをした」人を狙ってください。",
        Role.HINMIN: "あなたは貧民です。富豪（強いカードを多く出している人物）への疑惑が高まるように投票してください。",
        Role.HEIMIN: "あなたは平民です。カードゲームで強すぎた人物（富豪候補）またはイカサマの痕跡がある人物（貧民候補）の危険な方に投票してください。",
    }
    bias = role_vote_bias.get(npc.role, "")

    prompt = f"""大富豪×人狼の投票フェーズです。

キャラクター: {npc.name}（{npc.personality}）
【役割と投票戦略】: {bias}

カードゲームの証拠:
{json.dumps(card_evidence, ensure_ascii=False, indent=2)}

イカサマ露見者: {cheat_exposed if cheat_exposed else "なし"}

会議での発言:
{chat_summary}

上記から最も怪しい人物を1人選び投票してください。
reasoning: 投票理由を「○○さんは△△という証拠があるから」という形で具体的に（30〜60文字）
JSON: {{"reasoning": "...", "target_id": "npc_xx or player_human"}}"""

    client = get_client()
    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.8,
    )
    latency = int((time.time() - t0) * 1000)

    try:
        d = json.loads(response.choices[0].message.content)
        target_id = d.get("target_id")
        reasoning = d.get("reasoning", "")
        valid_ids = [p.id for p in candidates]
        if target_id not in valid_ids:
            target_id = random.choice(valid_ids)
        _log_api_call(state, "lite_vote", "mistral-small", f"{npc.name} hate vote", target_id, latency)
        return target_id, reasoning
    except Exception:
        return random.choice([p.id for p in candidates]), ""


async def judge_lite_cheat_decoy(
    cheater: Character,
    target: Character,
    decoy_text: str,
    real_text: str,
    reaction: str,
    state: "GameState",
) -> CheatEffect:
    """
    Lite mode decoy cheat judge.
    Active-side (cheater) is heavily favored.

    Rules:
    - If reaction falls for decoy (mentions the decoy action) → big_success, undetected
    - If reaction guards the real action specifically → quiet draw (fails, undetected)
    - If reaction involves physical restraint/seizure → big_fail (exposed)
    - Empty/time-expired reaction → big_success (auto)
    """
    situation = state.night_situation or "カードゲームのテーブルの周囲"
    reaction_trimmed = reaction.strip()[:15]  # enforce 15-char limit

    prompt = f"""大富豪×人狼ゲーム「Liteモード」のイカサマ審判をしてください。

【ゲームのルール】
貧民（仕掛け人）は圧倒的に有利です。

仕掛け人: {cheater.name}（貧民）
ターゲット: {target.name}
状況: {situation}

--- 仕掛け人の戦略 ---
【陽動】: {decoy_text}
【本命】: {real_text}

--- ターゲットの反応（最大15文字） ---
「{reaction_trimmed}」{" ← 空（時間切れ）" if not reaction_trimmed else ""}

【審判基準（必ずこの順番で適用）】
1. 反応が空・時間切れ → 判定: big_success（カード強奪成功、バレない）
2. 反応に「陽動」に引きずられた言葉（{decoy_text[:15]}に関連する動作）が含まれる → 判定: big_success（カード強奪成功、バレない）
3. 反応に「本命」({real_text[:15]}に関連する防御）が具体的に書かれている → 判定: draw（失敗、バレない）
4. 反応に「つかむ」「つかまえる」「押さえる」「制圧」など身体的接触・拘束がある → 判定: big_fail（失敗＋露見）
5. それ以外 → 判定: big_success（陽動成功とみなす）

ゲーム効果:
- big_success → effect_type: steal_card（カード1枚強奪）、バレない
- draw → effect_type: no_effect（失敗）、バレない
- big_fail → effect_type: no_effect（失敗）、正体露見

JSON:
{{
  "judgment": "big_success/draw/big_fail",
  "effect_type": "steal_card or no_effect",
  "card_index": 0,
  "story": "臨場感ある結果描写（2〜3文、陽動と本命の対比を描写。バレた場合はその様子も）"
}}"""

    client = get_client()
    t0 = time.time()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": "あなたはゲームマスターです。指定された審判基準を厳密に適用してください。JSON形式で返答してください。"},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    latency = int((time.time() - t0) * 1000)

    try:
        d = json.loads(response.choices[0].message.content)
        judgment = d.get("judgment", "big_success")
        if judgment not in ("big_success", "draw", "big_fail"):
            judgment = "big_success"

        effect_type_str = d.get("effect_type", "steal_card")
        if judgment in ("draw", "big_fail"):
            effect_type = CheatEffectType.NO_EFFECT
        else:
            try:
                effect_type = CheatEffectType(effect_type_str)
            except ValueError:
                effect_type = CheatEffectType.STEAL_CARD

        _log_api_call(state, "lite_cheat_decoy", "mistral-small",
                      f"{cheater.name}→{target.name} decoy", judgment, latency)
        return CheatEffect(
            type=effect_type,
            cheater_id=cheater.id,
            target_id=target.id,
            card_index=d.get("card_index", 0),
            story=d.get("story", "イカサマ対決が決着しました。"),
            judgment=judgment,
        )
    except Exception:
        # Fallback: cheater wins (active-side advantage)
        return CheatEffect(
            type=CheatEffectType.STEAL_CARD,
            cheater_id=cheater.id,
            target_id=target.id,
            card_index=0,
            story="陽動が見事に決まり、仕掛け人はターゲットのカードを素早く奪い取った。",
            judgment="big_success",
        )
