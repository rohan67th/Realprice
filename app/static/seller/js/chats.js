/* chats.js — Production Seller Chats renderer with real FastAPI backend */
var CHATS = [];
let activeChat = -1;
let renderedMsgIds = new Set();
let pollInterval = null;
let searchQuery = '';

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatMsgTime(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return isoStr;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch (e) {
    return isoStr;
  }
}

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

function initChatsData() {
  const dataEl = document.getElementById('seller-conversations-data');
  if (dataEl && dataEl.textContent.trim()) {
    try {
      CHATS = JSON.parse(dataEl.textContent);
    } catch (e) {
      console.error('[Chats] Failed to parse seller conversations JSON:', e);
      CHATS = [];
    }
  } else if (window.REAL_CHATS && Array.isArray(window.REAL_CHATS)) {
    CHATS = window.REAL_CHATS;
  } else {
    CHATS = [];
  }
}

function renderChatList() {
  const listEl = document.getElementById('chat-list');
  if (!listEl) return;

  const q = searchQuery.toLowerCase().trim();
  const filtered = CHATS.map((c, idx) => ({ c, originalIndex: idx })).filter(item => {
    if (!q) return true;
    const nameMatch = (item.c.name || '').toLowerCase().includes(q);
    const propMatch = (item.c.property || '').toLowerCase().includes(q);
    const lastMatch = (item.c.last || '').toLowerCase().includes(q);
    return nameMatch || propMatch || lastMatch;
  });

  if (CHATS.length === 0) {
    listEl.innerHTML = `
      <div class="p-8 text-center text-ink-400">
        <i class="ri-chat-3-line text-3xl mb-2 block text-brand-500"></i>
        <p class="font-semibold text-sm text-ink-900 dark:text-white">No conversations yet</p>
        <p class="text-xs text-ink-400 mt-1">When buyers schedule approved tours, conversations will appear here.</p>
      </div>
    `;
    return;
  }

  if (filtered.length === 0) {
    listEl.innerHTML = `
      <div class="p-6 text-center text-ink-400 text-xs">
        <i class="ri-search-line text-2xl mb-1 block"></i>
        <p>No conversations match "${escapeHtml(searchQuery)}"</p>
      </div>
    `;
    return;
  }

  listEl.innerHTML = filtered.map(({ c, originalIndex }) => {
    const isActive = originalIndex === activeChat;
    return `
      <button type="button" onclick="selectChat(${originalIndex})" class="w-full flex items-center gap-3 p-3 text-left transition ${
        isActive ? 'bg-brand-50 dark:bg-brand-900/20' : 'hover:bg-ink-50 dark:hover:bg-ink-800/40'
      }">
        <div class="relative shrink-0">
          <img src="${escapeHtml(c.avatar || 'https://ui-avatars.com/api/?name=Buyer&background=4f46e5&color=fff')}" class="h-11 w-11 rounded-full object-cover" alt="" onerror="this.src='https://ui-avatars.com/api/?name=Buyer&background=4f46e5&color=fff'"/>
          ${c.online ? '<span class="absolute bottom-0 right-0 h-3 w-3 rounded-full bg-success-500 ring-2 ring-white dark:ring-ink-900"></span>' : ''}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-baseline">
            <p class="text-sm font-semibold text-ink-900 dark:text-white truncate">${escapeHtml(c.name)}</p>
            <span class="text-[10px] text-ink-400 shrink-0 ml-1">${escapeHtml(c.time || '')}</span>
          </div>
          <p class="text-xs text-ink-400 truncate mt-0.5">${escapeHtml(c.last || 'No messages yet')}</p>
          ${c.property ? `<p class="text-[10px] text-brand-600 dark:text-brand-400 truncate mt-0.5 font-medium">${escapeHtml(c.property)}</p>` : ''}
        </div>
        ${c.unread ? `<span class="grid place-items-center min-w-4 h-4 px-1 text-[9px] font-bold text-white bg-brand-600 rounded-full shrink-0">${c.unread}</span>` : ''}
      </button>
    `;
  }).join('');
}

function selectChat(idx) {
  if (idx < 0 || idx >= CHATS.length) {
    activeChat = -1;
    renderChatList();
    renderEmptyThread();
    return;
  }

  activeChat = idx;
  renderChatList();
  renderChatThread();
}
window.selectChat = selectChat;

function renderEmptyThread() {
  const headerEl = document.getElementById('chat-header');
  const threadEl = document.getElementById('chat-thread');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');

  if (headerEl) {
    headerEl.innerHTML = `
      <div class="flex items-center gap-2 text-ink-400 text-sm">
        <i class="ri-chat-3-line text-lg"></i>
        <span>Select a conversation</span>
      </div>
    `;
  }
  if (threadEl) {
    threadEl.innerHTML = `
      <div class="flex items-center justify-center h-full text-center p-8">
        <div>
          <i class="ri-chat-smile-3-line text-4xl text-brand-500 mb-3 block"></i>
          <p class="text-sm font-semibold text-ink-900 dark:text-white">Select a conversation to start chatting</p>
          <p class="text-xs text-ink-400 mt-1">Choose a buyer from the list on the left.</p>
        </div>
      </div>
    `;
  }
  if (inputEl) inputEl.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

function renderChatThread() {
  if (activeChat < 0 || activeChat >= CHATS.length) {
    renderEmptyThread();
    return;
  }

  const c = CHATS[activeChat];
  const headerEl = document.getElementById('chat-header');
  const threadEl = document.getElementById('chat-thread');
  const inputEl = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');

  if (inputEl) inputEl.disabled = false;
  if (sendBtn) sendBtn.disabled = false;

  // Render header
  if (headerEl) {
    headerEl.innerHTML = `
      <img src="${escapeHtml(c.avatar || 'https://ui-avatars.com/api/?name=Buyer&background=4f46e5&color=fff')}" class="h-10 w-10 rounded-full object-cover shrink-0" onerror="this.src='https://ui-avatars.com/api/?name=Buyer&background=4f46e5&color=fff'"/>
      <div class="flex-1 min-w-0">
        <p class="font-bold text-ink-900 dark:text-white text-sm truncate">${escapeHtml(c.name)}</p>
        <p class="text-xs text-ink-400 truncate">${escapeHtml(c.property || '')} · <span class="capitalize text-success-600 dark:text-success-400 font-medium">${escapeHtml(c.status || 'Approved')}</span></p>
      </div>
      <a href="/seller_profile/${window.CURRENT_SELLER_ID || ''}/visits/" class="h-8 w-8 grid place-items-center rounded-lg text-ink-400 hover:bg-ink-100 dark:hover:bg-ink-800" title="Visit Tours">
        <i class="ri-calendar-check-line"></i>
      </a>
    `;
  }

  // Clear previous message IDs and poll interval
  renderedMsgIds.clear();
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }

  // Show loading indicator
  if (threadEl) {
    threadEl.innerHTML = `
      <div class="flex items-center justify-center h-full text-ink-400 text-xs">
        <i class="ri-loader-4-line animate-spin text-2xl text-brand-600 mr-2"></i>
        <span>Loading messages…</span>
      </div>
    `;
  }

  // Load message history from existing API
  fetchHistory(c.visit_id, true);

  // Start polling every 3 seconds for live message updates
  pollInterval = setInterval(function() {
    if (activeChat >= 0 && activeChat < CHATS.length && !document.hidden) {
      fetchHistory(CHATS[activeChat].visit_id, false);
    }
  }, 3000);
}

function fetchHistory(visitId, isInitial) {
  fetch(`/api/messaging/history/${visitId}/`, {
    headers: {
      'Accept': 'application/json',
    },
    credentials: 'same-origin',
  })
    .then(res => {
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      return res.json();
    })
    .then(data => {
      // In case activeChat changed while fetching
      if (activeChat < 0 || CHATS[activeChat].visit_id !== visitId) return;

      const threadEl = document.getElementById('chat-thread');
      if (!threadEl) return;

      const rawMessages = Array.isArray(data) ? data : (data.messages || []);

      if (isInitial) {
        threadEl.innerHTML = '';
        renderedMsgIds.clear();

        if (rawMessages.length === 0) {
          threadEl.innerHTML = `
            <div id="chat-no-msgs" class="flex items-center justify-center h-full text-center p-8">
              <div>
                <i class="ri-chat-smile-line text-4xl mb-2 block text-brand-500"></i>
                <p class="font-semibold text-sm text-ink-900 dark:text-white">No messages yet</p>
                <p class="text-xs text-ink-400 mt-1">Start chatting with ${escapeHtml(CHATS[activeChat].name)} regarding this property visit.</p>
              </div>
            </div>
          `;
          return;
        }
      } else {
        // Polling update: remove "No messages yet" placeholder if new messages arrived
        const emptyPlaceholder = document.getElementById('chat-no-msgs');
        if (emptyPlaceholder && rawMessages.length > 0) {
          emptyPlaceholder.remove();
        }
      }

      let hasNew = false;
      rawMessages.forEach(m => {
        const msgId = m.id;
        if (!renderedMsgIds.has(msgId)) {
          renderedMsgIds.add(msgId);
          hasNew = true;
          appendMessageBubble(m, threadEl);
        }
      });

      if (hasNew) {
        threadEl.scrollTop = threadEl.scrollHeight;

        // Update preview in conversation list
        if (rawMessages.length > 0) {
          const lastMsg = rawMessages[rawMessages.length - 1];
          CHATS[activeChat].last = lastMsg.content;
          CHATS[activeChat].time = formatMsgTime(lastMsg.timestamp);
          renderChatList();
        }
      }
    })
    .catch(err => {
      console.warn('[Chats] History fetch error:', err);
      if (isInitial) {
        const threadEl = document.getElementById('chat-thread');
        if (threadEl) {
          threadEl.innerHTML = `
            <div class="flex items-center justify-center h-full text-center p-8">
              <div class="text-danger-600 dark:text-danger-400 text-xs">
                <i class="ri-error-warning-line text-3xl mb-2 block"></i>
                <p class="font-semibold text-sm">Unable to load messages</p>
                <p class="text-ink-400 mt-1">Could not connect to messaging service.</p>
                <button type="button" onclick="fetchHistory(${visitId}, true)" class="btn-outline text-xs mt-3 px-3 py-1.5">
                  <i class="ri-refresh-line"></i> Try again
                </button>
              </div>
            </div>
          `;
        }
      }
    });
}

function appendMessageBubble(m, threadEl) {
  // Seller's own message: sender_seller_id matches window.CURRENT_SELLER_ID
  const isMe = window.CURRENT_SELLER_ID != null && String(m.sender_seller_id) === String(window.CURRENT_SELLER_ID);
  const timeStr = formatMsgTime(m.timestamp);

  const bubbleDiv = document.createElement('div');
  bubbleDiv.className = `flex ${isMe ? 'justify-end' : 'justify-start'} message-enter`;
  bubbleDiv.setAttribute('data-msg-id', m.id);

  bubbleDiv.innerHTML = `
    <div class="max-w-[75%] ${
      isMe
        ? 'bg-brand-600 text-white rounded-br-md'
        : 'bg-white dark:bg-ink-800 text-ink-800 dark:text-ink-100 rounded-bl-md'
    } rounded-2xl px-4 py-2.5 shadow-sm">
      <p class="text-sm whitespace-pre-wrap break-words">${escapeHtml(m.content)}</p>
      <p class="text-[10px] ${isMe ? 'text-brand-100' : 'text-ink-400'} mt-1 text-right">${escapeHtml(timeStr)}</p>
    </div>
  `;

  threadEl.appendChild(bubbleDiv);
}

function sendMessage() {
  if (activeChat < 0 || activeChat >= CHATS.length) return;

  const inputEl = document.getElementById('chat-input');
  if (!inputEl) return;

  const content = inputEl.value.trim();
  if (!content) return;

  const currentConv = CHATS[activeChat];
  const sendBtn = document.getElementById('chat-send-btn');

  // Disable UI while sending
  inputEl.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  fetch('/api/messaging/send/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    credentials: 'same-origin',
    body: JSON.stringify({
      visit_id: currentConv.visit_id,
      content: content,
    }),
  })
    .then(res => {
      if (!res.ok) {
        return res.json().then(data => {
          throw new Error(data.detail || data.error || `HTTP ${res.status}`);
        });
      }
      return res.json();
    })
    .then(data => {
      // Re-enable input
      inputEl.disabled = false;
      if (sendBtn) sendBtn.disabled = false;
      inputEl.value = '';
      inputEl.focus();

      // Remove empty placeholder if any
      const emptyPlaceholder = document.getElementById('chat-no-msgs');
      if (emptyPlaceholder) emptyPlaceholder.remove();

      // Render sent message immediately
      const threadEl = document.getElementById('chat-thread');
      if (threadEl && data.message_id) {
        renderedMsgIds.add(data.message_id);
        appendMessageBubble({
          id: data.message_id,
          sender_seller_id: window.CURRENT_SELLER_ID,
          content: content,
          timestamp: new Date().toISOString(),
        }, threadEl);
        threadEl.scrollTop = threadEl.scrollHeight;
      }

      // Update sidebar
      currentConv.last = content;
      currentConv.time = 'Just now';
      renderChatList();
    })
    .catch(err => {
      console.error('[Chats] Send error:', err);
      inputEl.disabled = false;
      if (sendBtn) sendBtn.disabled = false;
      inputEl.focus();
      alert(`Could not send message: ${err.message}`);
    });
}

document.addEventListener('DOMContentLoaded', function() {
  initChatsData();

  // Search input handler
  const searchInput = document.getElementById('chat-search');
  if (searchInput) {
    searchInput.addEventListener('input', function(e) {
      searchQuery = e.target.value;
      renderChatList();
    });
  }

  // Form submit handler
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', function(e) {
      e.preventDefault();
      sendMessage();
    });
  }

  // Initial selection
  if (CHATS.length > 0) {
    let targetIndex = 0;
    if (window.INITIAL_VISIT_ID) {
      const matchIdx = CHATS.findIndex(c => String(c.visit_id) === String(window.INITIAL_VISIT_ID));
      if (matchIdx !== -1) {
        targetIndex = matchIdx;
      }
    }
    selectChat(targetIndex);
  } else {
    renderChatList();
    renderEmptyThread();
  }
});
