(() => {
  const root = document.querySelector("[data-hjchat]");
  if (!root || typeof io === "undefined") {
    return;
  }

  const displayName = root.dataset.displayName || "Guest";
  const logEl = document.getElementById("hjchat-log");
  const formEl = document.getElementById("hjchat-form");
  const inputEl = document.getElementById("hjchat-input");

  const socket = io({
    transports: ["websocket", "polling"],
  });

  const makeTime = () => {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  const appendSystem = (message) => {
    if (!logEl || !message) {
      return;
    }
    const bubble = document.createElement("div");
    bubble.className = "wa-system";
    bubble.textContent = message;
    logEl.appendChild(bubble);
    logEl.scrollTop = logEl.scrollHeight;
  };

  const appendMessage = ({ sender, message, timestamp }) => {
    if (!logEl || !message) {
      return;
    }

    const mine = sender === displayName;
    const bubble = document.createElement("div");
    bubble.className = `wa-message ${mine ? "me" : "other"}`;

    if (!mine) {
      const senderEl = document.createElement("strong");
      senderEl.className = "wa-sender";
      senderEl.textContent = sender || "Guest";
      bubble.appendChild(senderEl);
    }

    const textEl = document.createElement("div");
    textEl.textContent = message;
    bubble.appendChild(textEl);

    const timeEl = document.createElement("small");
    timeEl.className = "wa-time";
    timeEl.textContent = timestamp || makeTime();
    bubble.appendChild(timeEl);

    logEl.appendChild(bubble);
    logEl.scrollTop = logEl.scrollHeight;
  };

  socket.on("connect", () => {
    socket.emit("hjchat_join", {
      name: displayName,
    });
  });

  socket.on("hjchat_history", (payload) => {
    if (!payload || !Array.isArray(payload.messages)) {
      return;
    }
    logEl.innerHTML = "";
    payload.messages.forEach((entry) => appendMessage(entry || {}));
  });

  socket.on("hjchat_system", (payload) => {
    if (payload?.message) {
      appendSystem(payload.message);
    }
  });

  socket.on("hjchat_message", (payload) => {
    appendMessage(payload || {});
  });

  socket.on("hjchat_error", (payload) => {
    appendSystem(payload?.message || "Unable to join chat.");
  });

  if (formEl) {
    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = (inputEl?.value || "").trim();
      if (!message) {
        return;
      }
      socket.emit("hjchat_message", {
        name: displayName,
        message,
      });
      inputEl.value = "";
      inputEl.focus();
    });
  }
})();
