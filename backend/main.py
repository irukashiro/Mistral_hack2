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
    generate_characters,
    generate_npc_speeches_for_player_message,
    run_npc_turns,
)
from game_engine import (
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


def _state_to_dict(state: GameState, requesting_player_id: str = None) -> dict:
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
        # Show role to: the player themselves, hanged players (revealed), requesting player
        is_self = p.is_human or (requesting_player_id and p.id == requesting_player_id)
        if is_self or p.is_hanged:
            pdata["role"] = p.role.value
        else:
            pdata["role"] = None  # hidden

        # Show hand to: self, or hanged (public hand)
        if is_self or p.is_hanged:
            pdata["hand"] = [c.to_dict() for c in p.hand]
        else:
            pdata["hand"] = None  # hidden

        players_data.append(pdata)

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
    """Start a new game: generate characters, deal cards, set up state."""
    try:
        # Generate NPC characters via Mistral AI
        npc_characters = await generate_characters(request.npc_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"キャラクター生成エラー: {str(e)}")

    # Create human player character
    human_id = "player_human"
    human_role = random.choice(list(Role))
    human_character = Character(
        id=human_id,
        name=request.player_name,
        role=human_role,
        backstory="あなた自身です。",
        personality="プレイヤー",
        speech_style="自由",
        victory_condition=VictoryCondition(
            type="first_out",
            description="最初に全ての手札を出し切る",
        ),
        is_human=True,
    )

    all_characters = [human_character] + npc_characters

    # Initialize game
    state = initialize_game(all_characters, human_id)

    # Add to store
    game_store[state.game_id] = state

    # Add opening chat messages
    state.chat_history.append(ChatMessage(
        speaker_id="system",
        speaker_name="システム",
        text=f"ゲームが始まりました。本日は{state.day_number}日目です。議論を始めてください。",
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
    return _state_to_dict(state, player_id)


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

    # Generate NPC responses
    try:
        npc_responses = await generate_npc_speeches_for_player_message(state, message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"NPC発言生成エラー: {str(e)}")

    for resp in npc_responses:
        state.chat_history.append(ChatMessage(
            speaker_id=resp["npc_id"],
            speaker_name=resp["name"],
            text=resp["text"],
            turn=state.day_number,
        ))

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

    # Transition to night phase
    state = transition_to_night(state)

    # After transitioning to night, run NPC turns until human's turn
    try:
        state, npc_actions = await run_npc_turns(state)
    except Exception:
        npc_actions = []

    return {
        "hanged_player": hanged_player_data,
        "vote_counts": vote_counts,
        "state": _state_to_dict(state, "player_human"),
        "npc_actions": npc_actions,
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


@app.delete("/api/game/{game_id}")
async def delete_game(game_id: str):
    """Delete a game."""
    if game_id in game_store:
        del game_store[game_id]
        return {"message": "ゲームを削除しました"}
    raise HTTPException(status_code=404, detail="ゲームが見つかりません")
