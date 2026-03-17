(() => {
  const root = document.getElementById('psc-chatbot-root');
  if (!root) return;

  let isOpen = false;
  let history = [];
  let socket = null;
  let roomId = null;
  let displayName = null;
  let liveReady = false;

  const createEl = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  };

  const loadSocketIo = () => {
    if (typeof io !== 'undefined') return Promise.resolve();
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.socket.io/4.7.5/socket.io.min.js';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Socket.IO failed to load'));
      document.head.appendChild(script);
    });
  };

  const appendIncoming = (sender, message) => {
    if (!message) return;
    const isSelf = sender && sender === displayName;
    history.push({
      role: isSelf ? 'user' : 'assistant',
      content: isSelf ? message : `${sender || 'SoBAB'}: ${message}`,
      time: new Date().toISOString()
    });
    render();
  };

  const initLiveChat = async () => {
    if (liveReady) return;
    try {
      await loadSocketIo();
      const res = await fetch('/support/room');
      if (!res.ok) throw new Error('Room lookup failed');
      const data = await res.json();
      roomId = data.room_id;
      displayName = data.display_name || 'Guest';
      socket = io({ transports: ['websocket', 'polling'] });
      socket.on('connect', () => {
        socket.emit('customer_join', { room_id: roomId, name: displayName });
      });
      socket.on('chat_system', (payload) => {
        if (payload && payload.message) {
          appendIncoming('PSC', payload.message);
        }
      });
      socket.on('chat_message', (payload) => {
        if (payload && payload.message) {
          appendIncoming(payload.sender || 'SoBAB', payload.message);
        }
      });
      liveReady = true;
    } catch (err) {
      liveReady = false;
    }
  };

  const escapeHtml = (value) =>
    value
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');

  const renderInline = (value) => {
    let html = value;
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
    return html;
  };

  const renderMarkdown = (value) => {
    if (!value) return '';
    const blocks = value.split(/```/);
    let html = '';

    blocks.forEach((block, index) => {
      if (index % 2 === 1) {
        html += `<pre><code>${escapeHtml(block.trim())}</code></pre>`;
        return;
      }

      const escaped = escapeHtml(block);
      const lines = escaped.split('\n');
      let inUl = false;
      let inOl = false;

      lines.forEach((line) => {
        const trimmed = line.trim();
        const unordered = /^[-*]\s+/.exec(trimmed);
        const ordered = /^(\d+)\.\s+/.exec(trimmed);

        if (unordered) {
          if (!inUl) {
            html += '<ul>';
            inUl = true;
          }
          if (inOl) {
            html += '</ol>';
            inOl = false;
          }
          html += `<li>${renderInline(trimmed.replace(/^[-*]\s+/, ''))}</li>`;
          return;
        }

        if (ordered) {
          if (!inOl) {
            html += '<ol>';
            inOl = true;
          }
          if (inUl) {
            html += '</ul>';
            inUl = false;
          }
          html += `<li>${renderInline(trimmed.replace(/^\d+\.\s+/, ''))}</li>`;
          return;
        }

        if (inUl) {
          html += '</ul>';
          inUl = false;
        }
        if (inOl) {
          html += '</ol>';
          inOl = false;
        }

        if (!trimmed) {
          html += '<br />';
          return;
        }

        html += `${renderInline(trimmed)}<br />`;
      });

      if (inUl) html += '</ul>';
      if (inOl) html += '</ol>';
    });

    return html;
  };

  const formatTime = (value) => {
    const date = value instanceof Date ? value : new Date(value);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const render = () => {
    root.innerHTML = '';
    if (!isOpen) {
      const btn = createEl('button', 'psc-chatbot-launch', 'Chat with PSC');
      btn.addEventListener('click', () => {
        isOpen = true;
        render();
      });
      root.appendChild(btn);
      return;
    }

    const panel = createEl('div', 'psc-chatbot-panel');
    const header = createEl('div', 'psc-chatbot-header');
    header.appendChild(createEl('span', '', 'PSC Live Support'));
    const adminLink = createEl('a', '', 'Open Support Window');
    adminLink.href = '/support';
    adminLink.style.color = '#38bdf8';
    adminLink.style.fontSize = '12px';
    adminLink.style.marginLeft = '8px';
    adminLink.style.textDecoration = 'none';
    adminLink.target = '_blank';
    const close = createEl('button', 'psc-chatbot-close', '✕');
    close.addEventListener('click', () => {
      isOpen = false;
      render();
    });
    header.appendChild(adminLink);
    header.appendChild(close);

    const messages = createEl('div', 'psc-chatbot-messages');
    if (history.length === 0) {
      const intro = createEl('div', 'psc-chatbot-msg bot', 'You are connected to PSC customer care. Ask anything about pens, loans, or subscriptions.');
      messages.appendChild(intro);
    }
    history.forEach((msg) => {
      const bubble = createEl('div', `psc-chatbot-msg ${msg.role === 'user' ? 'user' : 'bot'}`);
      const body = createEl('div', 'psc-chatbot-msg-body');
      if (msg.role === 'assistant') body.innerHTML = renderMarkdown(msg.content);
      else body.textContent = msg.content;
      const time = createEl('div', 'psc-chatbot-msg-time', formatTime(msg.time || Date.now()));
      bubble.appendChild(body);
      bubble.appendChild(time);
      messages.appendChild(bubble);
    });

    const inputWrap = createEl('div', 'psc-chatbot-input');
    const input = createEl('input');
    input.type = 'text';
    input.placeholder = 'Type your message...';
    const send = createEl('button', '', 'Send');

    const sendMessage = async () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      history.push({ role: 'user', content: text, time: new Date().toISOString() });
      render();
      messages.scrollTop = messages.scrollHeight;
      if (!liveReady) {
        history.push({
          role: 'assistant',
          content: 'Connecting you to SoBAB live support...',
          time: new Date().toISOString()
        });
        render();
        await initLiveChat();
        if (!liveReady || !socket) {
          history.push({
            role: 'assistant',
            content: 'Live support is offline right now. Please try again shortly.',
            time: new Date().toISOString()
          });
          render();
          return;
        }
      }
      socket.emit('customer_message', {
        room_id: roomId,
        name: displayName,
        message: text
      });
    };

    send.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendMessage();
    });

    inputWrap.appendChild(input);
    inputWrap.appendChild(send);

    panel.appendChild(header);
    panel.appendChild(messages);
    panel.appendChild(inputWrap);
    root.appendChild(panel);

    const msgBox = root.querySelector('.psc-chatbot-messages');
    if (msgBox) msgBox.scrollTop = msgBox.scrollHeight;

    if (!liveReady) {
      initLiveChat();
    }
  };

  render();
})();
