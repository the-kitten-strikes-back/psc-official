(() => {
  const logEl = document.getElementById('chat-log');
  const formEl = document.getElementById('chat-form');
  const inputEl = document.getElementById('chat-input');
  const statusEl = document.getElementById('chat-status');
  const welcomeEl = document.getElementById('chat-welcome');
  const loadingEl = document.getElementById('chat-loading');

  if (!logEl || typeof io === 'undefined') return;

  const displayName = logEl.dataset.displayName || 'Guest';

  const socket = io({ transports: ['websocket', 'polling'] });

  const makeTime = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const appendSystem = (message) => {
    const el = document.createElement('div');
    el.className = 'chat-system';
    el.textContent = message;
    logEl.appendChild(el);
    logEl.scrollTop = logEl.scrollHeight;
  };

  const appendMessage = ({ sender, message, timestamp }, prepend = false) => {
    if (!message) return;

    const mine = sender === displayName;
    const bubble = document.createElement('div');
    bubble.className = `chat-message ${mine ? 'me' : 'other'}`;

    if (!mine) {
      const senderEl = document.createElement('strong');
      senderEl.className = 'chat-sender';
      senderEl.textContent = sender || 'Guest';
      bubble.appendChild(senderEl);
    }

    const textEl = document.createElement('div');
    textEl.textContent = message;
    bubble.appendChild(textEl);

    const timeEl = document.createElement('small');
    timeEl.className = 'chat-time';
    timeEl.textContent = timestamp || makeTime();
    bubble.appendChild(timeEl);

    if (prepend) {
      logEl.insertBefore(bubble, logEl.firstChild);
    } else {
      logEl.appendChild(bubble);
      logEl.scrollTop = logEl.scrollHeight;
    }
  };

  socket.on('connect', () => {
    if (statusEl) {
      statusEl.innerHTML = '<span class="chat-online-dot"></span> Connected';
    }
    socket.emit('community_join', { name: displayName });
  });

  socket.on('disconnect', () => {
    if (statusEl) {
      statusEl.textContent = 'Reconnecting...';
    }
  });

  socket.on('community_history', (payload) => {
    if (loadingEl) loadingEl.style.display = 'none';
    if (welcomeEl) welcomeEl.style.display = 'none';

    if (payload?.messages && Array.isArray(payload.messages)) {
      payload.messages.reverse().forEach((entry) => appendMessage(entry));
    }
  });

  socket.on('community_message', (payload) => {
    if (welcomeEl) welcomeEl.style.display = 'none';
    if (loadingEl) loadingEl.style.display = 'none';
    appendMessage(payload || {});
  });

  socket.on('community_system', (payload) => {
    if (payload?.message) appendSystem(payload.message);
  });

  if (formEl) {
    formEl.addEventListener('submit', (e) => {
      e.preventDefault();
      const message = (inputEl?.value || '').trim();
      if (!message) return;

      socket.emit('community_message', { message });
      inputEl.value = '';
      inputEl.focus();
    });
  }
})();
