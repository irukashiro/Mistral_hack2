"""
FastAPI backend for Class Conflict: Millionaire (大富豪×人狼)
"""
import os
import random
import uuid
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from ai_service import (
    decide_npc_vote,
    detect_investigation_facts,
    generate_amnesia_clue,
    generate_characters,
    generate_hints,
    generate_human_relationships,
    generate_npc_defense,
    generate_npc_speeches_for_player_message,
    generate_night_situation,
    generate_world_setting,
    judge_cheat,
    process_all_npc_cheats,
    run_npc_turns,
)
from game_engine import (
    apply_cheat_effect,
    apply_pass,
    apply_play,
    check_revolution_victory,
    execute_hanging,
    initialize_game,
    check_victory,
    tally_votes,
    transition_to_day,
    transition_to_night,
)
from models import (
    Card,
    Character,
    ChatMessage,
    CheatEffectType,
    FinalizeVoteResponse,
    GameState,
    PassRequest,
    PassResponse,
    PlayCardsRequest,
    PlayCardsResponse,
    Role,
    StartGameRequest,
    StartGameResponse,
    VictoryCondition,
    VoteRequest,
    VoteResponse,
)

app = FastAPI(title="Class Conflict: Millionaire", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory game state store (single game for hackathon)
game_store: Dict[str, GameState] = {}


def _state_to_dict(
    state: GameState,
    requesting_player_id: str = None,
    include_hidden: bool = False,
) -> dict:
    """Convert game state to dict, hiding private info where appropriate."""
    players_data = []
    for p in state.players:
        pdata = {
            "id": p.id,
            "name": p.name,
            "is_human": p.is_human,
            "is_hanged": p.is_hanged,
            "is_out": p.is_out(),
            "hand_count": p.hand_count(),
            "victory_condition_description": p.victory_condition.description,
        }
        # Show role to: the player themselves, hanged players (revealed), or hidden mode
        is_self = p.is_human or (requesting_player_id and p.id == requesting_player_id)
        if is_self or p.is_hanged or include_hidden:
            pdata["role"] = p.role.value
        else:
            pdata["role"] = None  # hidden

        # Show hand to: self, hanged (public hand), hand_revealed via cheat, or hidden mode
        if is_self or p.is_hanged or p.hand_revealed or include_hidden:
            pdata["hand"] = [c.to_dict() for c in p.hand]
        else:
            pdata["hand"] = None  # hidden

        pdata["cheat_used_this_night"] = p.cheat_used_this_night
        pdata["hand_revealed"] = p.hand_revealed
        pdata["skip_next_turn"] = p.skip_next_turn
        pdata["argument_style"] = p.argument_style
        pdata["true_win"] = p.true_win.model_dump() if p.true_win else None

        # Show backstory and relationships for self or in hidden mode
        if is_self or include_hidden:
            pdata["backstory"] = p.backstory
            pdata["relationships"] = [
                {"target_id": r.target_id, "description": r.description}
                for r in p.relationships
            ]

        # Debug fields present only in hidden mode
        if include_hidden:
            pdata["_debug_role"] = p.role.value
            pdata["_debug_backstory"] = p.backstory
            pdata["_debug_true_win"] = p.true_win.model_dump() if p.true_win else None

        players_data.append(pdata)

    # Ghost mode: human player is hanged and requesting
    human = state.get_human_player()
    is_ghost_mode = (
        human is not None
        and human.is_hanged
        and requesting_player_id is not None
        and human.id == requesting_player_id
    )

    return {
        "game_id": state.game_id,
        "phase": state.phase,
        "day_number": state.day_number,
        "players": players_data,
        "table": [c.to_dict() for c in state.table],
        "last_played_by": state.last_played_by,
        "current_turn": state.current_turn,
        "turn_order": state.turn_order,
        "votes": state.votes,
        "chat_history": [
            {
                "speaker_id": m.speaker_id,
                "speaker_name": m.speaker_name,
                "text": m.text,
                "turn": m.turn,
            }
            for m in state.chat_history
        ],
        "game_over": state.game_over,
        "winner_ids": state.winner_ids,
        "revolution_active": state.revolution_active,
        "out_order": state.out_order,
        "hanged_today": state.hanged_today,
        "consecutive_passes": state.consecutive_passes,
        "table_clear_count": state.table_clear_count,
        "night_cheat_phase_done": state.night_cheat_phase_done,
        "pending_cheat": {
            "hint": state.pending_cheat.hint,
            "target_id": state.pending_cheat.target_id,
        } if state.pending_cheat else None,
        "cheat_log": [
            {
                "type": e.type.value,
                "cheater_id": e.cheater_id,
                "target_id": e.target_id,
                "story": e.story,
                "judgment": e.judgment,
            }
            for e in state.cheat_log
        ],
        "night_situation": state.night_situation,
        "investigation_notes": state.investigation_notes,
        "amnesia_clues": state.amnesia_clues,
        "is_ghost_mode": is_ghost_mode,
    }


# ─────────────────────────────────────────────
# Static files (frontend)
# ─────────────────────────────────────────────

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


@app.get("/")
async def serve_frontend():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Class Conflict: Millionaire API", "docs": "/docs"}


# ─────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────

@app.post("/api/game/start", response_model=StartGameResponse)
async def start_game(request: StartGameRequest):
    """Start a new game: generate world setting, characters, deal cards, set up state."""
    # 1. Generate shared world setting first
    try:
        world_setting = await generate_world_setting()
    except Exception:
        world_setting = {}

    # 2. Generate NPC characters with world setting context
    try:
        npc_characters = await generate_characters(request.npc_count, world_setting=world_setting, player_name=request.player_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャラクター生成エラー: {str(e)}")

    # Create human player character — amnesiac who doesn't know their own past
    human_id = "player_human"
    human_role = random.choice(list(Role))
    amnesia_backstory = (
        "……記憶がない。気がつくと、この場所にいた。"
        "自分の名前さえ、誰かに教えてもらったものだ。"
        "しかし、ここにいる人々のどこかに、見覚えのある顔がある気がする。"
    )
    human_character = Character(
        id=human_id,
        name=request.player_name,
        role=human_role,
        backstory=amnesia_backstory,
        personality="記憶喪失のプレイヤー — 何かを知っているはずなのに、思い出せない",
        speech_style="自由",
        victory_condition=VictoryCondition(
            type="first_out",
            description="最初に全ての手札を出し切る",
        ),
        is_human=True,
    )

    # 3. Generate relationships for the human player with world setting context
    try:
        human_rels = await generate_human_relationships(
            request.player_name, npc_characters, world_setting=world_setting
        )
        human_character.relationships = human_rels
    except Exception:
        pass  # Relationships are optional

    all_characters = [human_character] + npc_characters

    # Initialize game
    state = initialize_game(all_characters, human_id)

    # 4. Save world setting to state
    state.world_setting = world_setting

    # Add to store
    game_store[state.game_id] = state

    # Add opening chat message using world setting info
    setting_name = world_setting.get('setting_name', '')
    location = world_setting.get('location', '')
    if setting_name:
        intro_text = f"【{setting_name}】{(' — ' + location) if location else ''}\nゲームが始まりました。本日は{state.day_number}日目です。議論を始めてください。"
    else:
        intro_text = f"ゲームが始まりました。本日は{state.day_number}日目です。議論を始めてください。"
    state.chat_history.append(ChatMessage(
        speaker_id="system",
        speaker_name="システム",
        text=intro_text,
        turn=state.day_number,
    ))

    return StartGameResponse(
        game_id=state.game_id,
        state=_state_to_dict(state, human_id),
        player_id=human_id,
    )


@app.get("/api/game/state")
async def get_game_state(game_id: str, player_id: str = "player_human"):
    """Get the current game state."""
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    human = state.get_human_player()
    is_ghost = human is not None and human.is_hanged and human.id == player_id
    return _state_to_dict(state, player_id, include_hidden=is_ghost)


@app.get("/api/game/hints")
async def get_hints(game_id: str, player_id: str = "player_human"):
    """Get AI-generated action hints and template messages for the player (day phase only)."""
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ利用できます")
    player = state.get_player(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="プレイヤーが見つかりません")
    try:
        result = await generate_hints(state, player)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ヒント生成エラー: {str(e)}")


@app.get("/api/game/debug-state")
async def debug_state(game_id: str):
    """Return full game state with all hidden information (god eye mode)."""
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    return _state_to_dict(state, requesting_player_id=None, include_hidden=True)


@app.get("/api/game/result")
async def full_reveal(game_id: str):
    """Return full character disclosure for the result screen."""
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    characters = []
    for p in state.players:
        characters.append({
            "id": p.id,
            "name": p.name,
            "role": p.role.value,
            "backstory": p.backstory,
            "personality": p.personality,
            "speech_style": p.speech_style,
            "argument_style": p.argument_style,
            "is_human": p.is_human,
            "is_hanged": p.is_hanged,
            "victory_condition": p.victory_condition.description,
            "true_win": p.true_win.model_dump() if p.true_win else None,
            "relationships": [
                {"target_id": r.target_id, "description": r.description}
                for r in p.relationships
            ],
        })

    # Build flat relationship web across all players
    relationship_web = []
    for p in state.players:
        for r in p.relationships:
            relationship_web.append({
                "from_id": p.id,
                "from_name": p.name,
                "to_id": r.target_id,
                "description": r.description,
            })

    return {
        "characters": characters,
        "relationship_web": relationship_web,
        "winner_ids": state.winner_ids,
        "out_order": state.out_order,
        "cheat_log": [
            {
                "type": e.type.value,
                "cheater_id": e.cheater_id,
                "target_id": e.target_id,
                "story": e.story,
                "judgment": e.judgment,
            }
            for e in state.cheat_log
        ],
        "world_setting": state.world_setting,
        "amnesia_clues": state.amnesia_clues,
    }


@app.post("/api/game/ghost-advance")
async def ghost_advance(request: dict):
    """Ghost mode: run NPC turns automatically so the hanged player can observe."""
    game_id = request.get("game_id")
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")
    try:
        state, npc_actions = await run_npc_turns(state)
    except Exception:
        npc_actions = []
    return {
        "state": _state_to_dict(state, "player_human", include_hidden=True),
        "npc_actions": npc_actions,
    }


@app.post("/api/game/chat")
async def chat(request: dict):
    """Player sends a message; NPCs respond."""
    game_id = request.get("game_id")
    player_id = request.get("player_id", "player_human")
    message = request.get("message", "")

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ発言できます")

    # Add player message to history
    player = state.get_player(player_id)
    player_name = player.name if player else "プレイヤー"

    state.chat_history.append(ChatMessage(
        speaker_id=player_id,
        speaker_name=player_name,
        text=message,
        turn=state.day_number,
    ))

    # Generate NPC responses (pass world setting for richer references)
    try:
        npc_responses = await generate_npc_speeches_for_player_message(
            state, message, world_setting=state.world_setting
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NPC発言生成エラー: {str(e)}")

    for resp in npc_responses:
        state.chat_history.append(ChatMessage(
            speaker_id=resp["npc_id"],
            speaker_name=resp["name"],
            text=resp["text"],
            turn=state.day_number,
        ))

    # Extract investigation facts from NPC responses
    try:
        new_facts = await detect_investigation_facts(npc_responses, state)
        state.investigation_notes = (state.investigation_notes + new_facts)[-20:]
    except Exception:
        pass

    # Try to reveal an amnesia clue from NPC responses (40% chance)
    try:
        clue = await generate_amnesia_clue(npc_responses, state.world_setting, state.amnesia_clues)
        if clue:
            state.amnesia_clues = (state.amnesia_clues + [clue])[-15:]
    except Exception:
        pass

    return {
        "chat_history": [
            {
                "speaker_id": m.speaker_id,
                "speaker_name": m.speaker_name,
                "text": m.text,
                "turn": m.turn,
            }
            for m in state.chat_history[-20:]
        ],
        "npc_responses": npc_responses,
        "investigation_notes": state.investigation_notes,
        "amnesia_clues": state.amnesia_clues,
    }


@app.post("/api/game/vote")
async def vote(request: VoteRequest):
    """Record a vote for hanging."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ投票できます")

    voter = state.get_player(request.voter_id)
    target = state.get_player(request.target_id)

    if voter is None or voter.is_hanged:
        raise HTTPException(status_code=400, detail="投票できないプレイヤーです")
    if target is None or target.is_hanged:
        raise HTTPException(status_code=400, detail="無効な投票先です")
    if request.voter_id == request.target_id:
        raise HTTPException(status_code=400, detail="自分自身には投票できません")

    state.votes[request.voter_id] = request.target_id

    vote_counts = tally_votes(state.votes)
    return VoteResponse(
        votes=state.votes,
        message=f"{voter.name}が{target.name}に投票しました",
    )


@app.post("/api/game/npc-votes")
async def collect_npc_votes(request: dict):
    """Trigger NPC voting decisions."""
    game_id = request.get("game_id")
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    npcs = [p for p in state.alive_players() if not p.is_human]
    npc_vote_info = []

    for npc in npcs:
        if npc.id not in state.votes:
            try:
                target_id = await decide_npc_vote(npc, state)
                if target_id:
                    state.votes[npc.id] = target_id
                    target = state.get_player(target_id)
                    npc_vote_info.append({
                        "voter": npc.name,
                        "target": target.name if target else target_id,
                    })
            except Exception:
                pass  # Skip failed NPC votes

    vote_counts = tally_votes(state.votes)
    return {
        "votes": state.votes,
        "vote_counts": vote_counts,
        "npc_vote_info": npc_vote_info,
    }


@app.post("/api/game/finalize-vote")
async def finalize_vote(request: dict):
    """Finalize voting, hang the player with most votes, transition to night."""
    game_id = request.get("game_id")
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ実行できます")

    vote_counts = tally_votes(state.votes)

    hanged_player_data = None
    if vote_counts:
        # Find player with most votes (random tiebreak)
        max_votes = max(vote_counts.values())
        top_targets = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
        hanged_id = random.choice(top_targets)

        state = execute_hanging(state, hanged_id)
        hanged = state.get_player(hanged_id)
        if hanged:
            hanged_player_data = {
                "id": hanged.id,
                "name": hanged.name,
                "role": hanged.role.value,
                "hand": [c.to_dict() for c in hanged.hand],
                "victory_condition": hanged.victory_condition.description,
            }

    # If an instant victory triggered (martyr/revenge/beat_target), return game-over state
    if state.game_over:
        return {
            "hanged_player": hanged_player_data,
            "vote_counts": vote_counts,
            "state": _state_to_dict(state, "player_human"),
            "pending_cheat": None,
            "human_can_cheat": False,
            "npc_cheat_results": [],
            "night_situation": "",
        }

    # Transition to night phase
    state = transition_to_night(state)

    # Generate night situation flavor text
    try:
        state.night_situation = await generate_night_situation(state)
    except Exception:
        state.night_situation = ""

    # Process NPC cheat attempts (may produce a pending_cheat for human)
    npc_cheat_results = []
    pending_cheat_data = None
    try:
        state, pending_cheat, npc_cheat_results = await process_all_npc_cheats(state)
        if pending_cheat:
            pending_cheat_data = {"hint": pending_cheat.hint, "target_id": pending_cheat.target_id}
    except Exception:
        pass

    # Determine if human can cheat (hinmin who hasn't cheated yet)
    human = state.get_human_player()
    human_can_cheat = (
        human is not None
        and human.role == Role.HINMIN
        and not human.cheat_used_this_night
        and not human.is_hanged
    )

    return {
        "hanged_player": hanged_player_data,
        "vote_counts": vote_counts,
        "state": _state_to_dict(state, "player_human"),
        "pending_cheat": pending_cheat_data,
        "human_can_cheat": human_can_cheat,
        "npc_cheat_results": npc_cheat_results,
        "night_situation": state.night_situation,
    }


@app.post("/api/game/play-cards")
async def play_cards(request: PlayCardsRequest):
    """Human player plays cards during night phase."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみカードを出せます")

    if state.current_turn != request.player_id:
        raise HTTPException(status_code=400, detail="あなたのターンではありません")

    state, msg = apply_play(state, request.player_id, request.cards)

    if "革命" in msg and state.revolution_active:
        state = check_revolution_victory(state)

    npc_actions = []
    if not state.game_over:
        # Run NPC turns
        try:
            state, npc_actions = await run_npc_turns(state)
        except Exception:
            pass

    # Check if night is over (all players with cards have gone out)
    active = state.active_players()
    if len(active) <= 1 and not state.game_over:
        state = check_victory(state)
        if not state.game_over:
            state = transition_to_day(state)

    return PlayCardsResponse(
        success=True,
        message=msg,
        state=_state_to_dict(state, request.player_id),
        npc_actions=npc_actions,
    )


@app.post("/api/game/pass")
async def pass_turn(request: PassRequest):
    """Human player passes during night phase."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみパスできます")

    if state.current_turn != request.player_id:
        raise HTTPException(status_code=400, detail="あなたのターンではありません")

    state, msg = apply_pass(state, request.player_id)

    npc_actions = []
    if not state.game_over:
        try:
            state, npc_actions = await run_npc_turns(state)
        except Exception:
            pass

    # Check night → day transition
    active = state.active_players()
    if len(active) <= 1 and not state.game_over:
        state = check_victory(state)
        if not state.game_over:
            state = transition_to_day(state)

    return PassResponse(
        success=True,
        message=msg,
        state=_state_to_dict(state, request.player_id),
        npc_actions=npc_actions,
    )


@app.post("/api/game/cheat-initiate")
async def cheat_initiate(request: dict):
    """Human player (hinmin) initiates a cheat against an NPC."""
    game_id = request.get("game_id")
    cheater_id = request.get("cheater_id", "player_human")
    target_id = request.get("target_id")
    method = request.get("method", "")

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみイカサマできます")

    cheater = state.get_player(cheater_id)
    target = state.get_player(target_id)

    if cheater is None or cheater.is_hanged:
        raise HTTPException(status_code=400, detail="無効なプレイヤーです")
    if target is None or target.is_hanged or target.is_human:
        raise HTTPException(status_code=400, detail="無効なターゲットです")
    if cheater.cheat_used_this_night:
        raise HTTPException(status_code=400, detail="今夜すでにイカサマを使いました")

    cheater.cheat_used_this_night = True

    try:
        defense = await generate_npc_defense(target, "何かイカサマを感じる", state)
        effect = await judge_cheat(cheater, target, method, defense, state)
        state = apply_cheat_effect(state, effect)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"イカサマ処理エラー: {str(e)}")

    return {
        "story": effect.story,
        "success": effect.type != CheatEffectType.NO_EFFECT,
        "effect_type": effect.type.value,
        "state": _state_to_dict(state, "player_human"),
    }


@app.post("/api/game/cheat-defend")
async def cheat_defend(request: dict):
    """Human player defends against an NPC's pending cheat."""
    game_id = request.get("game_id")
    defender_id = request.get("defender_id", "player_human")
    defense_method = request.get("defense_method", "")
    defense_category = request.get("defense_category", "")

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.pending_cheat is None:
        raise HTTPException(status_code=400, detail="防御すべきイカサマがありません")

    pending = state.pending_cheat
    cheater = state.get_player(pending.cheater_id)
    target = state.get_player(pending.target_id)

    if cheater is None or target is None:
        raise HTTPException(status_code=400, detail="プレイヤーが見つかりません")

    try:
        effect = await judge_cheat(cheater, target, pending.method, defense_method, state,
                                   defense_category=defense_category)
        state = apply_cheat_effect(state, effect)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"防御処理エラー: {str(e)}")

    # Reveal cheater identity only on big_fail (defense read the cheat perfectly)
    cheater_revealed = (effect.judgment == "big_fail")
    state.pending_cheat = None

    return {
        "story": effect.story,
        "success": effect.type != CheatEffectType.NO_EFFECT,
        "cheater_revealed": cheater_revealed,
        "cheater_name": pending.cheater_name if cheater_revealed else None,
        "effect_type": effect.type.value,
        "state": _state_to_dict(state, "player_human"),
    }


@app.post("/api/game/cheat-skip")
async def cheat_skip(request: dict):
    """Human player skips their cheat opportunity this night."""
    game_id = request.get("game_id")
    player_id = request.get("player_id", "player_human")

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    player = state.get_player(player_id)
    if player:
        player.cheat_used_this_night = True

    return {"state": _state_to_dict(state, "player_human")}


@app.post("/api/game/cheat-phase-complete")
async def cheat_phase_complete(request: dict):
    """Mark the cheat phase as done and start NPC card play turns."""
    game_id = request.get("game_id")

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")

    state.night_cheat_phase_done = True
    state.pending_cheat = None

    try:
        state, npc_actions = await run_npc_turns(state)
    except Exception:
        npc_actions = []

    return {
        "state": _state_to_dict(state, "player_human"),
        "npc_actions": npc_actions,
    }


@app.post("/api/game/end-night")
async def end_night(request: dict):
    """Manually end the night phase and transition to day."""
    game_id = request.get("game_id")
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")

    state = transition_to_day(state)
    return {"state": _state_to_dict(state, "player_human")}


@app.get("/api/game/list")
async def list_games():
    """List all active games (debug endpoint)."""
    return {
        "games": [
            {"game_id": gid, "phase": s.phase, "day": s.day_number, "over": s.game_over}
            for gid, s in game_store.items()
        ]
    }


@app.post("/api/game/{game_id}/delete")
async def delete_game(game_id: str):
    """Delete a game."""
    if game_id in game_store:
        del game_store[game_id]
        return {"message": "ゲームを削除しました"}
    raise HTTPException(status_code=404, detail="ゲームが見つかりません")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
