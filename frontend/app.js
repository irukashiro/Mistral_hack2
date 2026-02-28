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

  if (gameState.phase === 'day') {
    showPhase('day');
    renderDayPhase();
  } else {
    showPhase('night');
    renderNightPhase();
  }
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
}

function renderPlayersList() {
  const container = $('players-list');
  container.innerHTML = '';
  gameState.players.forEach(p => {
    const div = document.createElement('div');
    div.className = `player-card${p.is_human ? ' is-human' : ''}${p.is_hanged ? ' hanged' : ''}${p.is_out ? ' out' : ''}`;
    const roleMap = { fugo: '富豪', heimin: '平民', hinmin: '貧民' };
    const roleLabel = p.role ? roleMap[p.role] : '?';
    const roleBadge = p.role
      ? `<span class="player-role-badge ${p.role}">${roleLabel}</span>`
      : '<span class="player-role-badge">?</span>';
    div.innerHTML = `
      <div class="player-name">${p.name}${p.is_human ? ' ★' : ''}${roleBadge}</div>
      <div class="player-cards-count">手札: ${p.hand_count}枚${p.is_hanged ? ' 【吊】' : ''}${p.is_out ? ' 【上がり】' : ''}</div>
    `;
    container.appendChild(div);
  });
}

function renderChatLog() {
  const log = $('chat-log');
  const wasAtBottom = log.scrollHeight - log.clientHeight <= log.scrollTop + 10;

  log.innerHTML = '';
  gameState.chat_history.forEach(msg => {
    const div = document.createElement('div');
    const cls = msg.speaker_id === 'system' ? 'system' : msg.speaker_id === playerId ? 'human' : 'npc';
    div.className = `chat-msg ${cls}`;
    if (msg.speaker_id !== 'system') {
      div.innerHTML = `<div class="chat-speaker">${msg.speaker_name}</div>${escHtml(msg.text)}`;
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

// Chat
$('chat-send-btn').addEventListener('click', sendChat);
$('chat-input').addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

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

    // Log any NPC vs NPC cheat results
    if (data.npc_cheat_results && data.npc_cheat_results.length > 0) {
      data.npc_cheat_results.forEach(r => {
        nightLog.push({ type: 'cheat', text: `[イカサマ] ${r.cheater} → ${r.target}: ${r.story}` });
      });
    }

    myVoteTarget = null;
    selectedCards.clear();
    renderAll();

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
      <div class="night-player-name">${p.name}${gameState.current_turn === p.id ? ' ▶' : ''}</div>
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

    renderAll();

    if (gameState.game_over) {
      setTimeout(renderGameOver, 800);
    }
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

    renderAll();

    if (gameState.game_over) {
      setTimeout(renderGameOver, 800);
    }
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

  $('defense-submit-btn').disabled = true;
  try {
    const res = await fetch(`${API}/api/game/cheat-defend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ game_id: gameId, defender_id: playerId, defense_method: defense }),
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
    gameState = data.state;

    if (data.npc_actions && data.npc_actions.length > 0) {
      addNightLogEntries(data.npc_actions);
    }

    renderAll();

    if (gameState.game_over) {
      setTimeout(renderGameOver, 800);
    }
  } catch (e) {
    console.error(e);
    renderAll();
  }
}

// ─── Game Over ───────────────────────────────────────────────
function renderGameOver() {
  const winners = gameState.winner_ids || [];
  const titleEl = $('gameover-title');
  const isWinner = winners.includes(playerId);

  titleEl.textContent = isWinner ? '🏆 勝利！' : '敗北...';
  titleEl.style.color = isWinner ? '#c8a84b' : '#c0392b';

  const winnersEl = $('gameover-winners');
  winnersEl.innerHTML = '';
  if (winners.length > 0) {
    winners.forEach(wid => {
      const p = gameState.players.find(p => p.id === wid);
      const div = document.createElement('div');
      div.className = `winner-item${wid === playerId ? ' you' : ''}`;
      div.textContent = `${p ? p.name : wid}${wid === playerId ? ' (あなた)' : ''}`;
      winnersEl.appendChild(div);
    });
  } else {
    winnersEl.innerHTML = '<p class="muted">勝者なし</p>';
  }

  showScreen('gameover');
}

$('restart-btn').addEventListener('click', () => {
  gameId = null;
  playerId = 'player_human';
  gameState = null;
  selectedCards.clear();
  myVoteTarget = null;
  nightLog = [];
  showScreen('setup');
});

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
