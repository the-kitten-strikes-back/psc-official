(() => {
  const root = document.querySelector("[data-sobab-chat]");
  if (!root || typeof io === "undefined") {
    return;
  }

  const roomsEl = document.getElementById("sobab-rooms");
  const logEl = document.getElementById("sobab-chat-log");
  const formEl = document.getElementById("sobab-chat-form");
  const inputEl = document.getElementById("sobab-chat-input");

  let activeRoomId = null;
  const rooms = new Map();
  const messagesByRoom = new Map();

  const socket = io({
    transports: ["websocket", "polling"],
  });

  const renderRooms = () => {
    if (!roomsEl) {
      return;
    }
    roomsEl.innerHTML = "";
    if (!rooms.size) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "No active chats yet.";
      roomsEl.appendChild(empty);
      return;
    }
    rooms.forEach((room) => {
      const card = document.createElement("div");
      card.className = "chat-room" + (room.room_id === activeRoomId ? " active" : "");
      card.textContent = room.name || "Guest";
      card.addEventListener("click", () => {
        activeRoomId = room.room_id;
        renderRooms();
        renderMessages();
      });
      roomsEl.appendChild(card);
    });
  };

  const renderMessages = () => {
    if (!logEl) {
      return;
    }
    logEl.innerHTML = "";
    if (!activeRoomId) {
      const empty = document.createElement("div");
      empty.className = "muted";
      empty.textContent = "Select a chat to begin responding.";
      logEl.appendChild(empty);
      return;
    }
    const messages = messagesByRoom.get(activeRoomId) || [];
    messages.forEach((message) => {
      const wrapper = document.createElement("div");
      wrapper.className = "chat-message";
      const senderEl = document.createElement("strong");
      senderEl.textContent = message.sender;
      const textEl = document.createElement("div");
      textEl.textContent = message.message;
      wrapper.appendChild(senderEl);
      wrapper.appendChild(textEl);
      logEl.appendChild(wrapper);
    });
    logEl.scrollTop = logEl.scrollHeight;
  };

  const storeMessage = (roomId, sender, message) => {
    if (!messagesByRoom.has(roomId)) {
      messagesByRoom.set(roomId, []);
    }
    messagesByRoom.get(roomId).push({ sender, message });
  };

  socket.on("connect", () => {
    socket.emit("sobab_join");
  });

  socket.on("sobab_rooms", (payload) => {
    const incoming = payload?.rooms || [];
    incoming.forEach((room) => {
      rooms.set(room.room_id, room);
    });
    if (!activeRoomId && incoming.length) {
      activeRoomId = incoming[0].room_id;
    }
    renderRooms();
    renderMessages();
  });

  socket.on("sobab_room_update", (payload) => {
    if (!payload?.room_id) {
      return;
    }
    rooms.set(payload.room_id, payload);
    if (!activeRoomId) {
      activeRoomId = payload.room_id;
    }
    renderRooms();
  });

  socket.on("sobab_message", (payload) => {
    if (!payload?.room_id || !payload.message) {
      return;
    }
    const sender = payload.sender || "Customer";
    storeMessage(payload.room_id, sender, payload.message);
    if (payload.room_id === activeRoomId) {
      renderMessages();
    }
  });

  socket.on("sobab_error", (payload) => {
    if (!logEl) {
      return;
    }
    logEl.innerHTML = "";
    const error = document.createElement("div");
    error.className = "muted";
    error.textContent = payload?.message || "Unable to join SoBAB chat.";
    logEl.appendChild(error);
  });

  if (formEl) {
    formEl.addEventListener("submit", (event) => {
      event.preventDefault();
      const message = (inputEl?.value || "").trim();
      if (!message || !activeRoomId) {
        return;
      }
      socket.emit("sobab_message", {
        room_id: activeRoomId,
        message,
      });
      inputEl.value = "";
      inputEl.focus();
    });
  }
})();
