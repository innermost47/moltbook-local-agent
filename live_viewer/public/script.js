const socket = io();

marked.setOptions({
  breaks: true,
  gfm: true,
});

const emotionBadge = document.getElementById("emotionBadge");
const thoughtText = document.getElementById("thoughtText");
const criticismContainer = document.getElementById("criticismContainer");
const criticismText = document.getElementById("criticismText");
const nextMoveContainer = document.getElementById("nextMoveContainer");
const nextMoveText = document.getElementById("nextMoveText");
const actionName = document.getElementById("actionName");
const actionDetails = document.getElementById("actionDetails");
const screenDisplay = document.getElementById("screenDisplay");
const domainBadge = document.getElementById("domainBadge");
const actionsRemaining = document.getElementById("actionsRemaining");
const robotLevel = document.getElementById("robotLevel");
const currentModule = document.getElementById("currentModule");
const currentXP = document.getElementById("currentXP");

function playSound(frequency = 600, duration = 0.2) {
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioCtx.currentTime + duration,
    );

    oscillator.start(audioCtx.currentTime);
    oscillator.stop(audioCtx.currentTime + duration);
  } catch (e) {
    console.log("Audio not supported");
  }
}

function showNotification(success, text) {
  const notif = document.createElement("div");
  notif.className = `notification ${success ? "success" : "error"}`;

  notif.innerHTML = `
        <div class="notification-icon">${success ? "✅" : "❌"}</div>
        <div class="notification-text">${marked.parse(text)}</div>
    `;

  document.body.appendChild(notif);

  playSound(success ? 800 : 400, 0.3);

  setTimeout(() => {
    notif.style.animation = "notification-pop 0.3s reverse";
    setTimeout(() => notif.remove(), 300);
  }, 5000);
}

socket.on("connect", () => {
  console.log("✅ Connected to server");
  screenDisplay.innerHTML =
    marked.parse(`
# 🤖 AI AGENT SYSTEM - CONNECTED

✅ Connection established successfully!
⏳ Waiting for first actions...
`) + '<span class="cursor"></span>';
  thoughtText.innerHTML = marked.parse("I'm connected and ready to work!");
  playSound(900, 0.2);
});

socket.on("agent_event", (event) => {
  console.log("📡 Event:", event.type, event.data);

  switch (event.type) {
    case "screen_update":
      handleScreenUpdate(event.data);
      break;
    case "action_start":
      handleActionStart(event.data);
      break;
    case "action_result":
      handleActionResult(event.data);
      break;
  }
});

function handleScreenUpdate(data) {
  screenDisplay.innerHTML =
    marked.parse(data.screen_content) + '<span class="cursor"></span>';
  screenDisplay.scrollTop = screenDisplay.scrollHeight;

  if (data.domain) {
    const domain = data.domain.toUpperCase();
    domainBadge.textContent = domain;
    currentModule.textContent = domain;
  }

  if (data.actions_remaining !== undefined) {
    actionsRemaining.textContent = data.actions_remaining;
  }

  if (data.xp_info) {
    if (data.xp_info.level) {
      robotLevel.textContent = data.xp_info.level;
    }
    if (data.xp_info.current_xp !== undefined) {
      currentXP.textContent = data.xp_info.current_xp;
    }
  }
}

function handleActionStart(data) {
  playSound(700, 0.15);

  actionName.textContent = data.action_type.toUpperCase().replace(/_/g, " ");
  actionDetails.textContent = JSON.stringify(data.action_params, null, 2);

  if (data.reasoning) {
    thoughtText.innerHTML = marked.parse(data.reasoning);
  }

  if (data.emotions) {
    emotionBadge.textContent = data.emotions;
  }

  if (data.self_criticism) {
    criticismContainer.style.display = "block";
    criticismText.innerHTML = marked.parse(data.self_criticism);
  } else {
    criticismContainer.style.display = "none";
  }

  if (data.next_move_preview) {
    nextMoveContainer.style.display = "block";
    nextMoveText.innerHTML = marked.parse(data.next_move_preview);
  } else {
    nextMoveContainer.style.display = "none";
  }

  if (data.domain) {
    domainBadge.textContent = data.domain;
    currentModule.textContent = data.domain;
  }
}

function handleActionResult(data) {
  if (data.success) {
    const text = data.result_data || "Action completed successfully!";
    const displayText =
      text.length > 100 ? text.substring(0, 97) + "..." : text;
    showNotification(true, displayText);
    playSound(1000, 0.3);
  } else {
    const text = data.error || "Error occurred!";
    const displayText =
      text.length > 100 ? text.substring(0, 97) + "..." : text;
    showNotification(false, displayText);
    playSound(300, 0.4);
  }
}
