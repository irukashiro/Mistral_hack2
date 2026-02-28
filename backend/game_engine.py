"""
Game engine for Daifugo (大富豪) card game logic.
Pure functions where possible for testability.
"""
import random
import uuid
from typing import Dict, List, Optional, Tuple

from models import (
    Card, Character, CheatEffect, CheatEffectType, GameState, Role, Suit,
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

    return state


def transition_to_day(state: GameState) -> GameState:
    """Switch to day phase."""
    state.phase = "day"
    state.day_number += 1
    state.votes = {}
    state.hanged_today = None
    # Deal new cards? No — in Daifugo cards persist. But for this game we re-deal each round
    # Actually in this game design, we do NOT re-deal. Cards persist until players go out.
    return state


# ─────────────────────────────────────────────
# Victory condition checks
# ─────────────────────────────────────────────

def check_victory(state: GameState) -> GameState:
    """Check if game is over and determine winners."""
    alive = state.alive_players()

    # Game ends if 1 or fewer alive players have cards
    players_with_cards = [p for p in alive if not p.is_out()]
    if len(players_with_cards) > 1:
        return state  # game continues

    winners = []
    for player in state.players:
        vc = player.victory_condition

        if vc.type == "first_out":
            # Win by being first to discard all cards
            if state.out_order and state.out_order[0] == player.id:
                winners.append(player.id)

        elif vc.type == "revolution":
            # Win if revolution was triggered at least once
            if state.revolution_active:
                winners.append(player.id)

        elif vc.type == "beat_target":
            # Win if target was hanged or finished after you
            target = state.get_player(vc.target_npc_id)
            if target and target.is_hanged:
                winners.append(player.id)
            elif target and target.id in state.out_order and player.id in state.out_order:
                if state.out_order.index(player.id) < state.out_order.index(target.id):
                    winners.append(player.id)

        elif vc.type == "help_target":
            # Win if target finishes first or survives to end
            target = state.get_player(vc.target_npc_id)
            if target and not target.is_hanged:
                if state.out_order and state.out_order[0] == target.id:
                    winners.append(player.id)

    if winners:
        state.game_over = True
        state.winner_ids = winners

    return state


def check_revolution_victory(state: GameState) -> GameState:
    """Called when revolution triggers — check revolution-type victory conditions."""
    for player in state.players:
        if player.victory_condition.type == "revolution" and player.id not in state.winner_ids:
            state.winner_ids.append(player.id)
    if state.winner_ids:
        state.game_over = True
    return state


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
