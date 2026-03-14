(() => {
  const root = document.getElementById('psc-chatbot-root');
  if (!root) return;

  let isOpen = false;
  let history = [];

  const createEl = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
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
      bubble.textContent = msg.content;
      messages.appendChild(bubble);
    });

    const inputWrap = createEl('div', 'psc-chatbot-input');
    const input = createEl('input');
    input.type = 'text';
    input.placeholder = 'Type your question...';
    const send = createEl('button', '', 'Send');

    const sendMessage = async () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      history.push({ role: 'user', content: text });
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
          history.push({ role: 'assistant', content: data.reply });
        } else {
          history.push({ role: 'assistant', content: 'Sorry, I could not generate a reply.' });
        }
      } catch (err) {
        history.push({ role: 'assistant', content: 'Network error. Please try again.' });
      }
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
