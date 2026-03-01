// ============================================================
// Class Conflict: Millionaire — Frontend App
// ============================================================

const API = '';  // same origin

// ─── State ───────────────────────────────────────────────────
let gameId = null;
let playerId = 'player_human';
let gameState = null;
let gameMode = 'lite';  // 'lite' or 'hard'
let selectedCards = new Set();  // indices in hand
let myVoteTarget = null;
let godEyeMode = localStorage.getItem('godEyeMode') === 'true';
let hintsVisible = false;
let ghostAdvanceTimer = null;
let introUsed = false;
let liteReactTimer = null;  // countdown timer for lite cheat react
// v4: Detective
let myGameRole = null;    // "detective", "none", etc.
let detectiveUsed = false; // whether ability has been used
// Auto mode
let autoMode = false;
let autoRunning = false;  // prevent concurrent auto runs

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
    gameMode = serverState.game_mode || 'hard';
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

// Mode selection
function selectMode(mode) {
  gameMode = mode;
  $('game-mode').value = mode;
  $('mode-lite-card').classList.toggle('active', mode === 'lite');
  $('mode-hard-card').classList.toggle('active', mode === 'hard');
  const npcRow = $('npc-count-row');
  if (mode === 'hard') {
    npcRow.classList.remove('hidden');
  } else {
    npcRow.classList.add('hidden');
  }
}

// Auto-restore from localStorage on page load
tryRestoreGame();

async function startGame() {
  const playerName = $('player-name').value.trim() || 'プレイヤー';
  const npcCount = $('npc-count') ? parseInt($('npc-count').value, 10) : 4;
  const mode = $('game-mode').value || 'lite';
  gameMode = mode;

  $('loading-overlay').classList.remove('hidden');
  $('start-btn').disabled = true;
  $('setup-error').classList.add('hidden');

  const endpoint = mode === 'lite' ? '/api/game/start-lite' : '/api/game/start';

  try {
    const res = await fetch(`${API}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ npc_count: npcCount, player_name: playerName, game_mode: mode }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'ゲーム開始に失敗しました');
    }

    const data = await res.json();
    gameId = data.game_id;
    playerId = data.player_id;
    gameState = data.state;

    // Reset all per-game state
    nightLog = [];
    selectedCards.clear();
    myVoteTarget = null;
    lastBatonMap = {};
    introUsed = false;
    autoMode = false;
    autoRunning = false;
    $('auto-mode-btn').classList.remove('active');
    $('auto-mode-btn').textContent = '⚡ AUTO';

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
    if (autoMode) scheduleAutoDay();
  } else {
    showPhase('night');
    renderNightPhase();
    // Ghost mode: auto-advance NPC turns
    if (gameState.is_ghost_mode) {
      startGhostAutoAdvance();
    }
    if (autoMode) scheduleAutoNight();
  }

  // Debug side panel (god eye mode)
  renderDebugSidePanel();
  // Smart Device (player status) panel
  renderSmartDevice();
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

    // v4: game_role badge
    if (me.game_role && me.game_role !== 'none') {
      myGameRole = me.game_role;
      const gameRoleBadge = $('header-game-role');
      const gameRoleLabels = { detective: '🔍 探偵', accomplice: '🤝 共犯者' };
      gameRoleBadge.textContent = gameRoleLabels[me.game_role] || me.game_role;
      gameRoleBadge.style.display = 'inline';
    }
  }

  // Sync detective_used_ability from state
  if (gameState.detective_used_ability !== undefined) {
    detectiveUsed = gameState.detective_used_ability;
  }
}

// ─── Smart Device (player status / missions) ─────────────────
function toggleSmartDevice(open) {
  const panel = $('smart-device-panel');
  if (!panel) return;
  if (open === undefined) open = panel.classList.contains('hidden');
  panel.classList.toggle('hidden', !open);
}

document.addEventListener('click', (e) => {
  if (e.target && e.target.id === 'device-toggle-btn') {
    toggleSmartDevice(true);
  }
  if (e.target && e.target.id === 'smart-device-close') {
    toggleSmartDevice(false);
  }
});

function renderSmartDevice() {
  const panel = $('smart-device-panel');
  if (!panel || !gameState) return;
  // only show to human player
  const me = (gameState.players || []).find(p => p.id === playerId);
  if (!me) { panel.classList.add('hidden'); return; }
  // Do not force-open the panel here; leave visibility to the toggle button

  // PROFILE
  const profileEl = $('sd-profile-content');
  const roleMap = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };
  const profileBack = me.backstory || me._debug_backstory || '（設定なし）';
  const profileHtml = `
    <div class="sd-row"><strong>現在の階級:</strong> ${escHtml(roleMap[me.role] || me.role || '不明')}</div>
    <div class="sd-row"><strong>現在の役職:</strong> ${escHtml(me.game_role || me.game_role || '—')}</div>
    <div class="sd-row"><strong>プロフィール:</strong> ${escHtml(profileBack)}</div>
  `;
  profileEl.innerHTML = profileHtml;

  // MAIN MISSION (faction goal)
  const mainEl = $('sd-main-content');
  let mainMission = '';
  if (me.faction_goal) mainMission = me.faction_goal;
  else if (gameState.faction_goals && gameState.faction_goals[me.role]) mainMission = gameState.faction_goals[me.role];
  else {
    // fallback per spec
    if (me.role === 'heimin') mainMission = '会議で「貧民」と「富豪」の両方を排除する';
    else if (me.role === 'fugo') mainMission = '夜の大富豪で誰よりも早く手札を0にする（上がる）';
    else if (me.role === 'hinmin') mainMission = '大富豪パートで早く上がる、または革命を成立させる';
    else mainMission = '陣営目標は未設定';
  }
  mainEl.innerHTML = `<div class="sd-row">${escHtml(mainMission)}</div>`;

  // SECRET MISSION (true win)
  const secretEl = $('sd-secret-content');
  let secret = '';
  if (me.true_win) secret = me.true_win.description || JSON.stringify(me.true_win);
  else if (me._debug_true_win) secret = me._debug_true_win.description || JSON.stringify(me._debug_true_win);
  else if (me.secret_mission) secret = me.secret_mission;
  else secret = '（個人目標なし）';
  secretEl.innerHTML = `<div class="sd-row">${escHtml(secret)}</div>`;

  // Hints — use logic_state suggestions or global hints
  const hintsContainer = $('sd-hints');
  const hints = (gameState.logic_state && gameState.logic_state.suggestions) || gameState.hints || [];
  if (!hints || hints.length === 0) {
    hintsContainer.innerHTML = '<div class="sd-hint">（現在利用可能なヒントはありません）</div>';
  } else {
    hintsContainer.innerHTML = hints.map(h => `<div class="sd-hint">・ ${escHtml(h)}</div>`).join('');
  }

  // Tab switching
  document.querySelectorAll('.sd-tab').forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll('.sd-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const target = tab.dataset.tab;
      document.querySelectorAll('.sd-panel').forEach(p => p.classList.remove('active'));
      $(`sd-${target}`).classList.add('active');
    };
  });
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

  // Lite mode: hide hard-mode-only panels
  const isLite = gameState && gameState.game_mode === 'lite';
  const notesPanel = $('notes-panel');
  const amnesiaPanel = $('amnesia-panel');
  const hintsToggle = $('hints-toggle-btn');
  if (notesPanel) notesPanel.style.display = isLite ? 'none' : '';
  if (amnesiaPanel) amnesiaPanel.style.display = isLite ? 'none' : '';
  if (hintsToggle) hintsToggle.style.display = isLite ? 'none' : '';

  if (!isLite) {
    renderInvestigationNotes();
    renderAmnesiaClues();
  }

  // CO buttons: show only in Lite mode during day
  const coBtns = $('co-buttons');
  if (coBtns) coBtns.classList.toggle('hidden', !isLite);

  updateIntroButton();
  updateChatLimit();
  renderBoardSummary();
}

function renderBoardSummary() {
  const ls = gameState && gameState.logic_state;
  const panel = $('board-summary-panel');
  if (!panel) return;
  if (!ls || !gameState || gameState.game_mode !== 'lite') {
    panel.classList.add('hidden');
    return;
  }
  const hasContent = (ls.board_summaries && ls.board_summaries.length > 0)
    || (ls.suggestions && ls.suggestions.length > 0);
  if (!hasContent) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  $('board-summary-list').innerHTML = (ls.board_summaries || [])
    .map(s => `<div class="board-summary-item">${escHtml(s)}</div>`).join('');
  $('board-suggestions-list').innerHTML = (ls.suggestions || [])
    .map(s => `<div class="board-suggestion-item">💡 ${escHtml(s)}</div>`).join('');

  // Template buttons — clicking copies text to chat input
  const btns = $('board-template-btns');
  btns.innerHTML = '';
  (ls.template_messages || []).forEach(tmpl => {
    const btn = document.createElement('button');
    btn.className = 'btn-template-msg';
    btn.textContent = tmpl;
    btn.onclick = () => {
      const input = $('chat-input');
      if (input) { input.value = tmpl; input.focus(); }
    };
    btns.appendChild(btn);
  });
}

function updateChatLimit() {
  const count = (gameState && gameState.day_chat_count) || 0;
  const max = (gameState && gameState.day_chat_max) || 5;
  const remaining = Math.max(0, max - count);
  const el = $('chat-remaining');
  if (el) el.textContent = remaining;

  const input = $('chat-input');
  const btn = $('chat-send-btn');
  const limitInfo = $('chat-limit-info');

  if (remaining <= 0) {
    if (input) { input.disabled = true; input.placeholder = '発言回数の上限に達しました'; }
    if (btn) btn.disabled = true;
    if (limitInfo) limitInfo.classList.add('limit-reached');
  } else {
    if (input) { input.disabled = false; input.placeholder = '発言する...'; }
    if (btn) btn.disabled = false;
    if (limitInfo) limitInfo.classList.remove('limit-reached');
  }
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

// CO declaration buttons (Lite mode)
const _CO_MESSAGES = {
  detective: '私が探偵COします！探偵です。',
  heimin:    '私は平民です。平民COします。',
  fugo:      '実は私が富豪です。富豪COします。',
  hinmin:    '実は私が貧民です。貧民COします。',
};
document.querySelectorAll('.btn-co').forEach(btn => {
  btn.addEventListener('click', () => {
    const role = btn.dataset.co;
    const msg = _CO_MESSAGES[role];
    if (msg) { $('chat-input').value = msg; sendChat(); }
  });
});

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

  // Check client-side limit before sending
  const count = (gameState && gameState.day_chat_count) || 0;
  const max = (gameState && gameState.day_chat_max) || 5;
  if (count >= max) {
    updateChatLimit();
    return;
  }

  $('chat-input').value = '';
  $('chat-send-btn').disabled = true;

  const chatEndpoint = (gameState && gameState.game_mode === 'lite')
    ? `${API}/api/game/lite/chat`
    : `${API}/api/game/chat`;

  try {
    const res = await fetch(chatEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId, message: msg }),
    });
    if (!res.ok) {
      const err = await res.json();
      if (res.status === 400 && err.detail && err.detail.includes('上限')) {
        if (gameState) gameState.day_chat_count = max;
        updateChatLimit();
      }
      return;
    }
    const data = await res.json();
    gameState.chat_history = data.chat_history;

    // Sync logic_state from response (Lite mode)
    if (data.logic_state) {
      gameState.logic_state = data.logic_state;
      renderBoardSummary();
    }

    // Hard mode: baton info
    if (data.npc_responses && gameState.game_mode !== 'lite') {
      data.npc_responses.forEach(r => {
        if (r.baton_target_id) {
          lastBatonMap[r.npc_id] = { baton_target_id: r.baton_target_id, baton_action: r.baton_action };
        } else {
          delete lastBatonMap[r.npc_id];
        }
      });
    }

    // Update investigation notes (hard mode)
    if (data.investigation_notes) {
      gameState.investigation_notes = data.investigation_notes;
      renderInvestigationNotes();
    }
    // Update amnesia clues — auto-expand panel on first new clue (hard mode)
    if (data.amnesia_clues) {
      const prevCount = (gameState.amnesia_clues || []).length;
      gameState.amnesia_clues = data.amnesia_clues;
      renderAmnesiaClues();
      if (data.amnesia_clues.length > prevCount) {
        $('amnesia-list').classList.remove('hidden');  // auto-open on new clue
      }
    }
    // Update chat count
    if (data.day_chat_count !== undefined) {
      gameState.day_chat_count = data.day_chat_count;
      gameState.day_chat_max = data.day_chat_max || 5;
    }
    updateChatLimit();
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
  const voteEndpoint = (gameState && gameState.game_mode === 'lite')
    ? `${API}/api/game/lite/npc-votes`
    : `${API}/api/game/npc-votes`;
  try {
    const res = await fetch(voteEndpoint, {
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
      const isMe = data.hanged_player.id === playerId;
      if (isMe) {
        // Ghost mode notification for human player
        await new Promise(resolve => {
          const modal = document.createElement('div');
          modal.className = 'ghost-notification-overlay';
          modal.innerHTML = `
            <div class="ghost-notification-box">
              <div class="ghost-notification-icon">💀</div>
              <h3 class="ghost-notification-title">あなたは吊られました</h3>
              <p class="ghost-notification-body">しかしゲームは続きます。<br>ゴーストとして観戦してください…<br><br>すべての真実があなたの目に映る。</p>
              <button class="btn-primary ghost-notification-ok">観戦を続ける</button>
            </div>
          `;
          document.body.appendChild(modal);
          modal.querySelector('.ghost-notification-ok').addEventListener('click', () => {
            modal.remove();
            resolve();
          });
        });
      } else {
        alert(`${data.hanged_player.name}が処刑されました。\n役職: ${roleLabel(data.hanged_player.role)}\n勝利条件: ${data.hanged_player.victory_condition}`);
      }
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

    // Lite mode: check for lite pending decoy (human as defender)
    if (gameState.game_mode === 'lite') {
      if (gameState.lite_pending_decoy) {
        showLiteCheatReactPanel(gameState.lite_pending_decoy.decoy_text);
      } else {
        // Check if human hinmin can cheat (lite)
        const me = gameState.players.find(p => p.id === playerId);
        if (me && me.role === 'hinmin' && !me.cheat_used_this_night && !me.is_hanged) {
          showLiteCheatDecoyPanel();
        } else {
          await completeCheatPhase();
        }
      }
      return;
    }

    // Hard mode: Route to cheat phase
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

  // v4: detective panel — shown at night start if player is detective and hasn't used ability
  const detectivePanel = $('v4-detective-panel');
  if (gameMode === 'lite' && myGameRole === 'detective' && !detectiveUsed) {
    detectivePanel.classList.remove('hidden');
    populateDetectiveTargetSelect();
  } else {
    detectivePanel.classList.add('hidden');
  }

  renderNightPlayersList();
  renderTableCards();
  renderPlayerHand();
  updateTurnIndicator();
  renderNightLog();
  renderHangedPanel();
  renderNightChatTemplates();
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

// ─── Night Chat ──────────────────────────────────────────────
const NIGHT_CHAT_TEMPLATES = [
  { label: 'いい手だ', msg: 'いい手だ…' },
  { label: '次は覚悟しろ', msg: '次は覚悟しろ' },
  { label: 'なんだそれは！', msg: 'なんだそれは！' },
  { label: 'ふん、まだまだ', msg: 'ふん、まだまだだ' },
  { label: '静かにしろ', msg: '…静かにしろ' },
];

function renderNightChatTemplates() {
  const container = $('night-chat-templates');
  if (!container) return;
  container.innerHTML = '';
  NIGHT_CHAT_TEMPLATES.forEach(t => {
    const btn = document.createElement('button');
    btn.className = 'night-template-btn';
    btn.textContent = t.label;
    btn.addEventListener('click', () => {
      $('night-chat-input').value = t.msg;
      sendNightChat();
    });
    container.appendChild(btn);
  });
}

$('night-chat-send-btn').addEventListener('click', sendNightChat);
$('night-chat-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendNightChat(); });

async function sendNightChat() {
  const input = $('night-chat-input');
  const msg = input.value.trim();
  if (!msg || !gameId) return;

  input.value = '';
  $('night-chat-send-btn').disabled = true;

  // Add to local night log immediately
  const me = gameState.players.find(p => p.id === playerId);
  nightLog.push({ type: 'night-chat-player', text: `${me ? me.name : 'あなた'}:「${msg}」` });
  renderNightLog();

  try {
    const res = await fetch(`${API}/api/game/night-chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, player_id: playerId, message: msg }),
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.reactions && data.reactions.length > 0) {
      data.reactions.forEach(r => {
        nightLog.push({ type: 'night-chat-npc', text: `${r.name}:「${r.text}」` });
      });
      renderNightLog();
    }
  } catch (e) {
    console.error(e);
  } finally {
    $('night-chat-send-btn').disabled = false;
  }
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

// ─── Auto Mode ────────────────────────────────────────────────
$('auto-mode-btn').addEventListener('click', () => {
  autoMode = !autoMode;
  $('auto-mode-btn').classList.toggle('active', autoMode);
  $('auto-mode-btn').textContent = autoMode ? '⚡ AUTO ON' : '⚡ AUTO';
  if (autoMode && gameState && !gameState.game_over) {
    if (gameState.phase === 'day') scheduleAutoDay();
    else if (gameState.phase === 'night') scheduleAutoNight();
  }
});

function scheduleAutoDay() {
  if (!autoMode || autoRunning) return;
  setTimeout(autoRunDay, 800);
}
function scheduleAutoNight() {
  if (!autoMode || autoRunning) return;
  setTimeout(autoRunNight, 600);
}

async function autoRunDay() {
  if (!autoMode || autoRunning || !gameState || gameState.phase !== 'day' || gameState.game_over) return;
  if (gameState.game_mode !== 'lite') return;  // day-auto is Lite only
  autoRunning = true;
  $('auto-mode-btn').textContent = '⚡ 進行中…';
  try {
    const res = await fetch(`${API}/api/game/lite/auto-day`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId }),
    });
    if (!res.ok) {
      console.error('autoRunDay: server error', res.status, await res.text());
      return;
    }
    const data = await res.json();
    gameState = data.state;
    nightLog = [];  // reset for new night

    // Merge chat log from server (append new entries)
    if (data.chat_log && Array.isArray(data.chat_log)) {
      gameState.chat_history = [...(gameState.chat_history || []), ...data.chat_log];
    }
    // Apply baton / npc response info if provided
    if (data.npc_responses && Array.isArray(data.npc_responses)) {
      data.npc_responses.forEach(r => {
        if (r.baton_target_id) lastBatonMap[r.npc_id] = { baton_target_id: r.baton_target_id, baton_action: r.baton_action };
        else delete lastBatonMap[r.npc_id];
      });
    }
    // Update investigation notes / amnesia clues if present
    if (data.investigation_notes) {
      gameState.investigation_notes = data.investigation_notes;
    }
    if (data.amnesia_clues) {
      const prevCount = (gameState.amnesia_clues || []).length;
      gameState.amnesia_clues = data.amnesia_clues;
      if (data.amnesia_clues.length > prevCount) $('amnesia-list').classList.remove('hidden');
    }
    // Update chat counters if server sent them
    if (data.day_chat_count !== undefined) {
      gameState.day_chat_count = data.day_chat_count;
      gameState.day_chat_max = data.day_chat_max || gameState.day_chat_max || 5;
    }
    if (data.hanged_player) {
      const hp = data.hanged_player;
      const isMe = hp.id === playerId;
      if (!isMe) {
        nightLog.push({ type: 'special', text: `⚖ ${hp.name}が処刑されました（${roleLabel(hp.role)}）` });
      }
    }
    if (data.night_situation) {
      $('night-situation-text').textContent = data.night_situation;
      $('night-situation-banner').classList.remove('hidden');
    }
    // Reset BEFORE renderAll so scheduleAutoNight() can set its timer
    autoRunning = false;
    $('auto-mode-btn').textContent = '⚡ AUTO ON';
    renderAll();
  } catch (e) {
    console.error('autoRunDay error:', e);
  } finally {
    autoRunning = false;
    $('auto-mode-btn').textContent = '⚡ AUTO ON';
  }
}

async function autoRunNight() {
  if (!autoMode || autoRunning || !gameState || gameState.phase !== 'night' || gameState.game_over) return;
  // If it's an NPC's turn, the server handles it — just wait and retry
  if (gameState.current_turn !== playerId) {
    setTimeout(autoRunNight, 800);
    return;
  }
  autoRunning = true;
  try {
    const res = await fetch(`${API}/api/game/auto-play`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId }),
    });
    if (!res.ok) {
      console.error('autoRunNight: server error', res.status, await res.text());
      return;
    }
    const data = await res.json();
    gameState = data.state;
    if (data.npc_actions && data.npc_actions.length > 0) {
      addNightLogEntries(data.npc_actions);
    }
    // Reset BEFORE renderAll so scheduleAutoDay/Night() can set its timer
    autoRunning = false;
    renderAll();
  } catch (e) {
    console.error('autoRunNight error:', e);
  } finally {
    autoRunning = false;
  }
}

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

// ═══════════════════════════════════════════════════════════
//   LITE MODE: 陽動イカサマシステム
// ═══════════════════════════════════════════════════════════

function showLiteCheatDecoyPanel() {
  // Fill target select
  const targetSel = $('lite-cheat-target');
  targetSel.innerHTML = '';
  gameState.players
    .filter(p => p.id !== playerId && !p.is_hanged && !p.is_out)
    .forEach(p => {
      const opt = document.createElement('option');
      opt.value = p.id;
      opt.textContent = p.name;
      targetSel.appendChild(opt);
    });
  $('lite-decoy-text').value = '';
  $('lite-real-text').value = '';
  $('lite-cheat-decoy-panel').classList.remove('hidden');
}

$('lite-cheat-submit-btn').addEventListener('click', submitLiteCheatDecoy);
$('lite-cheat-skip-btn').addEventListener('click', async () => {
  $('lite-cheat-decoy-panel').classList.add('hidden');
  await completeCheatPhase();
});

async function submitLiteCheatDecoy() {
  const targetId = $('lite-cheat-target').value;
  const decoyText = $('lite-decoy-text').value.trim();
  const realText = $('lite-real-text').value.trim();
  if (!decoyText || !realText) {
    alert('【陽動】と【本命】の両方を入力してください');
    return;
  }
  $('lite-cheat-submit-btn').disabled = true;
  $('lite-cheat-decoy-panel').classList.add('hidden');

  try {
    const res = await fetch(`${API}/api/game/lite/cheat-decoy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        cheater_id: playerId,
        target_id: targetId,
        decoy_text: decoyText,
        real_text: realText,
      }),
    });
    const data = await res.json();
    gameState = data.state;

    if (data.pending) {
      // Human is defending — show react panel
      showLiteCheatReactPanel(data.decoy_shown);
    } else {
      // NPC was targeted — show result
      showLiteCheatResult(data);
    }
  } catch (e) {
    console.error(e);
    await completeCheatPhase();
  } finally {
    $('lite-cheat-submit-btn').disabled = false;
  }
}

function showLiteCheatReactPanel(decoyText) {
  $('lite-decoy-display').textContent = decoyText;
  $('lite-react-input').value = '';
  $('lite-cheat-react-panel').classList.remove('hidden');
  $('lite-react-submit-btn').disabled = false;

  // Start 5-second countdown
  let seconds = 5;
  $('lite-react-timer').textContent = seconds;
  if (liteReactTimer) clearInterval(liteReactTimer);
  liteReactTimer = setInterval(() => {
    seconds -= 1;
    const el = $('lite-react-timer');
    if (el) el.textContent = seconds;
    if (seconds <= 0) {
      clearInterval(liteReactTimer);
      liteReactTimer = null;
      // Auto-submit with empty reaction (time expired)
      submitLiteCheatReact();
    }
  }, 1000);
}

$('lite-react-submit-btn').addEventListener('click', submitLiteCheatReact);

async function submitLiteCheatReact() {
  if (liteReactTimer) {
    clearInterval(liteReactTimer);
    liteReactTimer = null;
  }
  $('lite-react-submit-btn').disabled = true;
  $('lite-cheat-react-panel').classList.add('hidden');

  const reaction = ($('lite-react-input').value || '').slice(0, 15);

  try {
    const res = await fetch(`${API}/api/game/lite/cheat-react`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, defender_id: playerId, reaction }),
    });
    const data = await res.json();
    gameState = data.state;
    showLiteCheatResult(data);
  } catch (e) {
    console.error(e);
    renderAll();
    await completeCheatPhase();
  }
}

function showLiteCheatResult(data) {
  const panel = $('lite-cheat-result-panel');
  const judgmentMap = { big_success: '🃏 陽動成功！', draw: '🛡 かわした！', big_fail: '💥 露見！' };
  $('lite-cheat-result-title').textContent = judgmentMap[data.judgment] || 'イカサマ結果';
  $('lite-cheat-result-story').textContent = data.story || '';

  const revealEl = $('lite-cheat-result-reveal');
  if (data.cheater_revealed && data.cheater_name) {
    revealEl.textContent = `⚠ ${data.cheater_name}のイカサマが露見しました！（翌日の投票に注意）`;
    revealEl.classList.remove('hidden');
  } else {
    revealEl.classList.add('hidden');
  }

  panel.classList.remove('hidden');

  $('lite-cheat-result-ok').onclick = async () => {
    panel.classList.add('hidden');
    renderAll();
    await completeCheatPhase();
  };
}


// ─── v4: Detective UI ─────────────────────────────────────────

function populateDetectiveTargetSelect() {
  const sel = $('detective-target-select');
  sel.innerHTML = '';
  const others = gameState.players.filter(p => p.id !== playerId && !p.is_hanged);
  others.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name;
    sel.appendChild(opt);
  });
}

async function submitDetectiveInvestigate() {
  const targetId = $('detective-target-select').value;
  const infoType = document.querySelector('input[name="detective-info"]:checked').value;
  if (!targetId) return;

  $('detective-investigate-btn').disabled = true;
  try {
    const res = await fetch(`${API}/api/game/lite/detective-investigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        game_id: gameId,
        detective_id: playerId,
        target_id: targetId,
        info_type: infoType,
      }),
    });
    const data = await res.json();
    if (!res.ok) { alert(data.detail || 'エラーが発生しました'); return; }

    detectiveUsed = true;
    const resultArea = $('detective-result-area');
    resultArea.style.display = 'block';
    resultArea.innerHTML = `<strong>🔍 調査結果（秘密）</strong><br>${escHtml(data.message)}`;
    $('detective-investigate-btn').disabled = true;
    $('detective-skip-btn').textContent = '閉じる';
  } catch (e) {
    console.error(e);
    alert('エラー: ' + e.message);
    $('detective-investigate-btn').disabled = false;
  }
}

$('detective-investigate-btn').addEventListener('click', submitDetectiveInvestigate);
$('detective-skip-btn').addEventListener('click', () => {
  $('v4-detective-panel').classList.add('hidden');
  // If ability not yet used, mark it as skipped for this session (won't prompt again until page reload)
  if (!detectiveUsed) {
    detectiveUsed = true;
  }
});

// ─── Init ────────────────────────────────────────────────────
showScreen('setup');
