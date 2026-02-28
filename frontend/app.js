// ============================================================
// Class Conflict: Millionaire — Frontend App
// ============================================================

const API = '';  // same origin

// ─── State ───────────────────────────────────────────────────
let gameId = null;
let playerId = 'player_human';
let gameState = null;
let selectedCards = new Set();  // indices in hand
let myVoteTarget = null;
let godEyeMode = localStorage.getItem('godEyeMode') === 'true';
let hintsVisible = false;
let ghostAdvanceTimer = null;
let introUsed = false;

// ─── localStorage persistence ────────────────────────────────
function saveGameToStorage() {
  if (!gameId || !gameState) return;
  try {
    const data = {
      gameId,
      playerId,
      // Trim chat_history to last 50 entries to stay under 5MB
      gameState: Object.assign({}, gameState, {
        chat_history: (gameState.chat_history || []).slice(-50),
      }),
    };
    localStorage.setItem('ccm_save', JSON.stringify(data));
  } catch (e) {
    console.warn('localStorage save failed:', e);
  }
}

function clearGameStorage() {
  localStorage.removeItem('ccm_save');
}

async function tryRestoreGame() {
  try {
    const raw = localStorage.getItem('ccm_save');
    if (!raw) return false;
    const data = JSON.parse(raw);
    if (!data.gameId) return false;
    // Verify game still exists on server
    const res = await fetch(`${API}/api/game/state?game_id=${data.gameId}&player_id=${data.playerId}`);
    if (!res.ok) {
      clearGameStorage();
      return false;
    }
    const serverState = await res.json();
    gameId = data.gameId;
    playerId = data.playerId;
    gameState = serverState;
    showScreen('game');
    renderAll();
    return true;
  } catch (e) {
    clearGameStorage();
    return false;
  }
}

// ─── DOM refs ────────────────────────────────────────────────
const $ = id => document.getElementById(id);

const screens = {
  setup: $('setup-screen'),
  game: $('game-screen'),
  gameover: $('gameover-screen'),
};

// ─── Screen management ───────────────────────────────────────
function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.add('hidden'));
  screens[name].classList.remove('hidden');
}

// ─── Card rendering ──────────────────────────────────────────
const SUIT_SYMBOL = { clubs: '♣', diamonds: '♦', hearts: '♥', spades: '♠', joker: '🃏' };

// ─── Character State Labels (0-9) ────────────────────────────
const STATE_LABELS = {
  0: { label: '不在', cls: 'state-0' },
  1: { label: '死亡', cls: 'state-1' },
  2: { label: 'Play', cls: 'state-2' },
  3: { label: '被疑', cls: 'state-3' },
  4: { label: '追放', cls: 'state-4' },
  5: { label: '上がり', cls: 'state-5' },
  6: { label: '会議', cls: 'state-6' },
  7: { label: '攻撃', cls: 'state-7' },
  8: { label: '擁護', cls: 'state-8' },
  9: { label: '勝利', cls: 'state-9' },
};

function stateBadgeHtml(stateCode) {
  const info = STATE_LABELS[stateCode];
  if (!info) return '';
  return `<span class="state-badge ${info.cls}">${info.label}</span>`;
}

// ─── Relationship value labels ────────────────────────────────
const REL_CELL_CLASS = {
  '-2': 'rel-cell-enemy',
  '-1': 'rel-cell-hostile',
  '0': 'rel-cell-neutral',
  '1': 'rel-cell-friendly',
  '2': 'rel-cell-trust',
  '3': 'rel-cell-secret',
};

function cardEl(card, index, selectable = false, small = false) {
  const el = document.createElement('div');
  el.className = `card ${card.suit}${small ? ' card-sm' : ''}`;
  if (card.is_joker) {
    el.textContent = '🃏';
    el.title = 'ジョーカー';
  } else {
    const numMap = { 1: 'A', 11: 'J', 12: 'Q', 13: 'K' };
    const num = numMap[card.number] || String(card.number);
    el.innerHTML = `<span class="card-num">${num}</span><span class="card-suit">${SUIT_SYMBOL[card.suit]}</span>`;
    el.title = `${SUIT_SYMBOL[card.suit]}${num}`;
  }

  if (selectable) {
    el.dataset.index = index;
    if (selectedCards.has(index)) el.classList.add('selected');
    el.addEventListener('click', () => toggleCard(index, el));
  }
  return el;
}

function toggleCard(index, el) {
  if (selectedCards.has(index)) {
    selectedCards.delete(index);
    el.classList.remove('selected');
  } else {
    selectedCards.add(index);
    el.classList.add('selected');
  }
  $('play-cards-btn').disabled = selectedCards.size === 0;
}

// ─── Setup Screen ─────────────────────────────────────────────
$('start-btn').addEventListener('click', startGame);
$('player-name').addEventListener('keydown', e => { if (e.key === 'Enter') startGame(); });

// Auto-restore from localStorage on page load
tryRestoreGame();

async function startGame() {
  const playerName = $('player-name').value.trim() || 'プレイヤー';
  const npcCount = parseInt($('npc-count').value, 10);

  $('loading-overlay').classList.remove('hidden');
  $('start-btn').disabled = true;
  $('setup-error').classList.add('hidden');

  try {
    const res = await fetch(`${API}/api/game/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ npc_count: npcCount, player_name: playerName }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'ゲーム開始に失敗しました');
    }

    const data = await res.json();
    gameId = data.game_id;
    playerId = data.player_id;
    gameState = data.state;

    showScreen('game');
    renderAll();
    saveGameToStorage();
  } catch (e) {
    $('setup-error').textContent = e.message;
    $('setup-error').classList.remove('hidden');
  } finally {
    $('loading-overlay').classList.add('hidden');
    $('start-btn').disabled = false;
  }
}

// ─── Main render ─────────────────────────────────────────────
function renderAll() {
  if (!gameState) return;

  if (gameState.game_over) {
    renderGameOver();
    return;
  }

  updateHeader();
  updateRevolutionBanner();

  // Ghost mode banner
  if (gameState.is_ghost_mode) {
    $('ghost-mode-banner').classList.remove('hidden');
  } else {
    $('ghost-mode-banner').classList.add('hidden');
  }

  if (gameState.phase === 'day') {
    // Hide night situation banner during day
    $('night-situation-banner').classList.add('hidden');
    showPhase('day');
    renderDayPhase();
  } else {
    showPhase('night');
    renderNightPhase();
    // Ghost mode: auto-advance NPC turns
    if (gameState.is_ghost_mode) {
      startGhostAutoAdvance();
    }
  }

  // Debug side panel (god eye mode)
  renderDebugSidePanel();
  // Keep legacy floating panels hidden
  $('debug-log-panel').classList.add('hidden');
  $('relationship-matrix-panel').classList.add('hidden');

  saveGameToStorage();
}

function showPhase(phase) {
  $('day-phase').classList.remove('active');
  $('night-phase').classList.remove('active');
  $('day-phase').classList.add('hidden');
  $('night-phase').classList.add('hidden');

  const panel = $(phase + '-phase');
  panel.classList.remove('hidden');
  panel.classList.add('active');
}

function updateHeader() {
  $('header-day').textContent = `Day ${gameState.day_number}`;

  const phaseEl = $('header-phase');
  phaseEl.textContent = gameState.phase === 'day' ? '昼' : '夜';
  phaseEl.className = 'header-phase ' + gameState.phase;

  const me = gameState.players.find(p => p.id === playerId);
  if (me) {
    const roleEl = $('header-role');
    const roleMap = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };
    roleEl.textContent = me.role ? roleMap[me.role] || me.role : '?';
    roleEl.className = 'header-role ' + (me.role || '');
    $('header-cards').textContent = `手札: ${me.hand_count}枚`;
  }
}

function updateRevolutionBanner() {
  const banner = $('revolution-banner');
  if (gameState.revolution_active) {
    banner.classList.remove('hidden');
  } else {
    banner.classList.add('hidden');
  }
}

// ─── Day Phase ───────────────────────────────────────────────
function renderDayPhase() {
  renderPlayersList();
  renderChatLog();
  renderVoteList();
  renderInvestigationNotes();
  renderAmnesiaClues();
  updateIntroButton();
}

function updateIntroButton() {
  const btn = $('intro-btn');
  if (gameState && gameState.day_number === 1 && !introUsed) {
    btn.classList.remove('hidden');
  } else {
    btn.classList.add('hidden');
  }
}

function renderPlayersList() {
  const container = $('players-list');
  container.innerHTML = '';
  const roleMap = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };
  gameState.players.forEach(p => {
    const div = document.createElement('div');
    div.className = `player-card${p.is_human ? ' is-human' : ''}${p.is_hanged ? ' hanged' : ''}${p.is_out ? ' out' : ''}`;
    const displayRole = p._debug_role || p.role;
    const roleLabel = displayRole ? roleMap[displayRole] : '?';
    const roleBadge = displayRole
      ? `<span class="player-role-badge ${displayRole}">${roleLabel}</span>`
      : '<span class="player-role-badge">?</span>';
    div.innerHTML = `
      <div class="player-name">${p.name}${p.is_human ? ' ★' : ''}${roleBadge}${stateBadgeHtml(p.state)}</div>
      <div class="player-cards-count">手札: ${p.hand_count}枚${p.is_hanged ? ' 【吊】' : ''}${p.is_out ? ' 【上がり】' : ''}</div>
    `;
    // God eye mode overlay
    if (godEyeMode && p._debug_role && !p.is_human) {
      const debugDiv = document.createElement('div');
      debugDiv.className = 'debug-overlay';
      const twDesc = p._debug_true_win ? escHtml(p._debug_true_win.description || '') : '';
      debugDiv.innerHTML = `
        <span class="debug-role">${roleMap[p._debug_role] || p._debug_role}</span>
        ${p._debug_backstory ? `<div class="debug-backstory">${escHtml(p._debug_backstory)}</div>` : ''}
        ${twDesc ? `<div class="debug-backstory">目標: ${twDesc}</div>` : ''}
      `;
      div.appendChild(debugDiv);
    }
    container.appendChild(div);
  });
}

// baton info keyed by speaker_id for the latest NPC responses
let lastBatonMap = {};  // npc_id -> {baton_target_id, baton_action}

function renderChatLog() {
  const log = $('chat-log');
  const wasAtBottom = log.scrollHeight - log.clientHeight <= log.scrollTop + 10;

  log.innerHTML = '';
  gameState.chat_history.forEach(msg => {
    const div = document.createElement('div');
    const cls = msg.speaker_id === 'system' ? 'system' : msg.speaker_id === playerId ? 'human' : 'npc';
    div.className = `chat-msg ${cls}`;
    if (msg.speaker_id !== 'system') {
      let inner = `<div class="chat-speaker">${msg.speaker_name}</div>${escHtml(msg.text)}`;
      // Append baton indicator if available for this NPC
      const baton = lastBatonMap[msg.speaker_id];
      if (baton && baton.baton_target_id) {
        const targetPlayer = gameState.players.find(p => p.id === baton.baton_target_id);
        const targetName = targetPlayer ? targetPlayer.name : baton.baton_target_id;
        const actionLabel = { question: '質問', rebuttal: '反論要求', agreement_request: '同意要求' }[baton.baton_action] || baton.baton_action;
        inner += `<span class="chat-baton">→ ${targetName} への${actionLabel}</span>`;
      }
      div.innerHTML = inner;
    } else {
      div.textContent = msg.text;
    }
    log.appendChild(div);
  });

  if (wasAtBottom) log.scrollTop = log.scrollHeight;
}

function renderVoteList() {
  const container = $('vote-list');
  container.innerHTML = '';
  const candidates = gameState.players.filter(p => !p.is_hanged && !p.is_out && p.id !== playerId);

  candidates.forEach(p => {
    const div = document.createElement('div');
    div.className = `vote-item${myVoteTarget === p.id ? ' selected-vote' : ''}`;
    div.innerHTML = `
      <span class="vote-item-name">${p.name}</span>
      <button class="vote-btn${myVoteTarget === p.id ? ' voted' : ''}" data-id="${p.id}">投票</button>
    `;
    div.querySelector('.vote-btn').addEventListener('click', () => castVote(p.id));
    container.appendChild(div);
  });
}

// Goto result button
$('goto-result-btn').addEventListener('click', async () => {
  if (!gameId) return;
  await renderGameOver();
});

// Chat
$('chat-send-btn').addEventListener('click', sendChat);
$('chat-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

// Intro button — Day 1 flavor action
$('intro-btn').addEventListener('click', () => {
  if (introUsed) return;
  introUsed = true;
  $('intro-btn').classList.add('hidden');
  $('chat-input').value = 'みんな、自己紹介してください';
  sendChat();
});

async function sendChat() {
  const msg = $('chat-input').value.trim();
  if (!msg) return;

  $('chat-input').value = '';
  $('chat-send-btn').disabled = true;

  try {
    const res = await fetch(`${API}/api/game/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId, message: msg }),
    });
    const data = await res.json();
    gameState.chat_history = data.chat_history;
    // Store baton info from latest NPC responses
    if (data.npc_responses) {
      data.npc_responses.forEach(r => {
        if (r.baton_target_id) {
          lastBatonMap[r.npc_id] = { baton_target_id: r.baton_target_id, baton_action: r.baton_action };
        } else {
          delete lastBatonMap[r.npc_id];
        }
      });
    }
    // Update investigation notes
    if (data.investigation_notes) {
      gameState.investigation_notes = data.investigation_notes;
      renderInvestigationNotes();
    }
    // Update amnesia clues — auto-expand panel on first new clue
    if (data.amnesia_clues) {
      const prevCount = (gameState.amnesia_clues || []).length;
      gameState.amnesia_clues = data.amnesia_clues;
      renderAmnesiaClues();
      if (data.amnesia_clues.length > prevCount) {
        $('amnesia-list').classList.remove('hidden');  // auto-open on new clue
      }
    }
    renderChatLog();
  } catch (e) {
    console.error(e);
  } finally {
    $('chat-send-btn').disabled = false;
  }
}

// Voting
async function castVote(targetId) {
  try {
    const res = await fetch(`${API}/api/game/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, voter_id: playerId, target_id: targetId }),
    });
    const data = await res.json();
    myVoteTarget = targetId;
    gameState.votes = data.votes;
    renderVoteList();
  } catch (e) {
    console.error(e);
  }
}

$('collect-votes-btn').addEventListener('click', collectNpcVotes);
async function collectNpcVotes() {
  $('collect-votes-btn').disabled = true;
  try {
    const res = await fetch(`${API}/api/game/npc-votes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId }),
    });
    const data = await res.json();
    gameState.votes = data.votes;

    // Show tally
    const tally = $('vote-tally');
    tally.classList.remove('hidden');
    tally.innerHTML = '<h4>現在の投票状況</h4>';
    Object.entries(data.vote_counts).sort((a, b) => b[1] - a[1]).forEach(([id, cnt]) => {
      const p = gameState.players.find(p => p.id === id);
      const row = document.createElement('div');
      row.className = 'tally-row';
      row.innerHTML = `<span>${p ? p.name : id}</span><span>${cnt}票</span>`;
      tally.appendChild(row);
    });

    // Show NPC vote reasoning in god eye mode
    if (godEyeMode && data.npc_vote_info) {
      const reasonDiv = document.createElement('div');
      reasonDiv.className = 'vote-reasoning-debug';
      reasonDiv.innerHTML = '<h4 class="debug-reason-title">AI判断理由</h4>';
      data.npc_vote_info.forEach(info => {
        if (info.reasoning) {
          const r = document.createElement('div');
          r.className = 'debug-vote-reason';
          r.innerHTML = `<span class="debug-voter">${escHtml(info.voter)}</span> → ${escHtml(info.target)}: <span class="debug-reason-text">${escHtml(info.reasoning)}</span>`;
          reasonDiv.appendChild(r);
        }
      });
      tally.appendChild(reasonDiv);
    }

    renderVoteList();
  } catch (e) {
    console.error(e);
  } finally {
    $('collect-votes-btn').disabled = false;
  }
}

$('finalize-vote-btn').addEventListener('click', finalizeVote);
async function finalizeVote() {
  if (!confirm('投票を確定して処刑を実行しますか？')) return;
  $('finalize-vote-btn').disabled = true;

  try {
    const res = await fetch(`${API}/api/game/finalize-vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId }),
    });
    const data = await res.json();
    gameState = data.state;

    if (data.hanged_player) {
      alert(`${data.hanged_player.name}が処刑されました。\n役職: ${roleLabel(data.hanged_player.role)}\n勝利条件: ${data.hanged_player.victory_condition}`);
    }

    // Show night situation banner
    if (data.night_situation) {
      const banner = $('night-situation-banner');
      $('night-situation-text').textContent = data.night_situation;
      banner.classList.remove('hidden');
    }

    // Log any NPC vs NPC cheat results
    if (data.npc_cheat_results && data.npc_cheat_results.length > 0) {
      data.npc_cheat_results.forEach(r => {
        nightLog.push({ type: 'cheat', text: `[イカサマ] ${r.cheater} → ${r.target}: ${r.story}` });
      });
    }

    myVoteTarget = null;
    selectedCards.clear();
    renderAll();

    // If instant victory fired (martyr/revenge etc.), stop here — result screen is already shown
    if (gameState.game_over) return;

    // Route to cheat phase
    if (data.pending_cheat) {
      showDefendPanel(data.pending_cheat.hint);
    } else if (data.human_can_cheat) {
      showCheatInitiatePanel();
    } else {
      await completeCheatPhase();
    }
  } catch (e) {
    console.error(e);
    alert('エラーが発生しました: ' + e.message);
  } finally {
    $('finalize-vote-btn').disabled = false;
  }
}

// ─── Night Phase ─────────────────────────────────────────────
let nightLog = [];

function renderNightPhase() {
  // Show night situation banner if available
  const situationBanner = $('night-situation-banner');
  if (gameState.night_situation) {
    $('night-situation-text').textContent = gameState.night_situation;
    situationBanner.classList.remove('hidden');
  } else {
    situationBanner.classList.add('hidden');
  }

  renderNightPlayersList();
  renderTableCards();
  renderPlayerHand();
  updateTurnIndicator();
  renderNightLog();
  renderHangedPanel();
  // Update clear counter
  const clearCount = $('clear-count');
  if (clearCount) clearCount.textContent = gameState.table_clear_count || 0;
}

function renderNightPlayersList() {
  const container = $('night-players-list');
  container.innerHTML = '';
  const others = gameState.players.filter(p => p.id !== playerId);

  others.forEach(p => {
    const div = document.createElement('div');
    div.className = `night-player-item${gameState.current_turn === p.id ? ' current-turn' : ''}${p.is_hanged ? ' hanged' : ''}${p.is_out ? ' out' : ''}`;
    div.innerHTML = `
      <div class="night-player-name">${p.name}${gameState.current_turn === p.id ? ' ▶' : ''}${stateBadgeHtml(p.state)}</div>
      <div class="night-player-count">手札: ${p.hand_count}枚${p.is_hanged ? ' 【吊】' : ''}${p.is_out ? ' 上がり' : ''}</div>
    `;
    container.appendChild(div);
  });
}

function renderTableCards() {
  const container = $('table-cards');
  container.innerHTML = '';
  if (!gameState.table || gameState.table.length === 0) {
    container.innerHTML = '<span class="empty-table">（場は空き）</span>';
  } else {
    gameState.table.forEach(card => {
      container.appendChild(cardEl(card, -1, false, false));
    });
  }
}

function renderPlayerHand() {
  const me = gameState.players.find(p => p.id === playerId);
  if (!me || !me.hand) return;

  const container = $('player-hand');
  container.innerHTML = '';
  $('hand-count-label').textContent = `(${me.hand.length}枚)`;

  me.hand.forEach((card, i) => {
    container.appendChild(cardEl(card, i, true, false));
  });

  // Re-apply selections
  selectedCards.forEach(idx => {
    const el = container.querySelector(`[data-index="${idx}"]`);
    if (el) el.classList.add('selected');
  });

  $('play-cards-btn').disabled = selectedCards.size === 0;
}

function updateTurnIndicator() {
  const me = gameState.players.find(p => p.id === playerId);
  const isMyTurn = gameState.current_turn === playerId;
  const current = gameState.players.find(p => p.id === gameState.current_turn);

  $('turn-indicator-text').textContent = isMyTurn
    ? 'あなたのターンです！'
    : `${current ? current.name : '?'} のターン`;

  $('play-cards-btn').disabled = !isMyTurn || selectedCards.size === 0;
  $('pass-btn').disabled = !isMyTurn;
}

function renderNightLog() {
  const container = $('night-log');
  container.innerHTML = '';
  nightLog.forEach(entry => {
    const div = document.createElement('div');
    div.className = `night-log-entry ${entry.type}`;
    div.textContent = entry.text;
    container.appendChild(div);
  });
  container.scrollTop = container.scrollHeight;
}

function addNightLogEntries(npcActions) {
  npcActions.forEach(action => {
    const cardsStr = action.cards.length > 0
      ? action.cards.map(c => c.display).join(' ')
      : '';
    // Show NPC speech before the action line
    if (action.speech) {
      nightLog.push({ type: 'npc-speech', text: `${action.name}:「${action.speech}」` });
    }
    if (action.action === 'pass') {
      nightLog.push({ type: 'pass', text: `${action.name}: パス` });
    } else {
      const msg = action.message || '';
      const special = msg.includes('革命') || msg.includes('8切り');
      nightLog.push({
        type: special ? 'special' : 'play',
        text: `${action.name}: ${cardsStr} を出した${msg.includes('革命') ? ' 🔥革命！' : msg.includes('8切り') ? ' ✂8切り！' : ''}`,
      });
    }
    // Debug: show reasoning in night log when god eye mode is on
    if (godEyeMode && action.reasoning) {
      nightLog.push({ type: 'debug-reasoning', text: `  [AI] ${action.name}: ${action.reasoning}` });
    }
  });
  renderNightLog();
}

function renderHangedPanel() {
  const container = $('hanged-info');
  const hanged = gameState.players.filter(p => p.is_hanged);
  if (hanged.length === 0) {
    container.innerHTML = '<p class="muted">まだ誰も吊られていません</p>';
    return;
  }
  container.innerHTML = '';
  hanged.forEach(p => {
    const div = document.createElement('div');
    div.className = 'hanged-player-card';
    div.innerHTML = `<h4>${p.name}</h4>`;
    if (p.hand) {
      const handDiv = document.createElement('div');
      handDiv.className = 'hanged-player-hand';
      p.hand.forEach(card => handDiv.appendChild(cardEl(card, -1, false, true)));
      div.appendChild(handDiv);
    }
    container.appendChild(div);
  });
}

// Night actions
$('play-cards-btn').addEventListener('click', playCards);
$('pass-btn').addEventListener('click', passTurn);

async function playCards() {
  const me = gameState.players.find(p => p.id === playerId);
  if (!me || !me.hand) return;

  const cards = [...selectedCards].map(i => me.hand[i]);
  if (cards.length === 0) return;

  $('play-cards-btn').disabled = true;
  $('pass-btn').disabled = true;

  try {
    const res = await fetch(`${API}/api/game/play-cards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId, cards }),
    });

    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'カードを出せませんでした');
      $('play-cards-btn').disabled = false;
      $('pass-btn').disabled = false;
      return;
    }

    selectedCards.clear();
    gameState = data.state;

    // Log player's play
    const cardsStr = cards.map(c => `${SUIT_SYMBOL[c.suit]}${c.number || ''}`).join(' ');
    nightLog.push({ type: 'play', text: `あなた: ${cardsStr} を出した` });

    if (data.npc_actions) addNightLogEntries(data.npc_actions);

    renderAll();  // handles game_over → renderGameOver internally
  } catch (e) {
    console.error(e);
    alert('エラー: ' + e.message);
    $('play-cards-btn').disabled = false;
    $('pass-btn').disabled = false;
  }
}

async function passTurn() {
  $('play-cards-btn').disabled = true;
  $('pass-btn').disabled = true;

  try {
    const res = await fetch(`${API}/api/game/pass`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId }),
    });

    const data = await res.json();
    selectedCards.clear();
    gameState = data.state;

    nightLog.push({ type: 'pass', text: 'あなた: パス' });
    if (data.npc_actions) addNightLogEntries(data.npc_actions);

    renderAll();  // handles game_over → renderGameOver internally
  } catch (e) {
    console.error(e);
  }
}

// ─── Cheat Phase ─────────────────────────────────────────────

function hideAllCheatPanels() {
  $('cheat-panel').classList.add('hidden');
  $('defend-panel').classList.add('hidden');
  $('cheat-result-panel').classList.add('hidden');
}

function showCheatInitiatePanel() {
  hideAllCheatPanels();

  // Populate target list with alive NPCs
  const select = $('cheat-target');
  select.innerHTML = '';
  const npcs = gameState.players.filter(p => !p.is_human && !p.is_hanged && !p.is_out);
  npcs.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name;
    select.appendChild(opt);
  });

  $('cheat-method').value = '';
  $('cheat-panel').classList.remove('hidden');
}

function showDefendPanel(hint) {
  hideAllCheatPanels();
  $('cheat-hint-text').textContent = hint;
  $('defense-method').value = '';
  $('defend-panel').classList.remove('hidden');
}

function showCheatResult(title, story, revealText) {
  hideAllCheatPanels();
  $('cheat-result-title').textContent = title;
  $('cheat-result-story').textContent = story;
  const revealEl = $('cheat-result-reveal');
  if (revealText) {
    revealEl.textContent = revealText;
    revealEl.classList.remove('hidden');
  } else {
    revealEl.classList.add('hidden');
  }
  $('cheat-result-panel').classList.remove('hidden');
}

// Cheat initiate submit
$('cheat-submit-btn').addEventListener('click', async () => {
  const targetId = $('cheat-target').value;
  const method = $('cheat-method').value.trim();
  if (!method) { alert('ズルの手口を入力してください'); return; }

  $('cheat-submit-btn').disabled = true;
  try {
    const res = await fetch(`${API}/api/game/cheat-initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, cheater_id: playerId, target_id: targetId, method }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'エラー'); return; }
    gameState = data.state;
    const title = data.success ? '✔ イカサマ成功！' : '✘ イカサマ失敗…';
    showCheatResult(title, data.story, null);
  } catch (e) {
    console.error(e);
    alert('エラー: ' + e.message);
  } finally {
    $('cheat-submit-btn').disabled = false;
  }
});

// Cheat skip
$('cheat-skip-btn').addEventListener('click', async () => {
  try {
    await fetch(`${API}/api/game/cheat-skip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId }),
    });
  } catch (e) {
    console.error(e);
  }
  hideAllCheatPanels();
  await completeCheatPhase();
});

// Defense submit
$('defense-submit-btn').addEventListener('click', async () => {
  const defense = $('defense-method').value.trim();
  if (!defense) { alert('対策を入力してください'); return; }

  const defenseCategory = $('defense-category').value;

  $('defense-submit-btn').disabled = true;
  try {
    const res = await fetch(`${API}/api/game/cheat-defend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, defender_id: playerId, defense_method: defense, defense_category: defenseCategory }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'エラー'); return; }
    gameState = data.state;
    const title = data.success ? '⚠ イカサマを受けた！' : '✔ 防御成功！';
    const reveal = data.cheater_revealed ? `正体を見破った！ 犯人: ${data.cheater_name}` : null;
    showCheatResult(title, data.story, reveal);
  } catch (e) {
    console.error(e);
    alert('エラー: ' + e.message);
  } finally {
    $('defense-submit-btn').disabled = false;
  }
});

// Cheat result OK — proceed to card play
$('cheat-result-ok').addEventListener('click', async () => {
  hideAllCheatPanels();

  // After a defend result, check if human can still cheat
  const me = gameState.players.find(p => p.id === playerId);
  const humanCanCheat = me && me.role === 'hinmin' && !me.cheat_used_this_night && !me.is_hanged;
  if (humanCanCheat) {
    showCheatInitiatePanel();
  } else {
    await completeCheatPhase();
  }
});

async function completeCheatPhase() {
  try {
    const res = await fetch(`${API}/api/game/cheat-phase-complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'cheat-phase-complete failed');
    gameState = data.state;

    if (data.npc_actions && data.npc_actions.length > 0) {
      addNightLogEntries(data.npc_actions);
    }

    renderAll();  // handles game_over internally
  } catch (e) {
    console.error(e);
    if (gameState) renderAll();
  }
}

// ─── Game Over (Rich Result) ──────────────────────────────────
async function renderGameOver() {
  console.log('[renderGameOver] gameId:', gameId, 'gameState:', gameState);
  showScreen('gameover');

  const isWinner = (gameState.winner_ids || []).includes(playerId);
  const titleEl = $('gameover-title');
  titleEl.textContent = isWinner ? '🏆 勝利！' : '敗北...';
  titleEl.style.color = isWinner ? '#c8a84b' : '#c0392b';

  $('result-characters').innerHTML = '<span class="muted">読み込み中...</span>';
  $('result-relationships').innerHTML = '';
  $('result-cheat-log').innerHTML = '';
  $('result-world-header').innerHTML = '<span class="muted">読み込み中...</span>';
  $('result-full-incident').innerHTML = '';
  $('result-player-secret').innerHTML = '';

  try {
    const url = `${API}/api/game/result?game_id=${gameId}`;
    console.log('[renderGameOver] Fetching:', url);
    const res = await fetch(url);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    console.log('[renderGameOver] Got data:', data);
    renderResultWorldSetting(data);
    renderResultPlayerSecret(data);
    renderResultVictoryReason(data);
    renderResultCharacters(data);
    renderResultRelationships(data);
    renderResultCheatLog(data);
  } catch (e) {
    console.error('[renderGameOver] Error:', e);
    $('result-characters').innerHTML = `<span class="muted">データ取得エラー: ${e.message}</span>`;
    $('result-world-header').innerHTML = `<span class="muted">エラー: ${e.message}</span>`;
  }
}

function renderResultWorldSetting(data) {
  console.log('[renderResultWorldSetting] data.world_setting:', data.world_setting);
  const ws = data.world_setting || {};
  const headerEl = $('result-world-header');
  const incidentEl = $('result-full-incident');

  if (!ws.setting_name && !ws.location) {
    headerEl.innerHTML = '<span class="muted">世界設定なし</span>';
    console.warn('[renderResultWorldSetting] No world setting');
    return;
  }

  headerEl.innerHTML = `
    <div class="result-ws-title">${escHtml(ws.setting_name || '')}</div>
    <div class="result-ws-location">📍 ${escHtml(ws.location || '')}</div>
    ${ws.context ? `<div class="result-ws-context">${escHtml(ws.context)}</div>` : ''}
    ${(ws.key_events || []).length > 0 ? `
      <div class="result-ws-events">
        <span class="result-ws-label">共通の過去:</span>
        <ul>${(ws.key_events || []).map(e => `<li>${escHtml(e)}</li>`).join('')}</ul>
      </div>` : ''}
    ${(ws.factions || []).length > 0 ? `
      <div class="result-ws-factions">
        <span class="result-ws-label">派閥:</span>
        ${(ws.factions || []).map(f => `<span class="result-ws-faction">${escHtml(f.name)}: ${escHtml(f.description)}</span>`).join('')}
      </div>` : ''}
  `;

  if (ws.full_incident) {
    incidentEl.innerHTML = `
      <div class="result-incident-label">— 事件の全貌 —</div>
      <div class="result-incident-body">${escHtml(ws.full_incident)}</div>
    `;
  }
}

function renderResultPlayerSecret(data) {
  const ws = data.world_setting || {};
  const secret = ws.player_secret_backstory;
  const clues = data.amnesia_clues || [];
  const container = $('result-player-secret');

  let html = '';
  if (secret) {
    html += `<div class="result-secret-body">${escHtml(secret)}</div>`;
  } else {
    html += '<span class="muted">記録なし</span>';
  }
  if (clues.length > 0) {
    html += `<div class="result-secret-clues-title">あなたが思い出した断片 (${clues.length}件):</div>`;
    html += clues.map(c => `<div class="result-secret-clue">🌀 ${escHtml(c)}</div>`).join('');
  }
  container.innerHTML = html;
}

function renderResultVictoryReason(data) {
  const container = $('result-victory-reason');
  const reason = data.victory_reason || (gameState && gameState.victory_reason) || '';
  if (!reason) {
    container.innerHTML = '<span class="muted">勝利理由の記録なし</span>';
    return;
  }
  container.innerHTML = reason.split('\n').map(line => `<div class="result-reason-line">${escHtml(line)}</div>`).join('');
}

function renderResultCharacters(data) {
  console.log('[renderResultCharacters] data.characters:', data.characters);
  const container = $('result-characters');
  container.innerHTML = '';
  const roleMap = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };

  if (!data.characters || data.characters.length === 0) {
    container.innerHTML = '<span class="muted">キャラクターデータなし</span>';
    console.warn('[renderResultCharacters] No characters found');
    return;
  }

  (data.characters || []).forEach(char => {
    const card = document.createElement('div');
    card.className = `result-char-card${char.is_human ? ' is-human' : ''}`;
    const rank = (data.out_order || []).indexOf(char.id);
    const rankStr = rank >= 0 ? `上がり順位: ${rank + 1}位` : (char.is_hanged ? '【処刑】' : '');
    const isWinner = (data.winner_ids || []).includes(char.id);
    card.innerHTML = `
      <div class="result-char-name">${escHtml(char.name)}${char.is_human ? ' ★' : ''}${isWinner ? ' 🏆' : ''}</div>
      <div class="result-char-role ${char.role}">${roleMap[char.role] || char.role}</div>
      <div class="result-char-rank">${escHtml(rankStr)}</div>
      <div class="result-char-style">${escHtml(char.argument_style || '')}</div>
      <div class="result-char-backstory">${escHtml(char.backstory || '')}</div>
      ${char.true_win ? `<div class="result-char-truewin">真の目標: ${escHtml(char.true_win.description || '')}</div>` : ''}
    `;
    container.appendChild(card);
  });
}

function renderResultRelationships(data) {
  console.log('[renderResultRelationships] data.relationship_web:', data.relationship_web);
  const container = $('result-relationships');
  container.innerHTML = '';
  const charMap = {};
  (data.characters || []).forEach(c => { charMap[c.id] = c.name; });

  const web = data.relationship_web || [];
  if (web.length === 0) {
    container.innerHTML = '<span class="muted">関係なし</span>';
    console.warn('[renderResultRelationships] No relationships found');
    return;
  }
  web.forEach(rel => {
    const div = document.createElement('div');
    div.className = 'result-rel-item';
    const fromName = charMap[rel.from_id] || rel.from_id;
    const toName = charMap[rel.to_id] || rel.to_id;
    div.innerHTML = `<span class="result-rel-from">${escHtml(fromName)}</span> → <span class="result-rel-to">${escHtml(toName)}</span>: ${escHtml(rel.description)}`;
    container.appendChild(div);
  });
}

function renderResultCheatLog(data) {
  console.log('[renderResultCheatLog] data.cheat_log:', data.cheat_log);
  const container = $('result-cheat-log');
  container.innerHTML = '';
  const charMap = {};
  (data.characters || []).forEach(c => { charMap[c.id] = c.name; });

  const log = data.cheat_log || [];
  if (log.length === 0) {
    container.innerHTML = '<span class="muted">イカサマなし</span>';
    console.warn('[renderResultCheatLog] No cheat log found');
    return;
  }
  log.forEach(entry => {
    const div = document.createElement('div');
    div.className = `result-cheat-item ${entry.judgment}`;
    const cheaterName = charMap[entry.cheater_id] || entry.cheater_id;
    const targetName = charMap[entry.target_id] || entry.target_id;
    const judgmentLabel = { big_success: '大成功', draw: '引き分け', big_fail: '大失敗' }[entry.judgment] || entry.judgment;
    div.innerHTML = `<span class="result-cheat-judgment">[${judgmentLabel}]</span> ${escHtml(cheaterName)} → ${escHtml(targetName)}: ${escHtml(entry.story)}`;
    container.appendChild(div);
  });
}

$('restart-btn').addEventListener('click', () => {
  clearGameStorage();
  gameId = null;
  playerId = 'player_human';
  gameState = null;
  selectedCards.clear();
  myVoteTarget = null;
  nightLog = [];
  lastBatonMap = {};
  introUsed = false;
  godEyeMode = false;
  localStorage.removeItem('godEyeMode');
  hintsVisible = false;
  if (ghostAdvanceTimer) { clearTimeout(ghostAdvanceTimer); ghostAdvanceTimer = null; }
  $('night-situation-banner').classList.add('hidden');
  $('ghost-mode-banner').classList.add('hidden');
  $('hints-panel').classList.add('hidden');
  $('amnesia-list').classList.add('hidden');
  $('debug-toggle-btn').classList.remove('active');
  $('debug-log-panel').classList.add('hidden');
  showScreen('setup');
});

// ─── God Eye Mode ─────────────────────────────────────────────
$('debug-toggle-btn').classList.toggle('active', godEyeMode);

$('debug-toggle-btn').addEventListener('click', () => {
  godEyeMode = !godEyeMode;
  localStorage.setItem('godEyeMode', godEyeMode);
  $('debug-toggle-btn').classList.toggle('active', godEyeMode);
  if (godEyeMode && gameId) {
    fetchAndApplyDebugState();
  } else {
    renderAll();
  }
});

async function fetchAndApplyDebugState() {
  if (!gameId) return;
  try {
    const res = await fetch(`${API}/api/game/debug-state?game_id=${gameId}`);
    if (!res.ok) {
      console.warn('debug-state endpoint error:', res.status);
      renderDebugSidePanel();
      return;
    }
    const data = await res.json();
    if (!data || !Array.isArray(data.players)) {
      console.warn('debug-state: unexpected response', data);
      renderDebugSidePanel();
      return;
    }
    // Apply debug fields to local gameState players
    data.players.forEach(debugP => {
      const p = gameState.players.find(gp => gp.id === debugP.id);
      if (p) {
        p._debug_role = debugP._debug_role;
        p._debug_backstory = debugP._debug_backstory;
        p._debug_true_win = debugP._debug_true_win;
        if (debugP.hand) p.hand = debugP.hand;
      }
    });
    if (data.debug_log) gameState.debug_log = data.debug_log;
    if (data.relationship_matrix) gameState.relationship_matrix = data.relationship_matrix;
    renderAll();
  } catch (e) {
    console.error('fetchAndApplyDebugState:', e);
    renderDebugSidePanel();
  }
}

// ─── Debug Log Panel ──────────────────────────────────────────
$('debug-log-close').addEventListener('click', () => {
  $('debug-log-panel').classList.add('hidden');
});

function renderDebugLog() {
  const panel = $('debug-log-panel');
  const entries = $('debug-log-entries');
  if (!godEyeMode) {
    panel.classList.add('hidden');
    return;
  }

  const log = (gameState && gameState.debug_log) || [];
  if (log.length === 0) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  entries.innerHTML = '';

  const typeLabels = { vote: '投票', play: 'カード', chat: '発言', cheat: 'イカサマ', victory: '勝利', api_call: 'API' };
  const typeClasses = { vote: 'debug-vote', play: 'debug-play', chat: 'debug-chat', cheat: 'debug-cheat', victory: 'debug-victory', api_call: 'debug-api' };

  log.forEach(entry => {
    const div = document.createElement('div');
    div.className = `debug-log-entry ${typeClasses[entry.type] || ''}`;
    const label = typeLabels[entry.type] || entry.type;
    let reasonText = '';
    if (typeof entry.reasoning === 'object' && entry.reasoning !== null) {
      reasonText = Object.entries(entry.reasoning).map(([k, v]) => `${k}: ${v}`).join(' / ');
    } else {
      reasonText = String(entry.reasoning || '');
    }
    // Show latency for API calls
    const latencyBadge = (entry.type === 'api_call' && entry.detail && entry.detail.latency_ms)
      ? `<span class="debug-entry-latency">${entry.detail.latency_ms}ms</span>` : '';
    div.innerHTML = `
      <span class="debug-entry-badge">${label}</span>
      <span class="debug-entry-turn">T${entry.turn || '?'}</span>
      <span class="debug-entry-actor">${escHtml(entry.actor_name || '')}</span>
      ${latencyBadge}
      <span class="debug-entry-reasoning">${escHtml(reasonText)}</span>
    `;
    entries.appendChild(div);
  });
  entries.scrollTop = entries.scrollHeight;
}

// ─── Relationship Matrix Panel ────────────────────────────────
$('rel-matrix-close').addEventListener('click', () => {
  $('relationship-matrix-panel').classList.add('hidden');
});

function renderRelationshipMatrix() {
  const panel = $('relationship-matrix-panel');
  const body = $('rel-matrix-body');
  if (!godEyeMode) {
    panel.classList.add('hidden');
    return;
  }

  const matrix = gameState && gameState.relationship_matrix;
  if (!matrix || Object.keys(matrix).length === 0) {
    panel.classList.add('hidden');
    return;
  }

  const players = gameState.players;
  const ids = players.map(p => p.id);
  const nameMap = {};
  players.forEach(p => { nameMap[p.id] = p.name; });

  let html = '<table class="relationship-matrix"><tr><th></th>';
  ids.forEach(id => { html += `<th>${escHtml(nameMap[id] || id)}</th>`; });
  html += '</tr>';

  ids.forEach(rowId => {
    html += `<tr><td class="rel-row-header">${escHtml(nameMap[rowId] || rowId)}</td>`;
    ids.forEach(colId => {
      if (rowId === colId) {
        html += '<td class="rel-cell-self">-</td>';
      } else {
        const val = (matrix[rowId] && matrix[rowId][colId] !== undefined) ? matrix[rowId][colId] : 0;
        const cls = REL_CELL_CLASS[String(val)] || 'rel-cell-neutral';
        html += `<td class="${cls}">${val}</td>`;
      }
    });
    html += '</tr>';
  });
  html += '</table>';

  body.innerHTML = html;
  panel.classList.remove('hidden');
}

// ─── Debug Side Panel ─────────────────────────────────────────
function renderDebugSidePanel() {
  const panel = $('debug-side-panel');
  if (!godEyeMode || !gameState) {
    panel.classList.add('hidden');
    return;
  }
  panel.classList.remove('hidden');

  // 1. Player true info
  const playersInfo = $('debug-players-info');
  playersInfo.innerHTML = '';
  gameState.players.forEach(p => {
    const div = document.createElement('div');
    div.className = 'debug-player-card';
    const roleLabel = p._debug_role || p.role || '?';
    const trueWin = p._debug_true_win
      ? `${p._debug_true_win.type}: ${p._debug_true_win.description || ''}` : '';
    const raw = p._debug_backstory || p.backstory || '';
    const backstory = raw.slice(0, 90) + (raw.length > 90 ? '…' : '');
    div.innerHTML =
      `<div class="debug-player-name">${escHtml(p.name)}${p.is_human ? ' 👤' : ''}</div>` +
      `<div class="debug-player-role">${escHtml(roleLabel)}</div>` +
      (trueWin ? `<div class="debug-player-win">🎯 ${escHtml(trueWin)}</div>` : '') +
      `<div class="debug-player-back">${escHtml(backstory)}</div>`;
    playersInfo.appendChild(div);
  });

  // 2. Relationship matrix (compact inline)
  const relDiv = $('debug-rel-matrix-inline');
  const matrix = gameState.relationship_matrix;
  if (matrix && Object.keys(matrix).length > 0) {
    const ids = gameState.players.map(p => p.id);
    const nameMap = {};
    gameState.players.forEach(p => { nameMap[p.id] = p.name; });
    let html = '<table class="debug-rel-table"><tr><th></th>';
    ids.forEach(id => {
      html += `<th title="${escHtml(nameMap[id] || id)}">${escHtml((nameMap[id] || id).slice(0, 3))}</th>`;
    });
    html += '</tr>';
    ids.forEach(rowId => {
      html += `<tr><td class="debug-rel-row">${escHtml((nameMap[rowId] || rowId).slice(0, 3))}</td>`;
      ids.forEach(colId => {
        if (rowId === colId) {
          html += '<td class="rel-self">-</td>';
        } else {
          const val = (matrix[rowId] && matrix[rowId][colId] !== undefined) ? matrix[rowId][colId] : 0;
          const cls = val > 0 ? 'rel-pos' : val < 0 ? 'rel-neg' : '';
          html += `<td class="${cls}">${val}</td>`;
        }
      });
      html += '</tr>';
    });
    html += '</table>';
    relDiv.innerHTML = html;
  } else {
    relDiv.innerHTML = '<span class="debug-muted">データなし</span>';
  }

  // 3. AI log (latest 15, newest first)
  const logDiv = $('debug-ai-log-inline');
  const log = (gameState.debug_log || []).slice(-15).reverse();
  const typeLabels = { vote: '投票', play: '🃏', chat: '💬', cheat: '⚠', victory: '🏆', api_call: 'API' };
  if (log.length === 0) {
    logDiv.innerHTML = '<span class="debug-muted">ログなし</span>';
  } else {
    logDiv.innerHTML = log.map(entry => {
      const label = typeLabels[entry.type] || entry.type;
      let reasoning = '';
      if (typeof entry.reasoning === 'object' && entry.reasoning) {
        reasoning = Object.entries(entry.reasoning).map(([k, v]) => `${k}:${v}`).join(' ');
      } else {
        reasoning = String(entry.reasoning || '');
      }
      return `<div class="debug-log-mini">` +
        `<span class="dlm-badge">${escHtml(label)}</span>` +
        `<span class="dlm-actor">${escHtml(entry.actor_name || '')}</span>` +
        `<span class="dlm-reason">${escHtml(reasoning.slice(0, 80))}</span>` +
        `</div>`;
    }).join('');
  }
}

// ─── Hints System ─────────────────────────────────────────────
$('hints-toggle-btn').addEventListener('click', () => {
  hintsVisible = !hintsVisible;
  const panel = $('hints-panel');
  if (hintsVisible) {
    panel.classList.remove('hidden');
    fetchHints();
  } else {
    panel.classList.add('hidden');
  }
});

$('hints-refresh-btn').addEventListener('click', fetchHints);

async function fetchHints() {
  if (!gameId) return;
  $('hints-list').innerHTML = '<span class="muted">生成中...</span>';
  $('templates-list').innerHTML = '';
  try {
    const res = await fetch(`${API}/api/game/hints?game_id=${gameId}&player_id=${playerId}`);
    if (!res.ok) { $('hints-list').innerHTML = '<span class="muted">昼フェーズのみ使えます</span>'; return; }
    const data = await res.json();

    const hintsEl = $('hints-list');
    hintsEl.innerHTML = '';
    (data.hints || []).forEach(h => {
      const div = document.createElement('div');
      div.className = 'hint-item';
      div.textContent = h.text;
      hintsEl.appendChild(div);
    });

    const templatesEl = $('templates-list');
    templatesEl.innerHTML = '';
    (data.templates || []).forEach(t => {
      const btn = document.createElement('button');
      btn.className = 'template-btn';
      btn.textContent = t.label;
      btn.title = t.message;
      btn.addEventListener('click', () => {
        $('chat-input').value = t.message;
        $('chat-input').focus();
      });
      templatesEl.appendChild(btn);
    });
  } catch (e) {
    console.error(e);
    $('hints-list').innerHTML = '<span class="muted">ヒント生成エラー</span>';
  }
}

// ─── Investigation Notes ──────────────────────────────────────
$('notes-toggle-btn').addEventListener('click', () => {
  $('notes-list').classList.toggle('hidden');
});

function renderInvestigationNotes() {
  const notes = gameState.investigation_notes || [];
  $('notes-count').textContent = notes.length;
  const list = $('notes-list');
  list.innerHTML = '';
  notes.forEach(note => {
    const div = document.createElement('div');
    div.className = 'note-item';
    div.textContent = note;
    list.appendChild(div);
  });
}

// ─── Amnesia Clues (記憶の断片) ───────────────────────────────
$('amnesia-toggle-btn').addEventListener('click', () => {
  $('amnesia-list').classList.toggle('hidden');
});

function renderAmnesiaClues() {
  const clues = gameState.amnesia_clues || [];
  $('amnesia-count').textContent = clues.length;
  const list = $('amnesia-list');
  list.innerHTML = '';
  if (clues.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'muted';
    empty.style.padding = '0.3rem 0.5rem';
    empty.textContent = '— まだ何も思い出せない —';
    list.appendChild(empty);
    return;
  }
  clues.forEach((clue, i) => {
    const div = document.createElement('div');
    div.className = 'amnesia-clue';
    div.innerHTML = `<span class="amnesia-num">${i + 1}</span>${escHtml(clue)}`;
    list.appendChild(div);
  });
}

// ─── Ghost Mode ───────────────────────────────────────────────
function startGhostAutoAdvance() {
  if (ghostAdvanceTimer) return;  // Already scheduled
  ghostAdvanceTimer = setTimeout(async () => {
    ghostAdvanceTimer = null;
    if (!gameState || !gameState.is_ghost_mode || gameState.phase !== 'night') return;
    try {
      const res = await fetch(`${API}/api/game/ghost-advance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ game_id: gameId }),
      });
      const data = await res.json();
      gameState = data.state;
      if (data.npc_actions && data.npc_actions.length > 0) {
        addNightLogEntries(data.npc_actions);
      }
      renderAll();
    } catch (e) {
      console.error(e);
    }
  }, 2000);
}

// ─── Helpers ─────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function roleLabel(role) {
  const map = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };
  return map[role] || role;
}

// ─── Init ────────────────────────────────────────────────────
showScreen('setup');
