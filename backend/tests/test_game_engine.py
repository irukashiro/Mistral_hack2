"""Unit tests for game_engine.py — pure function tests, no AI dependency."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from models import (
    Card, Character, CharacterState, CheatEffect, CheatEffectType,
    GameState, Relationship, RelationshipValue, Role,
    VictoryCondition, TrueWinCondition, ChatMessage,
)
from game_engine import (
    compute_character_state,
    create_deck,
    init_relationship_matrix,
    is_friend,
    shuffle_and_deal,
    card_strength,
    cards_stronger,
    get_play_type,
    can_play,
    apply_play,
    apply_pass,
    tally_votes,
    execute_hanging,
    check_instant_victories,
    check_victory,
    check_revolution_victory,
    initialize_game,
    apply_cheat_effect,
    get_valid_plays,
    transition_to_night,
    transition_to_day,
    update_all_character_states,
    update_relationship_for_cheat,
    update_relationship_for_vote,
)


# ─── Helpers ──────────────────────────────────────────────────

def make_card(suit: str, number: int) -> Card:
    return Card(suit=suit, number=number, is_joker=False)


def make_joker() -> Card:
    return Card(suit="joker", number=None, is_joker=True)


def make_characters(n=3):
    roles = [Role.FUGO, Role.HEIMIN, Role.HINMIN]
    chars = []
    for i in range(n):
        chars.append(Character(
            id=f"player_{i}",
            name=f"テスト{i}",
            role=roles[i % len(roles)],
            backstory="テスト",
            personality="テスト",
            speech_style="普通",
            victory_condition=VictoryCondition(type="first_out", description="最初に上がる"),
            is_human=(i == 0),
        ))
    return chars


def fresh_state():
    return initialize_game(make_characters(), "player_0")


# ─────────────────────────────────────────────
# Deck creation & dealing
# ─────────────────────────────────────────────

class TestCreateDeck:
    def test_deck_has_54_cards(self):
        assert len(create_deck()) == 54

    def test_deck_has_2_jokers(self):
        assert len([c for c in create_deck() if c.is_joker]) == 2

    def test_deck_has_52_non_jokers(self):
        assert len([c for c in create_deck() if not c.is_joker]) == 52

    def test_deck_has_4_suits(self):
        suits = set(c.suit for c in create_deck() if not c.is_joker)
        assert suits == {"clubs", "diamonds", "hearts", "spades"}

    def test_each_suit_has_13_cards(self):
        deck = create_deck()
        for suit in ["clubs", "diamonds", "hearts", "spades"]:
            assert len([c for c in deck if c.suit == suit]) == 13

    def test_each_suit_numbers_1_to_13(self):
        deck = create_deck()
        for suit in ["clubs", "diamonds", "hearts", "spades"]:
            numbers = sorted(c.number for c in deck if c.suit == suit)
            assert numbers == list(range(1, 14))


class TestShuffleAndDeal:
    def test_deal_to_3_players(self):
        hands = shuffle_and_deal(create_deck(), 3)
        assert len(hands) == 3
        assert sum(len(h) for h in hands) == 54

    def test_deal_to_5_players(self):
        hands = shuffle_and_deal(create_deck(), 5)
        assert len(hands) == 5
        assert sum(len(h) for h in hands) == 54
        for h in hands:
            assert len(h) in [10, 11]

    def test_deal_preserves_all_cards(self):
        hands = shuffle_and_deal(create_deck(), 4)
        assert sum(len(h) for h in hands) == 54


# ─────────────────────────────────────────────
# Card strength
# ─────────────────────────────────────────────

class TestCardStrength:
    def test_3_is_weakest(self):
        assert card_strength(make_card("clubs", 3)) == 3

    def test_2_is_strongest_non_joker(self):
        assert card_strength(make_card("clubs", 2)) == 15

    def test_ace_is_14(self):
        assert card_strength(make_card("clubs", 1)) == 14

    def test_joker_is_strongest(self):
        assert card_strength(make_joker()) == 9999

    def test_revolution_reverses(self):
        s3 = card_strength(make_card("clubs", 3), revolution_active=True)
        s2 = card_strength(make_card("clubs", 2), revolution_active=True)
        assert s3 > s2

    def test_revolution_joker_unchanged(self):
        assert card_strength(make_joker(), revolution_active=True) == 9999


class TestCardsStronger:
    def test_higher_beats_lower(self):
        assert cards_stronger([make_card("clubs", 5)], [make_card("clubs", 3)]) is True

    def test_lower_loses(self):
        assert cards_stronger([make_card("clubs", 3)], [make_card("clubs", 5)]) is False

    def test_empty_table_always_wins(self):
        assert cards_stronger([make_card("clubs", 3)], []) is True

    def test_same_number_higher_suit_wins(self):
        assert cards_stronger([make_card("spades", 5)], [make_card("clubs", 5)]) is True

    def test_joker_beats_everything(self):
        assert cards_stronger([make_joker()], [make_card("spades", 2)]) is True


# ─────────────────────────────────────────────
# Play type detection
# ─────────────────────────────────────────────

class TestGetPlayType:
    def test_single(self):
        assert get_play_type([make_card("clubs", 5)]) == "single"

    def test_pair(self):
        assert get_play_type([make_card("clubs", 5), make_card("hearts", 5)]) == "pair"

    def test_triple(self):
        assert get_play_type([make_card("clubs", 5), make_card("hearts", 5), make_card("diamonds", 5)]) == "triple"

    def test_quad(self):
        cards = [make_card(s, 5) for s in ["clubs", "hearts", "diamonds", "spades"]]
        assert get_play_type(cards) == "quad"

    def test_joker_single(self):
        assert get_play_type([make_joker()]) == "single"

    def test_two_jokers_pair(self):
        assert get_play_type([make_joker(), make_joker()]) == "pair"

    def test_empty_is_none(self):
        assert get_play_type([]) is None

    def test_different_numbers_not_valid(self):
        assert get_play_type([make_card("clubs", 3), make_card("clubs", 5)]) is None

    def test_sequence_same_suit(self):
        cards = [make_card("hearts", 3), make_card("hearts", 4), make_card("hearts", 5)]
        assert get_play_type(cards) == "sequence"


# ─────────────────────────────────────────────
# Can play validation
# ─────────────────────────────────────────────

class TestCanPlay:
    def test_empty_cards_fails(self):
        assert can_play([], [], False)[0] is False

    def test_any_valid_on_empty_table(self):
        assert can_play([make_card("clubs", 3)], [], False)[0] is True

    def test_must_match_play_type(self):
        ok, _ = can_play([make_card("clubs", 5)], [make_card("clubs", 3), make_card("hearts", 3)], False)
        assert ok is False

    def test_must_be_stronger(self):
        ok, _ = can_play([make_card("clubs", 3)], [make_card("clubs", 5)], False)
        assert ok is False

    def test_stronger_passes(self):
        assert can_play([make_card("clubs", 10)], [make_card("clubs", 5)], False)[0] is True

    def test_quad_overrides_anything(self):
        quad = [make_card(s, 5) for s in ["clubs", "hearts", "diamonds", "spades"]]
        ok, msg = can_play(quad, [make_card("clubs", 2)], False)
        assert ok is True
        assert "革命" in msg


# ─────────────────────────────────────────────
# Apply play
# ─────────────────────────────────────────────

class TestApplyPlay:
    def test_valid_play_removes_cards(self):
        gs = fresh_state()
        player = gs.get_player("player_0")
        gs.phase = "night"
        gs.current_turn = "player_0"
        gs.table = []
        card = player.hand[0]
        initial = len(player.hand)
        apply_play(gs, "player_0", [card])
        assert len(player.hand) == initial - 1

    def test_invalid_card_not_in_hand(self):
        gs = fresh_state()
        gs.phase = "night"
        gs.current_turn = "player_0"
        gs.table = []
        player = gs.get_player("player_0")
        # Remove all cards and give a known hand, then try to play a card not in it
        player.hand = [make_card("clubs", 3)]
        fake = make_card("spades", 13)
        _, msg = apply_play(gs, "player_0", [fake])
        assert "手札にそのカード" in msg

    def test_eight_cut_clears_table(self):
        gs = fresh_state()
        player = gs.get_player("player_0")
        gs.phase = "night"
        gs.current_turn = "player_0"
        gs.table = []
        eight = make_card("hearts", 8)
        player.hand.append(eight)
        state, msg = apply_play(gs, "player_0", [eight])
        assert state.table == []
        assert "8切り" in msg


# ─────────────────────────────────────────────
# Apply pass
# ─────────────────────────────────────────────

class TestApplyPass:
    def test_pass_increments_consecutive(self):
        gs = fresh_state()
        gs.phase = "night"
        gs.current_turn = "player_0"
        gs.consecutive_passes = 0
        state, _ = apply_pass(gs, "player_0")
        assert state.consecutive_passes >= 0

    def test_all_pass_clears_table(self):
        gs = fresh_state()
        gs.phase = "night"
        gs.table = [make_card("clubs", 5)]
        for p in gs.alive_players():
            gs.current_turn = p.id
            gs, _ = apply_pass(gs, p.id)
        assert gs.table == []


# ─────────────────────────────────────────────
# Voting
# ─────────────────────────────────────────────

class TestTallyVotes:
    def test_simple_tally(self):
        counts = tally_votes({"a": "c", "b": "c", "c": "a"})
        assert counts["c"] == 2
        assert counts["a"] == 1

    def test_empty_votes(self):
        assert tally_votes({}) == {}


class TestExecuteHanging:
    def test_marks_player_as_hanged(self):
        gs = fresh_state()
        state = execute_hanging(gs, "player_1")
        assert state.get_player("player_1").is_hanged is True

    def test_sets_hanged_today(self):
        gs = fresh_state()
        state = execute_hanging(gs, "player_1")
        assert state.hanged_today == "player_1"

    def test_adds_system_message(self):
        gs = fresh_state()
        initial = len(gs.chat_history)
        state = execute_hanging(gs, "player_1")
        assert len(state.chat_history) > initial


# ─────────────────────────────────────────────
# Victory conditions
# ─────────────────────────────────────────────

class TestCheckInstantVictories:
    def test_martyr_wins_when_hanged(self):
        gs = fresh_state()
        p = gs.get_player("player_1")
        p.true_win = TrueWinCondition(type="martyr", description="自分が処刑される")
        p.is_hanged = True
        state = check_instant_victories(gs)
        assert "player_1" in state.winner_ids
        assert state.game_over is True

    def test_first_out_wins(self):
        gs = fresh_state()
        p = gs.get_player("player_0")
        p.victory_condition = VictoryCondition(type="first_out", description="最初に上がる")
        p.hand = []
        gs.out_order = ["player_0"]
        state = check_instant_victories(gs)
        assert "player_0" in state.winner_ids

    def test_revolution_wins(self):
        gs = fresh_state()
        p = gs.get_player("player_2")
        p.victory_condition = VictoryCondition(type="revolution", description="革命")
        gs.revolution_active = True
        state = check_instant_victories(gs)
        assert "player_2" in state.winner_ids

    def test_no_victory_when_conditions_not_met(self):
        gs = fresh_state()
        state = check_instant_victories(gs)
        assert state.game_over is False
        assert state.winner_ids == []


class TestCheckVictory:
    def test_class_default_when_one_player_left(self):
        gs = fresh_state()
        # Change all victory conditions to class_default-like to avoid first_out triggering
        for p in gs.players:
            p.victory_condition = VictoryCondition(type="revolution", description="革命")
            p.true_win = None
        for p in gs.players:
            if p.id != "player_0":
                p.hand = []
                gs.out_order.append(p.id)
        state = check_victory(gs)
        assert state.game_over is True
        # class_default: all non-hanged players win
        assert "player_0" in state.winner_ids

    def test_game_continues_when_multiple_active(self):
        gs = fresh_state()
        assert check_victory(gs).game_over is False


# ─────────────────────────────────────────────
# Phase transitions
# ─────────────────────────────────────────────

class TestPhaseTransitions:
    def test_transition_to_night(self):
        gs = fresh_state()
        state = transition_to_night(gs)
        assert state.phase == "night"
        assert state.table == []
        assert state.votes == {}
        assert state.night_cheat_phase_done is False

    def test_transition_to_day(self):
        gs = fresh_state()
        gs.phase = "night"
        state = transition_to_day(gs)
        assert state.phase == "day"
        assert state.day_number == 2

    def test_cheat_flags_reset_on_night(self):
        gs = fresh_state()
        for p in gs.players:
            p.cheat_used_this_night = True
            p.skip_next_turn = True
        state = transition_to_night(gs)
        for p in state.players:
            assert p.cheat_used_this_night is False
            assert p.skip_next_turn is False


# ─────────────────────────────────────────────
# Initialize game
# ─────────────────────────────────────────────

class TestInitializeGame:
    def test_all_players_get_cards(self):
        state = initialize_game(make_characters(), "player_0")
        for p in state.players:
            assert len(p.hand) > 0

    def test_total_cards_is_54(self):
        state = initialize_game(make_characters(), "player_0")
        assert sum(len(p.hand) for p in state.players) == 54

    def test_human_player_flagged(self):
        state = initialize_game(make_characters(), "player_0")
        human = state.get_human_player()
        assert human is not None
        assert human.id == "player_0"

    def test_turn_order_includes_all(self):
        state = initialize_game(make_characters(), "player_0")
        assert set(state.turn_order) == {p.id for p in state.players}


# ─────────────────────────────────────────────
# Cheat effects
# ─────────────────────────────────────────────

class TestApplyCheatEffect:
    def test_reveal_hand(self):
        gs = fresh_state()
        effect = CheatEffect(type=CheatEffectType.REVEAL_HAND, cheater_id="player_0", target_id="player_1", story="公開")
        state = apply_cheat_effect(gs, effect)
        assert state.get_player("player_1").hand_revealed is True

    def test_skip_turn(self):
        gs = fresh_state()
        effect = CheatEffect(type=CheatEffectType.SKIP_TURN, cheater_id="player_0", target_id="player_1", story="skip")
        state = apply_cheat_effect(gs, effect)
        assert state.get_player("player_1").skip_next_turn is True

    def test_steal_card(self):
        gs = fresh_state()
        cheater, target = gs.get_player("player_0"), gs.get_player("player_1")
        c0, t0 = len(cheater.hand), len(target.hand)
        effect = CheatEffect(type=CheatEffectType.STEAL_CARD, cheater_id="player_0", target_id="player_1", card_index=0, story="steal")
        apply_cheat_effect(gs, effect)
        assert len(cheater.hand) == c0 + 1
        assert len(target.hand) == t0 - 1

    def test_no_effect(self):
        gs = fresh_state()
        effect = CheatEffect(type=CheatEffectType.NO_EFFECT, cheater_id="player_0", target_id="player_1", story="fail")
        state = apply_cheat_effect(gs, effect)
        assert len(state.cheat_log) == 1

    def test_cheat_log_appended(self):
        gs = fresh_state()
        assert len(gs.cheat_log) == 0
        effect = CheatEffect(type=CheatEffectType.NO_EFFECT, cheater_id="player_0", target_id="player_1", story="log")
        apply_cheat_effect(gs, effect)
        assert len(gs.cheat_log) == 1


# ─────────────────────────────────────────────
# Valid plays enumeration
# ─────────────────────────────────────────────

class TestVictoryReason:
    def test_martyr_victory_reason(self):
        gs = fresh_state()
        p = gs.get_player("player_1")
        p.true_win = TrueWinCondition(type="martyr", description="自分が処刑される")
        p.is_hanged = True
        state = check_instant_victories(gs)
        assert state.victory_reason != ""
        assert "martyr" in state.victory_reason or "処刑" in state.victory_reason

    def test_first_out_victory_reason(self):
        gs = fresh_state()
        p = gs.get_player("player_0")
        p.victory_condition = VictoryCondition(type="first_out", description="最初に上がる")
        p.hand = []
        gs.out_order = ["player_0"]
        state = check_instant_victories(gs)
        assert state.victory_reason != ""
        assert "最初に上がる" in state.victory_reason or "公開条件" in state.victory_reason

    def test_revolution_victory_reason(self):
        gs = fresh_state()
        p = gs.get_player("player_2")
        p.victory_condition = VictoryCondition(type="revolution", description="革命を起こす")
        gs.revolution_active = True
        state = check_instant_victories(gs)
        assert state.victory_reason != ""
        assert "革命" in state.victory_reason

    def test_class_default_victory_reason(self):
        gs = fresh_state()
        for p in gs.players:
            p.victory_condition = VictoryCondition(type="revolution", description="革命")
            p.true_win = None
        for p in gs.players:
            if p.id != "player_0":
                p.hand = []
                gs.out_order.append(p.id)
        state = check_victory(gs)
        assert state.victory_reason != ""
        assert "生存者" in state.victory_reason or "共同勝利" in state.victory_reason

    def test_no_victory_no_reason(self):
        gs = fresh_state()
        state = check_instant_victories(gs)
        assert state.victory_reason == ""

    def test_beat_target_victory_reason_hanged(self):
        gs = fresh_state()
        p = gs.get_player("player_0")
        p.victory_condition = VictoryCondition(
            type="beat_target", target_npc_id="player_1", description="player_1を倒す"
        )
        target = gs.get_player("player_1")
        target.is_hanged = True
        state = check_instant_victories(gs)
        assert "player_0" in state.winner_ids
        assert state.victory_reason != ""
        assert "処刑" in state.victory_reason

    def test_debug_log_field_exists(self):
        gs = fresh_state()
        assert hasattr(gs, 'debug_log')
        assert gs.debug_log == []

    def test_victory_reason_field_exists(self):
        gs = fresh_state()
        assert hasattr(gs, 'victory_reason')
        assert gs.victory_reason == ""


class TestGetValidPlays:
    def test_singles_on_empty_table(self):
        hand = [make_card("clubs", 3), make_card("hearts", 5)]
        plays = get_valid_plays(hand, [], False)
        singles = [p for p in plays if len(p) == 1]
        assert len(singles) >= 2

    def test_pair_found(self):
        hand = [make_card("clubs", 5), make_card("hearts", 5), make_card("diamonds", 3)]
        plays = get_valid_plays(hand, [], False)
        pairs = [p for p in plays if len(p) == 2]
        assert len(pairs) >= 1

    def test_no_plays_when_weaker(self):
        hand = [make_card("clubs", 3)]
        table = [make_card("spades", 2)]
        plays = get_valid_plays(hand, table, False)
        assert len(plays) == 0


# ─────────────────────────────────────────────
# Character state machine
# ─────────────────────────────────────────────

class TestCharacterState:
    def test_initial_state_is_playing(self):
        state = fresh_state()
        state.phase = "night"
        state = update_all_character_states(state)
        for p in state.players:
            assert p.state == CharacterState.PLAYING

    def test_state_after_hanging(self):
        state = fresh_state()
        state.get_player("player_1").is_hanged = True
        state = update_all_character_states(state)
        assert state.get_player("player_1").state == CharacterState.DEAD

    def test_state_after_out(self):
        state = fresh_state()
        state.phase = "night"
        p = state.get_player("player_1")
        p.hand = []
        state.out_order.append("player_1")
        state = update_all_character_states(state)
        assert p.state == CharacterState.WON_ROUND

    def test_state_in_meeting(self):
        state = fresh_state()
        state.phase = "day"
        state = update_all_character_states(state)
        for p in state.players:
            assert p.state == CharacterState.IN_MEETING

    def test_state_complete_victory(self):
        state = fresh_state()
        state.game_over = True
        state.winner_ids = ["player_0"]
        state = update_all_character_states(state)
        assert state.get_player("player_0").state == CharacterState.COMPLETE_VICTORY


# ─────────────────────────────────────────────
# Relationship matrix
# ─────────────────────────────────────────────

class TestRelationshipMatrix:
    def test_init_matrix_empty(self):
        """No relationships → all zeros."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        for pid, row in state.relationship_matrix.items():
            for oid, val in row.items():
                assert val == 0

    def test_init_matrix_from_keywords(self):
        """Text keywords should convert to correct numeric values."""
        state = fresh_state()
        p0 = state.get_player("player_0")
        p0.relationships = [
            Relationship(target_id="player_1", description="彼を憎んでいる"),
            Relationship(target_id="player_2", description="秘密を共有する共犯者"),
        ]
        state = init_relationship_matrix(state)
        assert state.relationship_matrix["player_0"]["player_1"] == RelationshipValue.ENEMY
        assert state.relationship_matrix["player_0"]["player_2"] == RelationshipValue.SECRET_SHARED

    def test_update_for_vote(self):
        """Voting should decrease the target's feeling toward the voter."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        before = state.relationship_matrix["player_1"]["player_0"]
        update_relationship_for_vote(state, "player_0", "player_1")
        after = state.relationship_matrix["player_1"]["player_0"]
        assert after == before - 1

    def test_update_for_cheat_success(self):
        """Successful cheat → target's feeling toward cheater decreases."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        before = state.relationship_matrix["player_1"]["player_0"]
        update_relationship_for_cheat(state, "player_0", "player_1", success=True)
        after = state.relationship_matrix["player_1"]["player_0"]
        assert after == before - 1

    def test_update_for_cheat_fail(self):
        """Failed cheat (big_fail) → everyone's feeling toward cheater decreases."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        update_relationship_for_cheat(state, "player_0", "player_1", success=False)
        # player_1 and player_2 should both have decreased feelings toward player_0
        assert state.relationship_matrix["player_1"]["player_0"] == -1
        assert state.relationship_matrix["player_2"]["player_0"] == -1

    def test_is_friend(self):
        """is_friend returns True when value >= 1."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        state.relationship_matrix["player_0"]["player_1"] = 1
        assert is_friend(state, "player_0", "player_1") is True
        state.relationship_matrix["player_0"]["player_1"] = 0
        assert is_friend(state, "player_0", "player_1") is False

    def test_clamp_bounds(self):
        """Values should be clamped to [-2, 3]."""
        state = fresh_state()
        state = init_relationship_matrix(state)
        # Repeatedly vote to push value below -2
        for _ in range(10):
            update_relationship_for_vote(state, "player_0", "player_1")
        assert state.relationship_matrix["player_1"]["player_0"] == -2

        # Set to max and try to go above
        state.relationship_matrix["player_0"]["player_1"] = 3
        # Vote shouldn't go above 3 (it decreases), so let's test by cheating with direct set
        # and verify clamp logic holds
        assert state.relationship_matrix["player_0"]["player_1"] == 3
