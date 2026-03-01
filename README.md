# Class Conflict: Millionaire
### 大富豪 × 人狼 × AI感情シミュレーション

> *"It's not about card strength — it's about deception, alliance, and execution."*

A browser-based death-game adventure that reinvents the classic Japanese card game *Daifugo* (Rich Man, Poor Man) by fusing it with social deduction and **Mistral AI-powered characters**.

**Mistral AI Hackathon 2026**

---

## Demo Video

> `video/out/video.mp4` — 120-second presentation rendered with [Remotion](https://www.remotion.dev/)

---

## What is this?

Five strangers are locked in a closed space and secretly assigned to one of three classes:

| Class | Count | Goal |
|:------|:-----:|:-----|
| **Fugo (富豪 · Rich)** | 1 | Blend in, win at cards, escape execution |
| **Hinmin (貧民 · Poor)** | 1 | Use AI-powered bluffs to sabotage and frame the Fugo |
| **Heimin (平民 · Commoner)** | 3 | Find and execute the hidden threats |

**Night:** Players compete in Daifugo (card game) — but every strong card becomes evidence.
**Day:** Players debate, accuse, and vote to execute the most suspicious person.

Cards played at night become testimony in the courtroom of the day meeting. The card table is the crime scene.

---

## Key Features

### AI-Judged Decoy Bluff System
The headline mechanic — powered by Mistral AI.

The **Hinmin** player types two free-form actions:
- **【陽動 / Decoy】** — a misdirection to draw attention
- **【本命 / Real Action】** — the actual card theft

The target sees only the Decoy and has **5 seconds / 15 characters** to react.
Mistral AI judges the outcome in three tiers:

| Result | Condition | Effect |
|:-------|:----------|:-------|
| **Big Success** | Target falls for the decoy | Cards stolen, cheat stays hidden |
| **Draw** | Target guards correctly | Cheat fails, hidden |
| **Big Fail** | Target physically counters | Cheat exposed, cheater penalized |

> Raw verbal deception, judged in real time.

---

### Human-like NPC AI

NPCs are driven by two axes: **Trust (logic)** × **Affinity (emotion)**

Four personality types create dramatically different behavior:

| Type | Behavior |
|:-----|:---------|
| **論理型 Logical** | Derives werewolf theory on its own — roller tactics, line analysis, confirmed-safe deduction |
| **感情型 Emotional** | Understands the logic, then ignores it to protect someone it likes |
| **ヘイト回避型 Passive** | Avoids conflict, follows consensus, hard to read |
| **破滅型 Chaotic** | Acts unpredictably, disrupts strategies, creates noise |

The Logical AI derives legitimate werewolf-game tactics autonomously from the Trust/Affinity matrix. The Emotional AI understands those tactics — then overrides them for irrational, human reasons. **This contradiction is what creates extraordinary drama.**

---

### AI-Generated World, Every Playthrough

Mistral AI generates the entire game world from scratch before each session:

| Component | Model | Output |
|:----------|:------|:-------|
| World Setting + Incident | `mistral-large` | Setting, factions, 1000+ character incident narrative |
| Characters + Backstories | `mistral-large` | Names, history, relationships with shared episodes |
| Cheat Judgment | `mistral-large` | Contextual 3-tier judgment of decoy vs. defense |
| NPC Speech | `mistral-small` | Personality + relationship-driven strategic dialogue |
| NPC Vote Decision | `mistral-small` | Autonomous voting from Trust scores + logic flags |
| Detective Report | `mistral-small` | Evidence-based investigation summary |
| Night Atmosphere | `mistral-small` | Immersive scene text generated each night |
| Conversational Hints | `mistral-small` | Suggested dialogue lines for new players |

---

### Two-Layer Class × Role System

Beyond the three-faction class war, each character carries a **secret role**:

- **探偵 Detective** — Investigates and generates evidence reports
- **ボディガード Bodyguard** — Protects a target from execution
- **共犯者 Accomplice** — Hidden ally with a shared secret mission

Plus a **True Win condition** — a personal hidden objective assigned by AI, e.g.:
> *"Protect Tanaka from execution at any cost."*
> *"Be executed — it's the only way to win."*

At the game-end reveal screen, every hidden condition fires simultaneously — delivering a powerful **伏線回収 (foreshadowing payoff)** moment.

---

### Player-Assist UX

Designed so anyone can enjoy complex social deduction:

| Feature | Description |
|:--------|:------------|
| **AI Dialogue Suggestions** | 3 context-aware suggested lines, one-click to speak |
| **Auto Investigation Memo** | AI extracts logical clues from NPC speech automatically |
| **Memory Fragment Panel** | Amnesia narrative: your true identity revealed in fragments as you talk |
| **God's-Eye Mode (👁)** | Even after execution, watch the full drama with all secrets visible |

---

## Game Flow

```
Setup → AI generates world + characters + relationships
  │
  ▼
[Night] ── Daifugo card battle
  │         NPCs react to strong cards in real time
  │         Hinmin's Decoy Bluff phase
  │
  ▼
[Day] ── Debate & Accusation
  │       NPCs apply personality-driven logic
  │       Player votes → Execution
  │       Instant win-condition checks
  │
  └──► Repeat until game ends
         │
         ▼
      [Result Screen] — Full reveal:
        All true classes, secret roles, hidden win conditions,
        relationship map, incident full-text, cheat log
```

---

## Architecture

```
Mistral_hack2/
├── backend/
│   ├── main.py          # FastAPI — 29 API endpoints (Hard + Lite modes)
│   ├── game_engine.py   # Daifugo logic (pure functions) + win condition checks
│   ├── ai_service.py    # Mistral AI integration — 20+ functions
│   ├── models.py        # Pydantic models — 30+ classes
│   └── requirements.txt
├── frontend/
│   ├── index.html       # Single-page game UI (Setup / Game / Result)
│   ├── style.css        # Dark gothic theme — black × gold
│   └── app.js           # Vanilla JS frontend
├── video/
│   ├── src/             # Remotion TypeScript video source (9 scenes)
│   └── out/video.mp4    # Rendered 120s presentation
├── slides.html          # Hackathon presentation slides
├── com.md               # Talk script (EN/JA)
├── SETTING.md           # Full game design document (v2.0 → v4.0)
└── AGENTS.md            # AI agent behavior specifications
```

---

## Tech Stack

| Layer | Technology |
|:------|:-----------|
| Backend | Python · FastAPI · Uvicorn |
| AI | Mistral AI (`mistral-large`, `mistral-small`) |
| Frontend | Vanilla JS · HTML · CSS |
| Video | Remotion (React + TypeScript) |
| Data | In-memory store (Pydantic models) |

---

## Daifugo Rules Implemented

| Rule | Detail |
|:-----|:-------|
| 54-card deck | Standard 52 + 2 Jokers |
| Card strength | 3 (weakest) → 2 (strongest); suits: ♠ > ♥ > ♦ > ♣ |
| Hand types | Single / Pair / Triple / Quad / Sequence (3+ same-suit consecutive) |
| 8-cut | Playing an 8 clears the table |
| Revolution | Quad play reverses all strength rankings |
| Joker | Wildcard and absolute strongest |
| Night-end | Table clears 3 times → advance to next day |

---

## Setup & Run

```bash
# 1. Clone
git clone https://github.com/irukashiro/Mistral_hack2.git
cd Mistral_hack2

# 2. Install backend dependencies
cd backend
pip install -r requirements.txt

# 3. Set your Mistral API key
cp ../.env.example .env
# Edit .env and set MISTRAL_API_KEY=your_key_here

# 4. Start the server
uvicorn main:app --reload

# 5. Open in browser
# http://localhost:8000
```

---

## API Reference (Selected)

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| POST | `/api/game/start-lite` | Start Lite mode — generate world, chars, deal cards |
| GET  | `/api/game/state` | Full game state (God's-Eye mode returns all secrets) |
| POST | `/api/game/lite/chat` | Day: player speaks, NPCs respond with personality + foreshadowing |
| POST | `/api/game/lite/npc-votes` | NPCs cast votes autonomously |
| POST | `/api/game/finalize-vote` | Execute hanging → instant win check → transition to night |
| POST | `/api/game/lite/cheat-decoy` | Hinmin submits Decoy + Real Action |
| POST | `/api/game/lite/cheat-react` | Target reacts to Decoy (15 char / 5 sec limit) |
| POST | `/api/game/play-cards` | Night: play cards → NPC chain reactions |
| GET  | `/api/game/result` | Full reveal: world, all chars, relationships, cheat log |

---

## Powered by Mistral AI

This project uses Mistral AI exclusively for all generative components:
- `mistral-large` for world-building and cheat judgment (high reasoning required)
- `mistral-small` for real-time NPC actions (low latency required)
- Structured JSON output (`response_format={"type": "json_object"}`) throughout

---

*Built for Mistral AI Hackathon 2026*
