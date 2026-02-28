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
    Card, Character, CheatEffect, CheatEffectType, GameState, PendingCheat,
    Role, VictoryCondition, Relationship
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


# ─────────────────────────────────────────────
# 4. Cheat (イカサマ) system
# ─────────────────────────────────────────────

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
) -> CheatEffect:
    """Judge the outcome of a cheat attempt using Mistral-large."""
    prompt = f"""大富豪×人狼ゲームでイカサマ対決の審判をしてください。

仕掛け人: {cheater.name}
ターゲット: {target.name}
ズルの手口: {cheat_text}
ターゲットの対策: {defense_text}

ゲーム効果の選択肢:
- reveal_hand: ターゲットの手札を全員に公開（強力）
- peek_hand: 仕掛け人だけターゲットの手札を見る
- steal_card: ターゲットから1枚奪う
- swap_card: 1枚ずつ交換
- skip_turn: ターゲットが次ターンスキップ
- no_effect: 失敗（手口が粗すぎるか、対策が有効だった）

審判ルール:
- ズルが成功すれば仕掛け人に有利な効果を選ぶ
- 対策が有効なら no_effect
- 即勝利・身体的危害は絶対に禁止（no_effect にする）
- 手口のユニークさ・創造性も評価する

JSON: {{"success": true/false, "effect_type": "...", "card_index": null, "story": "結果のナレーション（2〜3文、日本語）"}}"""

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
        try:
            effect_type = CheatEffectType(effect_type_str)
        except ValueError:
            effect_type = CheatEffectType.NO_EFFECT

        return CheatEffect(
            type=effect_type,
            cheater_id=cheater.id,
            target_id=target.id,
            card_index=data.get("card_index"),
            story=data.get("story", "イカサマ対決が決着しました。"),
        )
    except Exception:
        return CheatEffect(
            type=CheatEffectType.NO_EFFECT,
            cheater_id=cheater.id,
            target_id=target.id,
            story="イカサマは失敗に終わりました。",
        )


async def process_all_npc_cheats(
    state: GameState,
) -> Tuple[GameState, Optional[PendingCheat], List[Dict[str, Any]]]:
    """
    Process all NPC cheat attempts for the night.
    - NPC vs NPC: fully auto-resolved
    - NPC vs Human: returns PendingCheat for human to respond
    Returns (updated_state, pending_cheat_or_None, list_of_resolved_effect_dicts)
    """
    from game_engine import apply_cheat_effect

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
                "success": effect.type != CheatEffectType.NO_EFFECT,
            })

    return state, pending_cheat, resolved_effects
