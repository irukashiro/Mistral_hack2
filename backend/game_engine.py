"""
Game engine for Daifugo (大富豪) card game logic.
Pure functions where possible for testability.
"""
import random
import uuid
from typing import Dict, List, Optional, Tuple

from models import (
    Card, Character, CharacterState, CheatEffect, CheatEffectType,
    GameState, RelationshipValue, Role, Suit,
    NUMBER_STRENGTH, SUIT_STRENGTH, ChatMessage
)


# ─────────────────────────────────────────────
# Deck creation & dealing
# ─────────────────────────────────────────────

def create_deck() -> List[Card]:
    """Create a standard 54-card deck (52 + 2 jokers)."""
    deck = []
    for suit in ["clubs", "diamonds", "hearts", "spades"]:
        for number in range(1, 14):
            deck.append(Card(suit=suit, number=number, is_joker=False))
    # Add 2 jokers
    deck.append(Card(suit="joker", number=None, is_joker=True))
    deck.append(Card(suit="joker", number=None, is_joker=True))
    return deck


def shuffle_and_deal(deck: List[Card], num_players: int) -> List[List[Card]]:
    """Shuffle deck and deal cards as evenly as possible."""
    shuffled = deck.copy()
    random.shuffle(shuffled)
    hands: List[List[Card]] = [[] for _ in range(num_players)]
    for i, card in enumerate(shuffled):
        hands[i % num_players].append(card)
    return hands


def assign_roles(num_players: int) -> List[Role]:
    """Assign roles based on player count."""
    roles = []
    # 1 fugo, roughly 1/3 hinmin, rest heimin
    roles.append(Role.FUGO)
    hinmin_count = max(1, num_players // 3)
    for _ in range(hinmin_count):
        roles.append(Role.HINMIN)
    while len(roles) < num_players:
        roles.append(Role.HEIMIN)
    random.shuffle(roles)
    return roles


# ─────────────────────────────────────────────
# Card strength helpers
# ─────────────────────────────────────────────

def card_strength(card: Card, revolution_active: bool = False) -> int:
    """Return the effective strength of a card, considering revolution."""
    if card.is_joker:
        return 9999
    base = NUMBER_STRENGTH.get(card.number, 0)
    if revolution_active:
        # Reverse: 3 becomes strongest, 2 becomes weakest
        max_val = 15
        min_val = 3
        base = max_val + min_val - base
    return base


def cards_stronger(
    new_cards: List[Card],
    table_cards: List[Card],
    revolution_active: bool = False,
) -> bool:
    """Check if new_cards beat table_cards."""
    if not table_cards:
        return True
    new_str = max(card_strength(c, revolution_active) for c in new_cards)
    table_str = max(card_strength(c, revolution_active) for c in table_cards)
    if new_str != table_str:
        return new_str > table_str
    # Same number strength: compare suit strength of highest suit card
    new_suit = max(SUIT_STRENGTH.get(c.suit, 0) for c in new_cards if not c.is_joker)
    table_suit = max(SUIT_STRENGTH.get(c.suit, 0) for c in table_cards if not c.is_joker)
    return new_suit > table_suit


# ─────────────────────────────────────────────
# Play validation
# ─────────────────────────────────────────────

def get_play_type(cards: List[Card]) -> Optional[str]:
    """
    Determine if a set of cards is a valid play.
    Returns: "single", "pair", "triple", "quad", "sequence", or None
    """
    if not cards:
        return None

    jokers = [c for c in cards if c.is_joker]
    non_jokers = [c for c in cards if not c.is_joker]
    n = len(cards)

    # Single card
    if n == 1:
        return "single"

    # All jokers? Valid as single/pair
    if len(jokers) == n:
        if n == 1:
            return "single"
        if n == 2:
            return "pair"
        return None

    # Same number (pair, triple, quad) - joker can substitute
    numbers = [c.number for c in non_jokers]
    if len(set(numbers)) == 1:
        if n == 2:
            return "pair"
        if n == 3:
            return "triple"
        if n == 4:
            return "quad"
        return None

    # Sequence: 3+ cards of same suit in consecutive order (joker can substitute)
    if n >= 3:
        suits = [c.suit for c in non_jokers]
        if len(set(suits)) == 1:  # all same suit (joker excluded from suit check)
            nums_sorted = sorted(NUMBER_STRENGTH[c.number] for c in non_jokers)
            # Check consecutive (with joker filling gaps)
            expected_range = nums_sorted[-1] - nums_sorted[0] + 1
            if expected_range <= n and len(set(nums_sorted)) == len(nums_sorted):
                return "sequence"

    return None


def can_play(
    cards: List[Card],
    table: List[Card],
    revolution_active: bool = False,
) -> Tuple[bool, str]:
    """
    Validate if cards can be played on the current table.
    Returns (can_play, reason).
    """
    if not cards:
        return False, "カードを選択してください"

    play_type = get_play_type(cards)
    if play_type is None:
        return False, "無効な手役です"

    # Empty table: anything valid goes
    if not table:
        return True, "OK"

    table_type = get_play_type(table)

    # Must match play type (single->single, pair->pair, etc.)
    if play_type != table_type:
        # Exception: quad can override anything (革命)
        if play_type == "quad":
            return True, "革命！"
        return False, f"{table_type}に{play_type}は出せません"

    # Must be same count (except joker subs)
    if len(cards) != len(table):
        return False, "枚数が合いません"

    # Must be stronger
    if not cards_stronger(cards, table, revolution_active):
        return False, "場のカードより強いカードを出してください"

    return True, "OK"


# ─────────────────────────────────────────────
# Game state mutations
# ─────────────────────────────────────────────

def apply_play(
    state: GameState,
    player_id: str,
    cards: List[Card],
) -> Tuple[GameState, str]:
    """
    Apply a card play to the game state.
    Returns (new_state, message).
    """
    player = state.get_player(player_id)
    if player is None:
        return state, "プレイヤーが見つかりません"

    if player.is_hanged:
        return state, "吊られたプレイヤーはパスします"

    # Validate play
    ok, msg = can_play(cards, state.table, state.revolution_active)
    if not ok:
        return state, msg

    # Check player actually has these cards
    hand_copies = player.hand.copy()
    for card in cards:
        found = False
        for i, hcard in enumerate(hand_copies):
            if hcard.suit == card.suit and hcard.number == card.number and hcard.is_joker == card.is_joker:
                hand_copies.pop(i)
                found = True
                break
        if not found:
            return state, "手札にそのカードがありません"

    # Remove cards from hand
    player.hand = hand_copies
    player.cards_played_history.append(cards)

    # Check 8-cut
    play_numbers = [c.number for c in cards if not c.is_joker]
    eight_cut = all(n == 8 for n in play_numbers) and play_numbers

    # Check revolution (quad of same number)
    play_type = get_play_type(cards)
    revolution_triggered = False
    if play_type == "quad":
        state.revolution_active = not state.revolution_active
        revolution_triggered = True

    # Update table
    if eight_cut:
        state.table = []
        state.last_played_by = None
        state.consecutive_passes = 0
        state.table_clear_count += 1
        msg = f"8切り！場をリセットしました"
    else:
        state.table = cards
        state.last_played_by = player_id
        state.consecutive_passes = 0

    if revolution_triggered:
        msg = "革命！強弱が逆転しました！"

    # Check if player is out
    if player.is_out():
        state.out_order.append(player_id)
        msg += f" {player.name}が上がりました！"

    # Advance turn
    state = _advance_turn(state)

    # Check night phase end
    state = _check_night_end(state)

    state = update_all_character_states(state)
    return state, msg


def apply_pass(state: GameState, player_id: str) -> Tuple[GameState, str]:
    """Apply a pass action."""
    player = state.get_player(player_id)
    if player is None:
        return state, "プレイヤーが見つかりません"

    state.consecutive_passes += 1
    active = [
        pid for pid in state.turn_order
        if not state.get_player(pid).is_hanged
        and not state.get_player(pid).is_out()
    ]

    msg = f"{player.name}がパスしました"

    # If everyone still playing has passed, clear the table
    if state.consecutive_passes >= len(active):
        state.table = []
        state.last_played_by = None
        state.consecutive_passes = 0
        state.table_clear_count += 1
        msg += " — 場が流れました"

    state = _advance_turn(state)
    state = _check_night_end(state)
    return state, msg


def _advance_turn(state: GameState) -> GameState:
    """Move to next non-hanged, non-out player, skipping skip_next_turn players."""
    if not state.turn_order:
        return state

    active_ids = [
        pid for pid in state.turn_order
        if not state.get_player(pid).is_hanged
        and not state.get_player(pid).is_out()
    ]

    if len(active_ids) <= 1:
        return state  # game may be over

    current_idx = None
    for i, pid in enumerate(state.turn_order):
        if pid == state.current_turn:
            current_idx = i
            break

    if current_idx is None:
        state.current_turn = active_ids[0]
        return state

    # Find next active player, respecting skip_next_turn
    n = len(state.turn_order)
    cur_pos = current_idx
    for _ in range(n):
        cur_pos = (cur_pos + 1) % n
        next_pid = state.turn_order[cur_pos]
        if next_pid not in active_ids:
            continue
        next_player = state.get_player(next_pid)
        if next_player and next_player.skip_next_turn:
            # Reset skip flag and continue searching from here
            next_player.skip_next_turn = False
            continue
        state.current_turn = next_pid
        return state

    # Fallback: all remaining were skipped — go to first active
    if active_ids:
        state.current_turn = active_ids[0]
    return state


def _check_night_end(state: GameState) -> GameState:
    """Check if the night phase should end and transition to day."""
    # Always check if active players are nearly exhausted (game-over condition)
    active = state.active_players()
    if len(active) <= 1:
        state = check_victory(state)
        return state

    # 夜終了条件: 場が3回流れたら翌日へ
    if state.table_clear_count >= 3:
        state = check_victory(state)
        if not state.game_over:
            state = transition_to_day(state)
    return state


# ─────────────────────────────────────────────
# Voting & Hanging
# ─────────────────────────────────────────────

def tally_votes(votes: Dict[str, str]) -> Dict[str, int]:
    """Count votes per target."""
    counts: Dict[str, int] = {}
    for target_id in votes.values():
        counts[target_id] = counts.get(target_id, 0) + 1
    return counts


def execute_hanging(state: GameState, target_id: str) -> GameState:
    """Mark a player as hanged — their hand is now public, they pass forever."""
    player = state.get_player(target_id)
    if player:
        player.is_hanged = True
        state.hanged_today = target_id
        state.chat_history.append(ChatMessage(
            speaker_id="system",
            speaker_name="システム",
            text=f"【処刑】{player.name}が吊られました。手札が公開されます。",
            turn=state.day_number,
        ))
    # Check for victory conditions triggered by this hanging (martyr, revenge_on, beat_target)
    state = check_instant_victories(state)
    state = update_all_character_states(state)
    return state


def transition_to_night(state: GameState) -> GameState:
    """Switch to night phase and reset table."""
    state.phase = "night"
    state.table = []
    state.last_played_by = None
    state.consecutive_passes = 0
    state.votes = {}
    state.hanged_today = None
    state.table_clear_count = 0
    state.night_cheat_phase_done = False
    state.pending_cheat = None

    for p in state.players:
        p.cheat_used_this_night = False
        p.skip_next_turn = False

    # Build turn order from alive players
    alive_ids = [p.id for p in state.alive_players()]
    state.turn_order = alive_ids
    if alive_ids:
        state.current_turn = alive_ids[0]

    state = update_all_character_states(state)
    return state


def transition_to_day(state: GameState) -> GameState:
    """Switch to day phase."""
    state.phase = "day"
    state.day_number += 1
    state.votes = {}
    state.hanged_today = None
    state.day_chat_count = 0  # 昼チャット回数リセット
    state.night_chat_log = []  # 夜チャットログリセット
    state = update_all_character_states(state)
    return state


# ─────────────────────────────────────────────
# Victory condition checks
# ─────────────────────────────────────────────

def check_instant_victories(state: GameState) -> GameState:
    """Check victory conditions that can trigger mid-game (not just at final night end).
    Called after: any hanging, any player going out, any revolution.
    """
    if state.game_over:
        return state

    new_winners = []
    for player in state.players:
        if player.id in state.winner_ids:
            continue  # already a winner
        vc = player.victory_condition
        tw = player.true_win

        # ── Public victory condition ──────────────────────────
        if vc.type == "first_out":
            if state.out_order and state.out_order[0] == player.id:
                new_winners.append(player.id)

        elif vc.type == "revolution":
            if state.revolution_active:
                new_winners.append(player.id)

        elif vc.type == "beat_target" and vc.target_npc_id:
            target = state.get_player(vc.target_npc_id)
            if target:
                if target.is_hanged:
                    new_winners.append(player.id)
                elif (target.id in state.out_order and player.id in state.out_order
                      and state.out_order.index(player.id) < state.out_order.index(target.id)):
                    new_winners.append(player.id)

        elif vc.type == "help_target" and vc.target_npc_id:
            target = state.get_player(vc.target_npc_id)
            if target and not target.is_hanged and state.out_order and state.out_order[0] == target.id:
                new_winners.append(player.id)

        # ── True (hidden) win condition ───────────────────────
        if tw:
            if tw.type == "revenge_on" and tw.target_id:
                t = state.get_player(tw.target_id)
                if t and (t.is_hanged or (
                    t.id in state.out_order and player.id in state.out_order
                    and state.out_order.index(player.id) < state.out_order.index(t.id)
                )):
                    if player.id not in new_winners:
                        new_winners.append(player.id)

            elif tw.type == "protect" and tw.target_id:
                t = state.get_player(tw.target_id)
                if t and not t.is_hanged and state.out_order and state.out_order[0] == t.id:
                    if player.id not in new_winners:
                        new_winners.append(player.id)

            elif tw.type == "climber":
                if state.out_order and state.out_order[0] == player.id:
                    if player.id not in new_winners:
                        new_winners.append(player.id)

            elif tw.type == "martyr":
                if player.is_hanged and player.id not in new_winners:
                    new_winners.append(player.id)

    if new_winners:
        state.winner_ids.extend(new_winners)
        state.game_over = True
        state = update_all_character_states(state)
        # Build victory reason text
        reasons = []
        for pid in new_winners:
            p = state.get_player(pid)
            if not p:
                continue
            vc = p.victory_condition
            tw = p.true_win
            reason_parts = []
            if vc.type == "first_out" and state.out_order and state.out_order[0] == pid:
                reason_parts.append(f"公開条件「{vc.description}」達成（最初に上がった）")
            elif vc.type == "revolution" and state.revolution_active:
                reason_parts.append(f"公開条件「{vc.description}」達成（革命が発動中）")
            elif vc.type == "beat_target" and vc.target_npc_id:
                t = state.get_player(vc.target_npc_id)
                tname = t.name if t else vc.target_npc_id
                if t and t.is_hanged:
                    reason_parts.append(f"公開条件達成（{tname}が処刑された）")
                else:
                    reason_parts.append(f"公開条件達成（{tname}より先に上がった）")
            elif vc.type == "help_target" and vc.target_npc_id:
                t = state.get_player(vc.target_npc_id)
                tname = t.name if t else vc.target_npc_id
                reason_parts.append(f"公開条件達成（{tname}を最初に上がらせた）")
            if tw:
                if tw.type == "revenge_on" and tw.target_id:
                    t = state.get_player(tw.target_id)
                    tname = t.name if t else tw.target_id
                    reason_parts.append(f"真の目標「{tw.description}」達成（{tname}への復讐）")
                elif tw.type == "protect" and tw.target_id:
                    t = state.get_player(tw.target_id)
                    tname = t.name if t else tw.target_id
                    reason_parts.append(f"真の目標「{tw.description}」達成（{tname}を守り抜いた）")
                elif tw.type == "climber":
                    reason_parts.append(f"真の目標「{tw.description}」達成（最初に上がった）")
                elif tw.type == "martyr":
                    reason_parts.append(f"真の目標「{tw.description}」達成（自ら処刑された）")
            if reason_parts:
                reasons.append(f"{p.name}: {' / '.join(reason_parts)}")
        if reasons:
            state.victory_reason = "\n".join(reasons)

    return state


def check_victory(state: GameState) -> GameState:
    """Check if game is over at night end. First checks instant victories, then end-game fallback."""
    # Always check mid-game instant conditions first
    state = check_instant_victories(state)
    if state.game_over:
        return state

    # Game ends only if ≤1 active player still has cards
    alive = state.alive_players()
    players_with_cards = [p for p in alive if not p.is_out()]
    if len(players_with_cards) > 1:
        return state  # game continues

    # Final fallback: class_default — anyone not hanged shares the win
    if not state.winner_ids:
        for player in state.players:
            if not player.is_hanged and player.id not in state.winner_ids:
                state.winner_ids.append(player.id)
        if not state.victory_reason:
            names = [state.get_player(pid).name for pid in state.winner_ids if state.get_player(pid)]
            state.victory_reason = f"夜の終了: 生存者 ({', '.join(names)}) が共同勝利"

    if state.winner_ids:
        state.game_over = True

    return state


def check_revolution_victory(state: GameState) -> GameState:
    """Called when revolution triggers — delegates to check_instant_victories."""
    return check_instant_victories(state)


# ─────────────────────────────────────────────
# New game initialization
# ─────────────────────────────────────────────

def initialize_game(
    characters: List[Character],
    human_player_id: str,
) -> GameState:
    """Set up a fresh game state with dealt cards."""
    deck = create_deck()
    hands = shuffle_and_deal(deck, len(characters))

    for i, character in enumerate(characters):
        character.hand = hands[i]
        character.is_human = (character.id == human_player_id)

    turn_order = [c.id for c in characters]
    random.shuffle(turn_order)

    state = GameState(
        game_id=str(uuid.uuid4()),
        phase="day",
        day_number=1,
        players=characters,
        turn_order=turn_order,
        current_turn=turn_order[0],
    )

    return state


# ─────────────────────────────────────────────
# Cheat effect application
# ─────────────────────────────────────────────

def apply_cheat_effect(state: GameState, effect: CheatEffect) -> GameState:
    """Apply a resolved cheat effect to the game state."""
    cheater = state.get_player(effect.cheater_id)
    target = state.get_player(effect.target_id)

    if effect.type == CheatEffectType.REVEAL_HAND:
        if target:
            target.hand_revealed = True

    elif effect.type == CheatEffectType.STEAL_CARD:
        if cheater and target and target.hand:
            idx = effect.card_index if effect.card_index is not None else 0
            idx = min(idx, len(target.hand) - 1)
            card = target.hand.pop(idx)
            cheater.hand.append(card)

    elif effect.type == CheatEffectType.SWAP_CARD:
        if cheater and target and cheater.hand and target.hand:
            c_idx = effect.card_index if effect.card_index is not None else 0
            c_idx = min(c_idx, len(cheater.hand) - 1)
            t_idx = 0
            cheater.hand[c_idx], target.hand[t_idx] = target.hand[t_idx], cheater.hand[c_idx]

    elif effect.type == CheatEffectType.SKIP_TURN:
        if target:
            target.skip_next_turn = True

    # peek_hand and no_effect: no state change needed

    # Over-defense penalty: 防御者 (target) にもペナルティ
    if effect.defender_penalty == "reveal_card":
        if target:
            target.hand_revealed = True
    elif effect.defender_penalty == "skip_turn":
        if target:
            target.skip_next_turn = True

    state.cheat_log.append(effect)
    return state


# ─────────────────────────────────────────────
# AI helper: get valid moves for NPC
# ─────────────────────────────────────────────

def get_valid_plays(hand: List[Card], table: List[Card], revolution_active: bool) -> List[List[Card]]:
    """
    Return all valid card combinations an NPC could play.
    Simplified: returns singles, pairs, triples, quads, and sequences.
    """
    valid = []
    n = len(hand)

    # Singles
    for card in hand:
        play = [card]
        if can_play(play, table, revolution_active)[0]:
            valid.append(play)

    # Pairs, Triples, Quads (same number)
    from itertools import combinations
    for size in [2, 3, 4]:
        for combo in combinations(hand, size):
            combo_list = list(combo)
            non_jokers = [c for c in combo_list if not c.is_joker]
            if non_jokers:
                numbers = [c.number for c in non_jokers]
                if len(set(numbers)) == 1:  # same number
                    if can_play(combo_list, table, revolution_active)[0]:
                        valid.append(combo_list)

    # Sequences (3+ same suit consecutive)
    for size in range(3, n + 1):
        for combo in combinations(hand, size):
            combo_list = list(combo)
            if can_play(combo_list, table, revolution_active)[0]:
                play_type = get_play_type(combo_list)
                if play_type == "sequence":
                    valid.append(combo_list)

    return valid


# ─────────────────────────────────────────────
# Character state machine
# ─────────────────────────────────────────────

def compute_character_state(state: GameState, player: Character) -> int:
    """Compute the appropriate CharacterState code for a player."""
    if player.is_hanged:
        return CharacterState.DEAD

    if state.game_over and player.id in state.winner_ids:
        return CharacterState.COMPLETE_VICTORY

    if player.is_out():
        return CharacterState.WON_ROUND

    # Check if suspected (big_fail cheat exposure)
    for entry in state.cheat_log:
        if entry.cheater_id == player.id and entry.judgment == "big_fail":
            return CharacterState.SUSPECTED

    if state.phase == "day":
        return CharacterState.IN_MEETING

    # night phase — default to PLAYING
    return CharacterState.PLAYING


def update_all_character_states(state: GameState) -> GameState:
    """Recalculate state code for every player."""
    for player in state.players:
        player.state = compute_character_state(state, player)
    return state


# ─────────────────────────────────────────────
# Relationship matrix
# ─────────────────────────────────────────────

_ENEMY_KEYWORDS = ("敵", "憎", "復讐")
_HOSTILE_KEYWORDS = ("警戒", "不信", "疑")
_FRIENDLY_KEYWORDS = ("友", "好意")
_TRUST_KEYWORDS = ("信頼", "親密")
_SECRET_KEYWORDS = ("秘密", "共犯")


def _keyword_to_value(description: str) -> int:
    """Convert relationship description text to a numeric value via keyword matching."""
    for kw in _SECRET_KEYWORDS:
        if kw in description:
            return RelationshipValue.SECRET_SHARED
    for kw in _TRUST_KEYWORDS:
        if kw in description:
            return RelationshipValue.TRUST
    for kw in _FRIENDLY_KEYWORDS:
        if kw in description:
            return RelationshipValue.FRIENDLY
    for kw in _ENEMY_KEYWORDS:
        if kw in description:
            return RelationshipValue.ENEMY
    for kw in _HOSTILE_KEYWORDS:
        if kw in description:
            return RelationshipValue.HOSTILE
    return RelationshipValue.NEUTRAL


def init_relationship_matrix(state: GameState) -> GameState:
    """Build the initial N×N relationship matrix from AI-generated text relationships."""
    ids = [p.id for p in state.players]
    matrix: Dict[str, Dict[str, int]] = {pid: {oid: 0 for oid in ids} for pid in ids}

    for player in state.players:
        for rel in player.relationships:
            if rel.target_id in matrix[player.id]:
                matrix[player.id][rel.target_id] = _keyword_to_value(rel.description)

    state.relationship_matrix = matrix
    return state


def _clamp_rel(value: int) -> int:
    """Clamp relationship value to [-2, 3]."""
    return max(RelationshipValue.ENEMY, min(RelationshipValue.SECRET_SHARED, value))


def update_relationship_for_vote(state: GameState, voter_id: str, target_id: str) -> GameState:
    """When voter votes to hang target, the target's feeling toward voter decreases."""
    matrix = state.relationship_matrix
    if target_id in matrix and voter_id in matrix[target_id]:
        matrix[target_id][voter_id] = _clamp_rel(matrix[target_id][voter_id] - 1)
    return state


def update_relationship_for_cheat(
    state: GameState, cheater_id: str, target_id: str, success: bool
) -> GameState:
    """Update relationships after a cheat attempt.
    success=True: target's feeling toward cheater decreases.
    success=False (big_fail): everyone's feeling toward cheater decreases.
    """
    matrix = state.relationship_matrix
    if success:
        if target_id in matrix and cheater_id in matrix[target_id]:
            matrix[target_id][cheater_id] = _clamp_rel(matrix[target_id][cheater_id] - 1)
    else:
        # big_fail — all players' feelings toward cheater decrease
        for pid in matrix:
            if pid != cheater_id and cheater_id in matrix[pid]:
                matrix[pid][cheater_id] = _clamp_rel(matrix[pid][cheater_id] - 1)
    return state


def is_friend(state: GameState, a_id: str, b_id: str) -> bool:
    """Check if player a considers player b a friend (value >= 1)."""
    matrix = state.relationship_matrix
    if a_id in matrix and b_id in matrix[a_id]:
        return matrix[a_id][b_id] >= RelationshipValue.FRIENDLY
    return False
