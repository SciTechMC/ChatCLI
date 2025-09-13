import { store } from '../core/store.js';

let debTimer = null;

const ESC = s => s
  .replace(/&/g,'&amp;')
  .replace(/</g,'&lt;')
  .replace(/>/g,'&gt;')
  .replace(/"/g,'&quot;')
  .replace(/'/g,'&#39;');

function norm(s) {
  return (s || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, ''); // strip diacritics
}

function ensureEmptyStateEl() {
  let el = document.getElementById('chatSearchEmpty');
  if (!el) {
    el = document.createElement('div');
    el.id = 'chatSearchEmpty';
    el.textContent = 'No chats found';
    el.style.display = 'none';
    store.refs.chatListEl?.appendChild(el);
  }
  return el;
}

function getChatItems() {
  // Expect each chat row to have data-chat-id
  // and a child .chat-name (we'll add data-label for the pristine text)
  return Array.from(store.refs.chatListEl?.querySelectorAll('[data-chat-id]') || []);
}

function getLabelEl(row) {
  return row.querySelector('.chat-name') || row;
}

function setLabelWithHighlight(el, raw, q) {
  if (!q) { el.innerHTML = ESC(raw); return; }
  const lower = raw.toLowerCase();
  const i = lower.indexOf(q.toLowerCase());
  if (i < 0) { el.innerHTML = ESC(raw); return; }
  const a = ESC(raw.slice(0, i));
  const b = ESC(raw.slice(i, i + q.length));
  const c = ESC(raw.slice(i + q.length));
  el.innerHTML = `${a}<mark>${b}</mark>${c}`;
}

function applyFilter(query) {
  const qn = norm(query.trim());
  const rows = getChatItems();
  const emptyEl = ensureEmptyStateEl();

  let visible = 0;
  for (const row of rows) {
    const nameEl = getLabelEl(row);
    // keep pristine label in data-label once
    if (!nameEl.dataset.label) nameEl.dataset.label = nameEl.textContent?.trim() || '';

    const raw = nameEl.dataset.label;
    const matches = !qn || norm(raw).includes(qn);

    row.style.display = matches ? '' : 'none';
    if (matches) {
      setLabelWithHighlight(nameEl, raw, query);
      visible++;
    } else {
      // restore in case it was highlighted earlier (kept hidden, but consistent)
      nameEl.innerHTML = ESC(raw);
    }
  }

  emptyEl.style.display = (!visible && qn) ? '' : 'none';
}

export function initChatSearch() {
  const input = store.refs.chatSearchInput;
  if (!input) return;

  // initial reapply if user has something typed (e.g., hot reload)
  if (input.value) applyFilter(input.value);

  input.addEventListener('input', () => {
    clearTimeout(debTimer);
    debTimer = setTimeout(() => applyFilter(input.value), 120);
  });

  // Clear with Escape
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && input.value) {
      input.value = '';
      applyFilter('');
      e.stopPropagation();
    }
  });
}

// Call this after you re-render the chat list (e.g., after loadChats())
export function reapplyChatSearch() {
  const input = store.refs.chatSearchInput;
  if (input) applyFilter(input.value || '');
}
