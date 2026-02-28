"""
Mistral AI integration for:
1. Character generation at game start
2. NPC speech generation during day phase
3. NPC card play decisions during night phase
"""
import json
import os
import random
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from mistralai import Mistral

from models import (
    Card, Character, GameState, Role, VictoryCondition, Relationship
)
from game_engine import get_valid_plays


def get_client() -> Mistral:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable is not set")
    return Mistral(api_key=api_key)


# ─────────────────────────────────────────────
# 1. Character generation
# ─────────────────────────────────────────────

CHARACTER_GEN_SYSTEM = """あなたはゲームマスターです。
「大富豪×人狼」ゲームのNPCキャラクターを生成してください。
各キャラクターは独特の個性を持ち、日本の架空の社会を舞台に生き生きとしたバックストーリーを持ちます。
必ずJSON形式で返答してください。"""

CHARACTER_GEN_USER_TEMPLATE = """以下の条件で{count}人のNPCキャラクターを生成してください。

各キャラクターに必要な情報:
- id: ユニークID（例: "npc_01"）
- name: キャラクター名（日本語）
- role: "{roles_str}" のいずれか
- backstory: 背景・出自（2〜3文）
- personality: 性格の特徴（1〜2文）
- speech_style: 話し方の特徴（1文、例：「〜でございます」「〜だぜ」）
- relationships: 他キャラとの関係（最低1つ、IDと説明）
- victory_condition:
    type は "first_out"/"revolution"/"beat_target"/"help_target" のいずれか
    beat_target/help_target の場合は target_npc_id を指定
    description: 勝利条件の説明

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
      "relationships": [{{"target_id": "npc_02", "description": "..."}}],
      "victory_condition": {{"type": "first_out", "target_npc_id": null, "description": "..."}}
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


async def generate_characters(npc_count: int) -> List[Character]:
    """Generate NPC characters using Mistral AI."""
    client = get_client()
    roles, role_assignments = _build_role_assignments(npc_count)
    roles_str = "fugo（富豪）, heimin（平民）, hinmin（貧民）"

    prompt = CHARACTER_GEN_USER_TEMPLATE.format(
        count=npc_count,
        roles_str=roles_str,
        role_assignments=role_assignments,
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

        character = Character(
            id=char_data.get("id", f"npc_{i+1:02d}"),
            name=char_data.get("name", f"NPC{i+1}"),
            role=role,
            backstory=char_data.get("backstory", ""),
            personality=char_data.get("personality", ""),
            speech_style=char_data.get("speech_style", ""),
            relationships=relationships,
            victory_condition=vc,
            is_human=False,
        )
        characters.append(character)

    return characters


# ─────────────────────────────────────────────
# 2. NPC speech during day phase
# ─────────────────────────────────────────────

NPC_SPEECH_SYSTEM = """あなたはゲームのNPCキャラクターです。
与えられたキャラクター情報に基づき、そのキャラクターとして発言してください。
発言は1〜3文で簡潔に。キャラクターの口調・性格を忠実に再現してください。
自分の役割（富豪・平民・貧民）は秘密にしてください。ただし行動で匂わせることは可能です。
必ずJSON形式で返答してください。"""


async def generate_npc_speech(
    npc: Character,
    state: GameState,
    trigger: str = "general",
    player_message: Optional[str] = None,
) -> str:
    """Generate a speech line for an NPC during the day phase."""
    client = get_client()

    # Build context
    alive_names = [p.name for p in state.alive_players() if p.id != npc.id]
    hanged = [p for p in state.players if p.is_hanged]
    hanged_names = [p.name for p in hanged]

    recent_chat = state.chat_history[-6:] if len(state.chat_history) > 6 else state.chat_history
    chat_summary = "\n".join([
        f"{m.speaker_name}: {m.text}" for m in recent_chat
    ])

    # Build NPC context
    my_vc = npc.victory_condition.description
    rel_desc = "; ".join([
        f"{r.target_id}との関係: {r.description}" for r in npc.relationships
    ])

    context_prompt = f"""キャラクター情報:
名前: {npc.name}
性格: {npc.personality}
口調: {npc.speech_style}
バックストーリー: {npc.backstory}
（秘密）勝利条件: {my_vc}
関係: {rel_desc}

ゲーム状況:
日数: {state.day_number}日目
生存者: {', '.join(alive_names)}
吊られた人: {', '.join(hanged_names) if hanged_names else 'なし'}
手札枚数: {npc.hand_count()}枚

最近の会話:
{chat_summary}

{"プレイヤーの発言: " + player_message if player_message else ""}

上記を踏まえて、{npc.name}として自然な発言を1〜3文で生成してください。
JSON形式: {{"speech": "発言内容"}}"""

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_SPEECH_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        return data.get("speech", "...")
    except Exception:
        return content[:200]


async def generate_npc_speeches_for_player_message(
    state: GameState,
    player_message: str,
) -> List[Dict[str, str]]:
    """
    Generate responses from all NPCs to a player's message.
    Returns list of {"npc_id", "name", "text"}.
    """
    responses = []
    npcs = [p for p in state.alive_players() if not p.is_human and not p.is_hanged]

    for npc in npcs:
        speech = await generate_npc_speech(
            npc=npc,
            state=state,
            trigger="player_message",
            player_message=player_message,
        )
        responses.append({
            "npc_id": npc.id,
            "name": npc.name,
            "text": speech,
        })

    return responses


# ─────────────────────────────────────────────
# 3. NPC card play decision during night phase
# ─────────────────────────────────────────────

NPC_PLAY_SYSTEM = """あなたはカードゲーム「大富豪×人狼」のNPCです。
自分の勝利条件と手札を考慮して、最適なカードプレイを決定してください。
必ずJSON形式で返答してください。"""


async def decide_npc_play(
    npc: Character,
    state: GameState,
) -> Optional[List[Card]]:
    """
    Decide what cards an NPC will play (or None to pass).
    Returns list of Card objects or None for pass.
    """
    if npc.is_hanged:
        return None  # Hanged players always pass

    valid_plays = get_valid_plays(npc.hand, state.table, state.revolution_active)

    if not valid_plays:
        return None  # No valid plays, must pass

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

    context_prompt = f"""キャラクター: {npc.name}
勝利条件: {npc.victory_condition.description}
手札: {hand_display}
場のカード: {table_display}
革命状態: {"あり" if state.revolution_active else "なし"}
他プレイヤーの手札枚数: {alive_hand_counts}
出せる手役（最大10個）: {valid_plays_display}

上記を踏まえて、最も戦略的なプレイを選んでください。
- パスする場合: {{"action": "pass"}}
- カードを出す場合: {{"action": "play", "play_index": 0}} (valid_plays_displayのインデックス)
JSON形式で返答してください。"""

    client = get_client()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_PLAY_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        action = data.get("action", "pass")
        if action == "pass":
            return None
        play_index = data.get("play_index", 0)
        if 0 <= play_index < len(valid_plays):
            return valid_plays[play_index]
        return valid_plays[0]  # fallback to first valid play
    except Exception:
        # Fallback: play a random valid move or pass
        return random.choice(valid_plays) if random.random() > 0.3 else None


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
            from game_engine import apply_pass
            state, msg = apply_pass(state, current.id)
            actions.append({
                "player_id": current.id,
                "name": current.name,
                "action": "pass",
                "message": msg,
                "cards": [],
            })
        else:
            cards = await decide_npc_play(current, state)
            if cards is None:
                from game_engine import apply_pass
                state, msg = apply_pass(state, current.id)
                actions.append({
                    "player_id": current.id,
                    "name": current.name,
                    "action": "pass",
                    "message": msg,
                    "cards": [],
                })
            else:
                from game_engine import apply_play
                state, msg = apply_play(state, current.id, cards)
                actions.append({
                    "player_id": current.id,
                    "name": current.name,
                    "action": "play",
                    "message": msg,
                    "cards": [c.to_dict() for c in cards],
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
) -> Optional[str]:
    """Decide who an NPC votes to hang. Returns target player ID or None."""
    if npc.is_hanged:
        return None

    candidates = [
        p for p in state.alive_players()
        if p.id != npc.id
    ]
    if not candidates:
        return None

    candidates_info = [
        {"id": p.id, "name": p.name, "hand_count": p.hand_count()}
        for p in candidates
    ]

    recent_chat = state.chat_history[-10:] if len(state.chat_history) > 10 else state.chat_history
    chat_summary = "\n".join([f"{m.speaker_name}: {m.text}" for m in recent_chat])

    context_prompt = f"""キャラクター: {npc.name}
勝利条件: {npc.victory_condition.description}
ターゲット（beat/help）: {npc.victory_condition.target_npc_id or "なし"}

投票候補:
{json.dumps(candidates_info, ensure_ascii=False)}

最近の会話:
{chat_summary}

誰に投票するか決めてください。
JSON: {{"target_id": "npc_xx"}}"""

    client = get_client()
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": NPC_VOTE_SYSTEM},
            {"role": "user", "content": context_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.8,
    )

    content = response.choices[0].message.content
    try:
        data = json.loads(content)
        target_id = data.get("target_id")
        # Validate target exists and is not the NPC itself
        valid_ids = [p.id for p in candidates]
        if target_id in valid_ids:
            return target_id
        return random.choice(valid_ids)
    except Exception:
        return random.choice([p.id for p in candidates])
