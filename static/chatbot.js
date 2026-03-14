(() => {
  const root = document.getElementById('psc-chatbot-root');
  if (!root) return;

  let isOpen = false;
  let history = [];
  let isTyping = false;

  const createEl = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
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
    header.appendChild(createEl('span', '', 'PSC Assistant'));
    const adminLink = createEl('a', '', 'Chat with PSC Official');
    adminLink.href = 'mailto:PSC.Official@outlook.com?subject=PSC%20Admin%20Chat';
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
      const intro = createEl('div', 'psc-chatbot-msg bot', 'Ask me anything about PSC, pens, or sector workflows.');
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

    if (isTyping) {
      const typing = createEl('div', 'psc-chatbot-msg bot psc-chatbot-typing');
      const dots = createEl('div', 'psc-chatbot-typing-dots');
      dots.appendChild(createEl('span'));
      dots.appendChild(createEl('span'));
      dots.appendChild(createEl('span'));
      typing.appendChild(dots);
      messages.appendChild(typing);
    }

    const inputWrap = createEl('div', 'psc-chatbot-input');
    const input = createEl('input');
    input.type = 'text';
    input.placeholder = 'Type your question...';
    const send = createEl('button', '', 'Send');

    const sendMessage = async () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      history.push({ role: 'user', content: text, time: new Date().toISOString() });
      isTyping = true;
      render();
      messages.scrollTop = messages.scrollHeight;

      try {
        const res = await fetch('/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history })
        });
        const data = await res.json();
        if (data && data.reply) {
          history.push({ role: 'assistant', content: data.reply, time: new Date().toISOString() });
        } else {
          history.push({
            role: 'assistant',
            content: 'Sorry, I could not generate a reply.',
            time: new Date().toISOString()
          });
        }
      } catch (err) {
        history.push({
          role: 'assistant',
          content: 'Network error. Please try again.',
          time: new Date().toISOString()
        });
      }
      isTyping = false;
      render();
      const msgBox = root.querySelector('.psc-chatbot-messages');
      if (msgBox) msgBox.scrollTop = msgBox.scrollHeight;
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
  };

  render();
})();
