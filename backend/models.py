from enum import Enum
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    FUGO = "fugo"       # 富豪 (Rich)
    HEIMIN = "heimin"   # 平民 (Commoner)
    HINMIN = "hinmin"   # 貧民 (Poor)


class Suit(str, Enum):
    CLUBS = "clubs"
    DIAMONDS = "diamonds"
    HEARTS = "hearts"
    SPADES = "spades"
    JOKER = "joker"


# Suit strength: spades > hearts > diamonds > clubs
SUIT_STRENGTH: Dict[str, int] = {
    "clubs": 1,
    "diamonds": 2,
    "hearts": 3,
    "spades": 4,
    "joker": 99,
}

# Number strength (3 weakest, 2 strongest in standard Daifugo)
# numbers 3-13, 1=14, 2=15
NUMBER_STRENGTH: Dict[int, int] = {
    3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
    11: 11, 12: 12, 13: 13, 1: 14, 2: 15,
}


class Card(BaseModel):
    suit: str  # "clubs", "diamonds", "hearts", "spades", "joker"
    number: Optional[int] = None  # 1-13, None for joker
    is_joker: bool = False

    @property
    def strength(self) -> int:
        if self.is_joker:
            return 9999
        return NUMBER_STRENGTH.get(self.number, 0)

    @property
    def suit_strength(self) -> int:
        return SUIT_STRENGTH.get(self.suit, 0)

    def display(self) -> str:
        if self.is_joker:
            return "🃏"
        suit_symbols = {"clubs": "♣", "diamonds": "♦", "hearts": "♥", "spades": "♠"}
        num_display = {1: "A", 11: "J", 12: "Q", 13: "K"}
        num_str = num_display.get(self.number, str(self.number))
        return f"{suit_symbols.get(self.suit, '?')}{num_str}"

    def to_dict(self) -> dict:
        return {
            "suit": self.suit,
            "number": self.number,
            "is_joker": self.is_joker,
            "display": self.display(),
            "strength": self.strength,
        }


class VictoryCondition(BaseModel):
    type: Literal["first_out", "revolution", "beat_target", "help_target"]
    target_npc_id: Optional[str] = None
    description: str = ""


class Relationship(BaseModel):
    target_id: str
    description: str


class Character(BaseModel):
    id: str
    name: str
    role: Role
    backstory: str
    personality: str
    speech_style: str
    relationships: List[Relationship] = Field(default_factory=list)
    victory_condition: VictoryCondition
    hand: List[Card] = Field(default_factory=list)
    is_hanged: bool = False
    is_human: bool = False
    cards_played_history: List[List[Card]] = Field(default_factory=list)  # history of played cards per round

    def hand_count(self) -> int:
        return len(self.hand)

    def is_out(self) -> bool:
        return len(self.hand) == 0


class ChatMessage(BaseModel):
    speaker_id: str
    speaker_name: str
    text: str
    turn: int = 0


class VoteRecord(BaseModel):
    voter_id: str
    target_id: str


class GameState(BaseModel):
    game_id: str
    phase: Literal["day", "night"] = "day"
    day_number: int = 1
    players: List[Character] = Field(default_factory=list)
    table: List[Card] = Field(default_factory=list)  # cards currently on table
    last_played_by: Optional[str] = None  # who played the current table cards
    turn_order: List[str] = Field(default_factory=list)  # character IDs
    current_turn: Optional[str] = None
    consecutive_passes: int = 0  # how many consecutive passes
    votes: Dict[str, str] = Field(default_factory=dict)  # voter_id -> target_id
    chat_history: List[ChatMessage] = Field(default_factory=list)
    game_over: bool = False
    winner_ids: List[str] = Field(default_factory=list)
    revolution_active: bool = False
    out_order: List[str] = Field(default_factory=list)  # order players went out
    hanged_today: Optional[str] = None  # ID of player hanged today

    def get_player(self, player_id: str) -> Optional[Character]:
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def get_human_player(self) -> Optional[Character]:
        for p in self.players:
            if p.is_human:
                return p
        return None

    def active_players(self) -> List[Character]:
        """Players still in the game (not hanged, not out)"""
        return [p for p in self.players if not p.is_hanged and not p.is_out()]

    def alive_players(self) -> List[Character]:
        """Players not hanged (may or may not have cards)"""
        return [p for p in self.players if not p.is_hanged]


# API Request/Response Models

class StartGameRequest(BaseModel):
    npc_count: int = Field(default=4, ge=2, le=6)
    player_name: str = "プレイヤー"


class StartGameResponse(BaseModel):
    game_id: str
    state: dict
    player_id: str


class ChatRequest(BaseModel):
    game_id: str
    player_id: str
    message: str


class ChatResponse(BaseModel):
    chat_history: List[dict]
    npc_responses: List[dict]


class VoteRequest(BaseModel):
    game_id: str
    voter_id: str
    target_id: str


class VoteResponse(BaseModel):
    votes: Dict[str, str]
    message: str


class FinalizeVoteResponse(BaseModel):
    hanged_player: Optional[dict]
    vote_counts: Dict[str, int]
    state: dict


class PlayCardsRequest(BaseModel):
    game_id: str
    player_id: str
    cards: List[Card]


class PlayCardsResponse(BaseModel):
    success: bool
    message: str
    state: dict
    npc_actions: List[dict] = Field(default_factory=list)


class PassRequest(BaseModel):
    game_id: str
    player_id: str


class PassResponse(BaseModel):
    success: bool
    message: str
    state: dict
    npc_actions: List[dict] = Field(default_factory=list)
