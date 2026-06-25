(() => {
  const logEl = document.getElementById('chat-log');
  const formEl = document.getElementById('chat-form');
  const inputEl = document.getElementById('chat-input');
  const statusEl = document.getElementById('chat-status');
  const welcomeEl = document.getElementById('chat-welcome');
  const loadingEl = document.getElementById('chat-loading');

  if (!logEl) return;

  if (typeof io === 'undefined') {
    if (loadingEl) {
      loadingEl.innerHTML =
        '<i class="fas fa-exclamation-triangle" style="font-size:24px;margin-bottom:12px;display:block;color:#ef4444"></i> Failed to connect. Please refresh.';
    }
    return;
  }

  const displayName = logEl.dataset.displayName || 'Guest';
  const socket = io({ transports: ['websocket', 'polling'] });
  let connected = false;

  const loadingTimeout = setTimeout(() => {
    if (loadingEl && loadingEl.style.display !== 'none') {
      loadingEl.innerHTML =
        '<i class="fas fa-exclamation-triangle" style="font-size:24px;margin-bottom:12px;display:block;color:#ef4444"></i> Could not load messages. <button onclick="location.reload()" style="display:block;margin:12px auto 0;padding:8px 20px;border:none;border-radius:8px;background:var(--accent,#6366f1);color:#fff;cursor:pointer">Retry</button>';
    }
  }, 10000);

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
    connected = true;
    if (statusEl) {
      statusEl.innerHTML = '<span class="chat-online-dot"></span> Connected';
    }
    socket.emit('community_join', { name: displayName });
  });

  socket.on('disconnect', () => {
    connected = false;
    if (statusEl) {
      statusEl.textContent = 'Reconnecting...';
    }
  });

  socket.on('connect_error', () => {
    connected = false;
    clearTimeout(loadingTimeout);
    if (loadingEl && loadingEl.style.display !== 'none') {
      loadingEl.innerHTML =
        '<i class="fas fa-exclamation-triangle" style="font-size:24px;margin-bottom:12px;display:block;color:#ef4444"></i> Connection failed. <button onclick="location.reload()" style="display:block;margin:12px auto 0;padding:8px 20px;border:none;border-radius:8px;background:var(--accent,#6366f1);color:#fff;cursor:pointer">Retry</button>';
    }
    if (statusEl) {
      statusEl.textContent = 'Connection failed';
    }
  });

  socket.on('community_history', (payload) => {
    clearTimeout(loadingTimeout);
    if (loadingEl) loadingEl.style.display = 'none';
    if (welcomeEl) welcomeEl.style.display = 'none';

    if (payload?.messages && Array.isArray(payload.messages)) {
      payload.messages.forEach((entry) => appendMessage(entry));
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

      if (!connected) {
        const orig = inputEl.placeholder;
        inputEl.placeholder = 'Not connected - try again...';
        inputEl.classList.add('chat-input-error');
        setTimeout(() => {
          inputEl.placeholder = orig;
          inputEl.classList.remove('chat-input-error');
        }, 2000);
        return;
      }

      socket.emit('community_message', { message });
      inputEl.value = '';
      inputEl.focus();
    });
  }
})();
