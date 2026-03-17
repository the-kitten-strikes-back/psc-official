(() => {
  const root = document.querySelector("[data-support-chat]");
  if (!root || typeof io === "undefined") {
    return;
  }

  const roomId = root.dataset.roomId;
  const displayName = root.dataset.displayName || "Guest";
  const logEl = document.getElementById("support-chat-log");
  const formEl = document.getElementById("support-chat-form");
  const inputEl = document.getElementById("support-chat-input");

  const socket = io({
    transports: ["websocket", "polling"],
  });

  const appendMessage = (sender, message) => {
    if (!logEl) {
      return;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "chat-message";
    const senderEl = document.createElement("strong");
    senderEl.textContent = sender;
    const textEl = document.createElement("div");
    textEl.textContent = message;
    wrapper.appendChild(senderEl);
    wrapper.appendChild(textEl);
    logEl.appendChild(wrapper);
    logEl.scrollTop = logEl.scrollHeight;
  };

  socket.on("connect", () => {
    socket.emit("customer_join", {
      room_id: roomId,
      name: displayName,
    });
  });

  socket.on("chat_system", (payload) => {
    if (payload && payload.message) {
      appendMessage("PSC", payload.message);
    }
  });

  socket.on("chat_message", (payload) => {
    if (payload && payload.message) {
      appendMessage(payload.sender || "PSC", payload.message);
    }
  });

  if (formEl) {
    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = (inputEl?.value || "").trim();
      if (!message) {
        return;
      }
      socket.emit("customer_message", {
        room_id: roomId,
        name: displayName,
        message,
      });
      inputEl.value = "";
      inputEl.focus();
    });
  }
})();
