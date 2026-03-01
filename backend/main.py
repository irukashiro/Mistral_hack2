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
    decide_npc_play,
    decide_npc_vote,
    detect_investigation_facts,
    generate_amnesia_clue,
    generate_characters,
    generate_hints,
    generate_human_relationships,
    generate_npc_defense,
    generate_npc_night_reactions,
    generate_npc_speeches_for_player_message,
    generate_night_situation,
    generate_world_setting,
    judge_cheat,
    process_all_npc_cheats,
    run_npc_turns,
    # Lite mode
    generate_lite_characters,
    generate_lite_npc_speeches,
    decide_npc_lite_vote,
    judge_lite_cheat_decoy,
    # v4
    generate_detective_result,
)
from game_engine import (
    apply_cheat_effect,
    apply_pass,
    apply_play,
    assign_roles_lite,
    assign_detective_role_lite,
    check_revolution_victory,
    compute_logic_state,
    execute_hanging,
    init_relationship_matrix,
    initialize_game,
    check_victory,
    log_card_play_facts,
    log_role_co_fact,
    tally_votes,
    transition_to_day,
    transition_to_night,
    update_all_character_states,
    update_relationship_for_cheat,
    update_relationship_for_vote,
)
from models import (
    Card,
    Character,
    ChatMessage,
    ChatRequest,
    CheatDefendRequest,
    CheatEffectType,
    CheatInitiateRequest,
    DetectiveInvestigateRequest,
    FinalizeVoteResponse,
    GameIdRequest,
    GameIdWithPlayerRequest,
    GameRole,
    GameState,
    LiteCheatDecoyRequest,
    LiteCheatReactRequest,
    LitePendingDecoy,
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


def _save_npc_play_reasoning(state: GameState, npc_actions: list):
    """Save NPC card play reasoning from run_npc_turns results to debug_log."""
    for action in npc_actions:
        reasoning = action.get("reasoning", "")
        if reasoning:
            state.debug_log.append({
                "type": "play",
                "actor": action["player_id"],
                "actor_name": action["name"],
                "reasoning": reasoning,
                "detail": {"action": action["action"], "cards": [c.get("display", "") for c in action.get("cards", [])]},
                "turn": state.day_number,
            })

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
            "state": p.state,
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

        # game_role: show to self or god-eye mode only (secret role)
        if is_self or include_hidden:
            pdata["game_role"] = p.game_role.value if p.game_role else "none"
        else:
            pdata["game_role"] = None

        # detective_result: only reveal to the detective themselves
        if is_self and p.game_role == GameRole.DETECTIVE:
            pdata["detective_result"] = state.detective_result
        else:
            pdata["detective_result"] = None

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
        "relationship_matrix": state.relationship_matrix if include_hidden else {},
        "debug_log": state.debug_log if include_hidden else [],
        "victory_reason": state.victory_reason,
        "day_chat_count": state.day_chat_count,
        "day_chat_max": 5,
        "night_chat_log": [
            {
                "speaker_id": m.speaker_id,
                "speaker_name": m.speaker_name,
                "text": m.text,
                "turn": m.turn,
            }
            for m in state.night_chat_log
        ],
        "game_mode": state.game_mode,
        "lite_pending_decoy": {
            "cheater_id": state.lite_pending_decoy.cheater_id,
            "cheater_name": state.lite_pending_decoy.cheater_name,
            "target_id": state.lite_pending_decoy.target_id,
            "decoy_text": state.lite_pending_decoy.decoy_text,
        } if state.lite_pending_decoy else None,
        "detective_used_ability": state.detective_used_ability,
        "logic_state": state.logic_state.model_dump(),
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

    # 5. Initialize relationship matrix and character states
    state = init_relationship_matrix(state)
    state = update_all_character_states(state)

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
        "debug_log": state.debug_log,
        "victory_reason": state.victory_reason,
    }


@app.post("/api/game/ghost-advance")
async def ghost_advance(request: GameIdRequest):
    """Ghost mode: run NPC turns automatically so the hanged player can observe."""
    game_id = request.game_id
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")
    try:
        state, npc_actions = await run_npc_turns(state)
        _save_npc_play_reasoning(state, npc_actions)
    except Exception:
        npc_actions = []
    return {
        "state": _state_to_dict(state, "player_human", include_hidden=True),
        "npc_actions": npc_actions,
    }


@app.post("/api/game/chat")
async def chat(request: ChatRequest):
    """Player sends a message; NPCs respond."""
    game_id = request.game_id
    player_id = request.player_id
    message = request.message

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ発言できます")

    # Check chat limit (max 5 per day phase)
    if state.day_chat_count >= 5:
        raise HTTPException(status_code=400, detail="本日の発言回数上限（5回）に達しました。投票フェーズへ進んでください。")

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
        # Save reasoning to debug_log
        if resp.get("reasoning"):
            state.debug_log.append({
                "type": "chat",
                "actor": resp["npc_id"],
                "actor_name": resp["name"],
                "reasoning": resp["reasoning"],
                "detail": {"text": resp["text"]},
                "turn": state.day_number,
            })

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

    # Increment day chat count
    state.day_chat_count += 1

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
        "day_chat_count": state.day_chat_count,
        "day_chat_max": 5,
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
    update_relationship_for_vote(state, request.voter_id, request.target_id)

    vote_counts = tally_votes(state.votes)
    return VoteResponse(
        votes=state.votes,
        message=f"{voter.name}が{target.name}に投票しました",
    )


@app.post("/api/game/npc-votes")
async def collect_npc_votes(request: GameIdRequest):
    """Trigger NPC voting decisions."""
    game_id = request.game_id
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    npcs = [p for p in state.alive_players() if not p.is_human]
    npc_vote_info = []

    for npc in npcs:
        if npc.id not in state.votes:
            try:
                target_id, reasoning = await decide_npc_vote(npc, state)
                if target_id:
                    state.votes[npc.id] = target_id
                    update_relationship_for_vote(state, npc.id, target_id)
                    target = state.get_player(target_id)
                    npc_vote_info.append({
                        "voter": npc.name,
                        "target": target.name if target else target_id,
                        "reasoning": reasoning,
                    })
                    state.debug_log.append({
                        "type": "vote",
                        "actor": npc.id,
                        "actor_name": npc.name,
                        "reasoning": reasoning,
                        "detail": {"target_id": target_id, "target_name": target.name if target else target_id},
                        "turn": state.day_number,
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
async def finalize_vote(request: GameIdRequest):
    """Finalize voting, hang the player with most votes, transition to night."""
    game_id = request.game_id
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
        if state.victory_reason:
            state.debug_log.append({
                "type": "victory",
                "actor": "",
                "actor_name": "system",
                "reasoning": state.victory_reason,
                "detail": {"winner_ids": state.winner_ids},
                "turn": state.day_number,
            })
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
    # Record strong-card facts for logic state (Lite mode logic uses this)
    log_card_play_facts(state)

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
            _save_npc_play_reasoning(state, npc_actions)
        except Exception:
            pass

    # Check if night is over (all players with cards have gone out)
    active = state.active_players()
    if len(active) <= 1 and not state.game_over:
        state = check_victory(state)
        if not state.game_over:
            state = transition_to_day(state)
            if state.game_mode == "lite":
                state.logic_state = compute_logic_state(state)

    if state.game_over and state.victory_reason:
        state.debug_log.append({
            "type": "victory",
            "actor": "",
            "actor_name": "system",
            "reasoning": state.victory_reason,
            "detail": {"winner_ids": state.winner_ids},
            "turn": state.day_number,
        })

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
            _save_npc_play_reasoning(state, npc_actions)
        except Exception:
            pass

    # Check night → day transition
    active = state.active_players()
    if len(active) <= 1 and not state.game_over:
        state = check_victory(state)
        if not state.game_over:
            state = transition_to_day(state)
            if state.game_mode == "lite":
                state.logic_state = compute_logic_state(state)

    if state.game_over and state.victory_reason:
        state.debug_log.append({
            "type": "victory",
            "actor": "",
            "actor_name": "system",
            "reasoning": state.victory_reason,
            "detail": {"winner_ids": state.winner_ids},
            "turn": state.day_number,
        })

    return PassResponse(
        success=True,
        message=msg,
        state=_state_to_dict(state, request.player_id),
        npc_actions=npc_actions,
    )


@app.post("/api/game/night-chat")
async def night_chat(request: ChatRequest):
    """Player sends a message during the night phase; 1-2 NPCs react briefly."""
    game_id = request.game_id
    player_id = request.player_id
    message = request.message

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみ使用できます")

    # Add player message to night chat log
    player = state.get_player(player_id)
    player_name = player.name if player else "プレイヤー"
    state.night_chat_log.append(ChatMessage(
        speaker_id=player_id,
        speaker_name=player_name,
        text=message,
        turn=state.day_number,
    ))

    # Generate NPC reactions
    try:
        reactions = await generate_npc_night_reactions(state, message)
    except Exception as e:
        reactions = []

    for r in reactions:
        state.night_chat_log.append(ChatMessage(
            speaker_id=r["npc_id"],
            speaker_name=r["name"],
            text=r["text"],
            turn=state.day_number,
        ))

    return {
        "reactions": reactions,
        "night_chat_log": [
            {
                "speaker_id": m.speaker_id,
                "speaker_name": m.speaker_name,
                "text": m.text,
                "turn": m.turn,
            }
            for m in state.night_chat_log
        ],
    }


@app.post("/api/game/cheat-initiate")
async def cheat_initiate(request: CheatInitiateRequest):
    """Human player (hinmin) initiates a cheat against an NPC."""
    game_id = request.game_id
    cheater_id = request.cheater_id
    target_id = request.target_id
    method = request.method

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
        is_big_fail = effect.judgment == "big_fail"
        update_relationship_for_cheat(state, cheater_id, target_id, success=not is_big_fail)
        state = update_all_character_states(state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"イカサマ処理エラー: {str(e)}")

    return {
        "story": effect.story,
        "success": effect.type != CheatEffectType.NO_EFFECT,
        "effect_type": effect.type.value,
        "state": _state_to_dict(state, "player_human"),
    }


@app.post("/api/game/cheat-defend")
async def cheat_defend(request: CheatDefendRequest):
    """Human player defends against an NPC's pending cheat."""
    game_id = request.game_id
    defender_id = request.defender_id
    defense_method = request.defense_method
    defense_category = request.defense_category

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
        is_big_fail = effect.judgment == "big_fail"
        update_relationship_for_cheat(state, pending.cheater_id, pending.target_id, success=not is_big_fail)
        state = update_all_character_states(state)
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
async def cheat_skip(request: GameIdWithPlayerRequest):
    """Human player skips their cheat opportunity this night."""
    game_id = request.game_id
    player_id = request.player_id

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    player = state.get_player(player_id)
    if player:
        player.cheat_used_this_night = True

    return {"state": _state_to_dict(state, "player_human")}


@app.post("/api/game/cheat-phase-complete")
async def cheat_phase_complete(request: GameIdRequest):
    """Mark the cheat phase as done and start NPC card play turns."""
    game_id = request.game_id

    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")

    state.night_cheat_phase_done = True
    state.pending_cheat = None

    try:
        state, npc_actions = await run_npc_turns(state)
        _save_npc_play_reasoning(state, npc_actions)
    except Exception:
        npc_actions = []

    return {
        "state": _state_to_dict(state, "player_human"),
        "npc_actions": npc_actions,
    }


@app.post("/api/game/end-night")
async def end_night(request: GameIdRequest):
    """Manually end the night phase and transition to day."""
    game_id = request.game_id
    state = game_store.get(game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")

    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズではありません")

    state = transition_to_day(state)
    return {"state": _state_to_dict(state, "player_human")}


# ═══════════════════════════════════════════════════════════
#   LITE MODE ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.post("/api/game/start-lite", response_model=StartGameResponse)
async def start_game_lite(request: StartGameRequest):
    """Lite mode: 5-player fixed composition (3 HEIMIN + 1 FUGO + 1 HINMIN).
    Lightweight characters, no amnesia, no world setting."""
    # Force 4 NPCs (total 5 players)
    npc_count = 4

    try:
        npc_characters = await generate_lite_characters(npc_count, player_name=request.player_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャラクター生成エラー: {str(e)}")

    human_id = "player_human"

    # Assign role to human player from the lite pool (1 fugo, 1 hinmin, 3 heimin across all 5)
    # Since generate_lite_characters assigns 4 NPC roles: 1 fugo + 1 hinmin + 2 heimin
    # Human gets the remaining 1 heimin slot... OR randomize properly.
    # Actually: we need 5 total players with 1 fugo, 1 hinmin, 3 heimin.
    # generate_lite_characters(4) does: 1 fugo, 1 hinmin, 2 heimin for 4 NPCs.
    # Human player → gets the 3rd heimin role.
    # But we could randomize this differently. Let's do a full 5-player role draw and assign one to human.
    all_roles = assign_roles_lite(5)
    npc_roles = all_roles[:4]
    human_role = all_roles[4]

    # Override NPC roles to match the 5-player distribution
    for i, npc in enumerate(npc_characters):
        npc.role = npc_roles[i]
        # Update victory condition to match new role
        if npc.role == Role.FUGO:
            npc.victory_condition = VictoryCondition(
                type="first_out",
                description="大富豪パートで手札を2枚以下に減らす（誰かが上がる前に）",
            )
        elif npc.role == Role.HINMIN:
            npc.victory_condition = VictoryCondition(
                type="revolution",
                description="富豪より先に上がる、または2・ジョーカーを場に出す",
            )
        else:
            npc.victory_condition = VictoryCondition(
                type="first_out",
                description="富豪と貧民を両方排除して生き残る",
            )
        # Ensure each lite NPC also has a secret true_win (assign randomly if missing)
        if not npc.true_win:
            TRUE_WIN_TYPES = ["revenge_on", "protect", "climber", "martyr", "class_default"]
            tw_type = random.choice(TRUE_WIN_TYPES)
            target_id = None
            if tw_type in ("revenge_on", "protect"):
                # choose a target among NPCs or the human
                choices = [c.id for c in npc_characters if c.id != npc.id] + ["player_human"]
                target_id = random.choice(choices) if choices else None
            npc.true_win = None
            try:
                npc.true_win = type(npc).model_fields.get('true_win') and npc.true_win
            except Exception:
                pass
            # Fallback: set via pydantic model construction
            from models import TrueWinCondition
            npc.true_win = TrueWinCondition(type=tw_type, target_id=target_id, description=(f"ターゲット: {target_id}" if target_id else ""))

    role_desc = {
        Role.FUGO: "平民のフリをして潜伏し、貧民への疑惑を煽る",
        Role.HINMIN: "平民のフリをして潜伏し、富豪への疑惑を煽る",
        Role.HEIMIN: "富豪と貧民を両方排除することが目的",
    }
    if human_role == Role.FUGO:
        vc = VictoryCondition(
            type="first_out",
            description="大富豪パートで手札を2枚以下に減らす（誰かが上がる前に）",
        )
    elif human_role == Role.HINMIN:
        vc = VictoryCondition(
            type="revolution",
            description="富豪より先に上がる、または2・ジョーカーを場に出す",
        )
    else:
        vc = VictoryCondition(
            type="first_out",
            description="富豪と貧民を両方排除して生き残る",
        )

    human_character = Character(
        id=human_id,
        name=request.player_name,
        role=human_role,
        backstory=f"あなたは{human_role.value}（{role_desc.get(human_role, '')}）として参加する。",
        personality="プレイヤー",
        speech_style="自由",
        victory_condition=vc,
        is_human=True,
    )

    all_characters = [human_character] + npc_characters

    state = initialize_game(all_characters, human_id)
    state.game_mode = "lite"

    state = init_relationship_matrix(state)
    # v4: Assign detective role to one HEIMIN player
    assign_detective_role_lite(state.players)
    state = update_all_character_states(state)
    game_store[state.game_id] = state

    role_jp = {"fugo": "富豪", "hinmin": "貧民", "heimin": "平民"}
    intro_text = (
        f"【Liteモード】5人ゲーム開始！\n"
        f"あなたの役割は「{role_jp.get(human_role.value, '不明')}」です。\n"
        f"目標: {vc.description}\n"
        f"議論を始めてください。（昼チャット上限: 5回）"
    )
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


@app.post("/api/game/lite/chat")
async def lite_chat(request: ChatRequest):
    """Lite mode: player speaks; NPCs respond with role-based foreshadowing."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードではありません")
    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ発言できます")
    if state.day_chat_count >= 5:
        raise HTTPException(status_code=400, detail="本日の発言回数上限（5回）に達しました。投票フェーズへ進んでください。")

    player = state.get_player(request.player_id)
    player_name = player.name if player else "プレイヤー"
    state.chat_history.append(ChatMessage(
        speaker_id=request.player_id,
        speaker_name=player_name,
        text=request.message,
        turn=state.day_number,
    ))

    # Parse human player CO from message keywords
    _CO_KEYWORDS = {
        "探偵": "detective",
        "平民": "heimin",
        "富豪": "fugo",
        "貧民": "hinmin",
    }
    msg = request.message
    for kw, role in _CO_KEYWORDS.items():
        if kw in msg and ("CO" in msg or "です" in msg or "だ" in msg or "宣言" in msg):
            log_role_co_fact(state, request.player_id, player_name, role)
            break

    try:
        npc_responses = await generate_lite_npc_speeches(state, request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NPC発言生成エラー: {str(e)}")

    for resp in npc_responses:
        state.chat_history.append(ChatMessage(
            speaker_id=resp["npc_id"],
            speaker_name=resp["name"],
            text=resp["text"],
            turn=state.day_number,
        ))
        if resp.get("reasoning") or resp.get("foreshadowing"):
            state.debug_log.append({
                "type": "chat",
                "actor": resp["npc_id"],
                "actor_name": resp["name"],
                "reasoning": resp.get("reasoning", ""),
                "detail": {"text": resp["text"], "foreshadowing": resp.get("foreshadowing", "")},
                "turn": state.day_number,
            })

    # Recompute logic state after this round of chat
    state.logic_state = compute_logic_state(state)

    state.day_chat_count += 1

    return {
        "chat_history": [
            {"speaker_id": m.speaker_id, "speaker_name": m.speaker_name, "text": m.text, "turn": m.turn}
            for m in state.chat_history[-20:]
        ],
        "npc_responses": npc_responses,
        "day_chat_count": state.day_chat_count,
        "day_chat_max": 5,
        "logic_state": state.logic_state.model_dump(),
    }


@app.post("/api/game/lite/npc-votes")
async def lite_npc_votes(request: GameIdRequest):
    """Lite mode: trigger NPC voting with the hate system."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードではありません")

    npcs = [p for p in state.alive_players() if not p.is_human]
    npc_vote_info = []

    for npc in npcs:
        if npc.id not in state.votes:
            try:
                target_id, reasoning = await decide_npc_lite_vote(npc, state)
                if target_id:
                    state.votes[npc.id] = target_id
                    update_relationship_for_vote(state, npc.id, target_id)
                    target = state.get_player(target_id)
                    npc_vote_info.append({
                        "voter": npc.name,
                        "target": target.name if target else target_id,
                        "reasoning": reasoning,
                    })
                    state.debug_log.append({
                        "type": "vote",
                        "actor": npc.id,
                        "actor_name": npc.name,
                        "reasoning": reasoning,
                        "detail": {"target_id": target_id},
                        "turn": state.day_number,
                    })
            except Exception:
                pass

    return {
        "votes": state.votes,
        "vote_counts": tally_votes(state.votes),
        "npc_vote_info": npc_vote_info,
    }


@app.post("/api/game/lite/cheat-decoy")
async def lite_cheat_decoy(request: LiteCheatDecoyRequest):
    """Lite mode: hinmin submits decoy + real cheat. Stores pending decoy for defender."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードではありません")
    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみイカサマできます")

    cheater = state.get_player(request.cheater_id)
    target = state.get_player(request.target_id)

    if cheater is None or cheater.is_hanged:
        raise HTTPException(status_code=400, detail="無効なプレイヤーです")
    if target is None or target.is_hanged:
        raise HTTPException(status_code=400, detail="無効なターゲットです")
    if cheater.cheat_used_this_night:
        raise HTTPException(status_code=400, detail="今夜すでにイカサマを使いました")

    cheater.cheat_used_this_night = True

    if target.is_human:
        # Human is the target — store pending decoy for them to react to
        state.lite_pending_decoy = LitePendingDecoy(
            cheater_id=cheater.id,
            cheater_name=cheater.name,
            target_id=target.id,
            decoy_text=request.decoy_text,
            real_text=request.real_text,
        )
        return {
            "pending": True,
            "decoy_shown": request.decoy_text,
            "state": _state_to_dict(state, "player_human"),
        }
    else:
        # NPC is the target — auto-generate a short reaction for the NPC
        # NPC reacts to decoy (simplified: random chance of falling for it)
        fell_for_decoy = random.random() < 0.65  # 65% chance NPC is fooled
        npc_reaction = "上を見る" if fell_for_decoy else "手元を押さえる"
        effect = await judge_lite_cheat_decoy(
            cheater, target,
            request.decoy_text, request.real_text,
            npc_reaction if fell_for_decoy else "手元のカードを強く握る",
            state,
        )
        state = apply_cheat_effect(state, effect)
        update_relationship_for_cheat(state, cheater.id, target.id, success=(effect.judgment == "big_success"))
        state = update_all_character_states(state)
        return {
            "pending": False,
            "story": effect.story,
            "judgment": effect.judgment,
            "effect_type": effect.type.value,
            "state": _state_to_dict(state, request.cheater_id),
        }


@app.post("/api/game/lite/cheat-react")
async def lite_cheat_react(request: LiteCheatReactRequest):
    """Lite mode: human defender reacts to the decoy (15-char limit)."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードではありません")
    if state.lite_pending_decoy is None:
        raise HTTPException(status_code=400, detail="陽動イカサマが待機していません")

    pending = state.lite_pending_decoy
    cheater = state.get_player(pending.cheater_id)
    target = state.get_player(pending.target_id)

    if cheater is None or target is None:
        raise HTTPException(status_code=400, detail="プレイヤーが見つかりません")

    # Enforce 15-char reaction limit
    reaction = request.reaction[:15] if request.reaction else ""

    effect = await judge_lite_cheat_decoy(
        cheater, target,
        pending.decoy_text, pending.real_text,
        reaction,
        state,
    )
    state = apply_cheat_effect(state, effect)
    update_relationship_for_cheat(state, pending.cheater_id, pending.target_id,
                                  success=(effect.judgment == "big_success"))
    state = update_all_character_states(state)
    state.lite_pending_decoy = None

    cheater_revealed = (effect.judgment == "big_fail")

    return {
        "story": effect.story,
        "judgment": effect.judgment,
        "effect_type": effect.type.value,
        "cheater_revealed": cheater_revealed,
        "cheater_name": pending.cheater_name if cheater_revealed else None,
        "state": _state_to_dict(state, "player_human"),
    }


@app.post("/api/game/lite/detective-investigate")
async def lite_detective_investigate(request: DetectiveInvestigateRequest):
    """Lite mode: detective investigates one player at night start (1-time use)."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードではありません")
    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみ利用できます")

    detective = state.get_player(request.detective_id)
    if detective is None or detective.game_role != GameRole.DETECTIVE:
        raise HTTPException(status_code=403, detail="あなたは探偵ではありません")
    if state.detective_used_ability:
        raise HTTPException(status_code=400, detail="探偵能力は1回しか使えません")

    target = state.get_player(request.target_id)
    if target is None or target.is_hanged:
        raise HTTPException(status_code=400, detail="無効なターゲットです")

    result = generate_detective_result(state, request.target_id, request.info_type)

    state.detective_used_ability = True
    state.detective_result = result

    state.debug_log.append({
        "type": "detective",
        "actor": request.detective_id,
        "actor_name": detective.name,
        "reasoning": result.get("display", ""),
        "detail": result,
        "turn": state.day_number,
    })

    return {
        "result": result,
        "message": result.get("display", "調査完了"),
    }


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


_AUTO_DAY_TRIGGERS = [
    "では会議を始めましょう。昨夜の大富豪の結果を踏まえ、怪しい人物について話し合ってください。",
    "探偵の方は名乗り出てください。また、証拠をもとに疑惑の人物を指摘してください。",
    "投票の前に最後の発言をどうぞ。誰を処刑すべきか、理由とともに述べてください。",
]


@app.post("/api/game/lite/auto-day")
async def lite_auto_day(request: GameIdRequest):
    """Run the entire Lite day phase automatically — no player input needed."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.game_mode != "lite":
        raise HTTPException(status_code=400, detail="Liteモードのみ対応")
    if state.phase != "day":
        raise HTTPException(status_code=400, detail="昼フェーズでのみ実行できます")

    all_chat = []

    # Run 3 rounds of NPC-only discussion
    for trigger in _AUTO_DAY_TRIGGERS:
        state.chat_history.append(ChatMessage(
            speaker_id="system", speaker_name="【進行】", text=trigger, turn=state.day_number,
        ))
        all_chat.append({"speaker_id": "system", "speaker_name": "【進行】", "text": trigger, "turn": state.day_number})

        try:
            npc_responses = await generate_lite_npc_speeches(state, trigger)
        except Exception:
            npc_responses = []

        for resp in npc_responses:
            state.chat_history.append(ChatMessage(
                speaker_id=resp["npc_id"], speaker_name=resp["name"],
                text=resp["text"], turn=state.day_number,
            ))
            all_chat.append({
                "speaker_id": resp["npc_id"], "speaker_name": resp["name"],
                "text": resp["text"], "turn": state.day_number,
            })
            if resp.get("reasoning") or resp.get("foreshadowing"):
                state.debug_log.append({
                    "type": "chat", "actor": resp["npc_id"], "actor_name": resp["name"],
                    "reasoning": resp.get("reasoning", ""),
                    "detail": {"text": resp["text"], "foreshadowing": resp.get("foreshadowing", "")},
                    "turn": state.day_number,
                })
        state.day_chat_count += 1

    state.logic_state = compute_logic_state(state)

    # NPC voting
    npcs = [p for p in state.alive_players() if not p.is_human]
    npc_vote_info = []
    for npc in npcs:
        if npc.id not in state.votes:
            try:
                target_id, reasoning = await decide_npc_lite_vote(npc, state)
                if target_id:
                    state.votes[npc.id] = target_id
                    update_relationship_for_vote(state, npc.id, target_id)
                    target = state.get_player(target_id)
                    npc_vote_info.append({
                        "voter": npc.name,
                        "target": target.name if target else target_id,
                        "reasoning": reasoning,
                    })
            except Exception:
                pass

    # Tally and execute hanging
    vote_counts = tally_votes(state.votes)
    hanged_player_data = None
    if vote_counts:
        max_votes = max(vote_counts.values())
        top_targets = [pid for pid, cnt in vote_counts.items() if cnt == max_votes]
        hanged_id = random.choice(top_targets)
        state = execute_hanging(state, hanged_id)
        hanged = state.get_player(hanged_id)
        if hanged:
            hanged_player_data = {
                "id": hanged.id, "name": hanged.name, "role": hanged.role.value,
                "hand": [c.to_dict() for c in hanged.hand],
                "victory_condition": hanged.victory_condition.description,
            }

    if state.game_over:
        return {
            "state": _state_to_dict(state, "player_human"),
            "chat_log": all_chat, "vote_counts": vote_counts,
            "hanged_player": hanged_player_data, "npc_vote_info": npc_vote_info,
            "night_situation": "",
        }

    state = transition_to_night(state)
    log_card_play_facts(state)
    try:
        state.night_situation = await generate_night_situation(state)
    except Exception:
        state.night_situation = ""

    return {
        "state": _state_to_dict(state, "player_human"),
        "chat_log": all_chat, "vote_counts": vote_counts,
        "hanged_player": hanged_player_data, "npc_vote_info": npc_vote_info,
        "night_situation": state.night_situation,
    }


@app.post("/api/game/auto-play")
async def auto_play_turn(request: GameIdRequest):
    """Auto-play the human player's current night turn (treats them like an NPC)."""
    state = game_store.get(request.game_id)
    if state is None:
        raise HTTPException(status_code=404, detail="ゲームが見つかりません")
    if state.phase != "night":
        raise HTTPException(status_code=400, detail="夜フェーズでのみ実行できます")

    human = state.get_human_player()
    if human is None:
        raise HTTPException(status_code=400, detail="プレイヤーが見つかりません")

    all_actions = []
    msg = ""

    if state.current_turn == human.id and not human.is_out() and not human.is_hanged:
        cards, speech, reasoning = await decide_npc_play(human, state)
        if cards:
            state, msg = apply_play(state, human.id, cards)
            if "革命" in msg and state.revolution_active:
                state = check_revolution_victory(state)
            all_actions.append({
                "player_id": human.id, "name": human.name + "（オート）",
                "action": "play", "message": msg,
                "cards": [c.to_dict() for c in cards],
                "speech": speech, "reasoning": reasoning,
            })
        else:
            state, msg = apply_pass(state, human.id)
            all_actions.append({
                "player_id": human.id, "name": human.name + "（オート）",
                "action": "pass", "message": msg,
                "cards": [], "speech": "", "reasoning": reasoning,
            })

    # Run subsequent NPC turns (stops when it's human's turn again or night ends)
    if not state.game_over and state.phase == "night":
        state, npc_actions = await run_npc_turns(state)
        _save_npc_play_reasoning(state, npc_actions)
        all_actions.extend(npc_actions)

    if state.phase == "day" and state.game_mode == "lite":
        state.logic_state = compute_logic_state(state)

    if state.game_over and state.victory_reason:
        state.debug_log.append({
            "type": "victory", "actor": "", "actor_name": "system",
            "reasoning": state.victory_reason,
            "detail": {"winner_ids": state.winner_ids},
            "turn": state.day_number,
        })

    return {
        "success": True, "message": msg,
        "state": _state_to_dict(state, human.id),
        "npc_actions": all_actions,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
