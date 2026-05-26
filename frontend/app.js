const state = {
  apiBase: "http://127.0.0.1:8000",
  currentRun: null,
  websocket: null,
};

const elements = {
  form: document.querySelector("#run-form"),
  apiBase: document.querySelector("#api-base"),
  task: document.querySelector("#task"),
  modelProfile: document.querySelector("#model-profile"),
  apiStatus: document.querySelector("#api-status"),
  apiStatusLabel: document.querySelector("#api-status-label"),
  runTitle: document.querySelector("#run-title"),
  runStatus: document.querySelector("#run-status"),
  runModel: document.querySelector("#run-model"),
  eventCount: document.querySelector("#event-count"),
  wsStatus: document.querySelector("#ws-status"),
  lastEvent: document.querySelector("#last-event"),
  artifactCount: document.querySelector("#artifact-count"),
  eventsList: document.querySelector("#events-list"),
  artifactsList: document.querySelector("#artifacts-list"),
  refreshRun: document.querySelector("#refresh-run"),
  cancelRun: document.querySelector("#cancel-run"),
  eventTemplate: document.querySelector("#event-template"),
  artifactTemplate: document.querySelector("#artifact-template"),
};

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await createRun();
});

elements.refreshRun.addEventListener("click", async () => {
  if (state.currentRun) {
    await loadRun(state.currentRun.id);
  }
});

elements.cancelRun.addEventListener("click", async () => {
  if (!state.currentRun) {
    return;
  }

  const response = await apiFetch(`/runs/${state.currentRun.id}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason: "Cancelled from dashboard." }),
  });
  state.currentRun = response;
  renderRun(response);
  await refreshRunDetails(response.id);
});

window.addEventListener("beforeunload", () => {
  closeWebSocket();
});

checkHealth();

async function createRun() {
  const task = elements.task.value.trim();
  if (!task) {
    elements.task.focus();
    return;
  }

  const run = await apiFetch("/runs", {
    method: "POST",
    body: JSON.stringify({
      task,
      model_profile: elements.modelProfile.value,
    }),
  });

  state.currentRun = run;
  renderRun(run);
  await refreshRunDetails(run.id);
  connectWebSocket(run.id);
}

async function loadRun(runId) {
  const run = await apiFetch(`/runs/${runId}`);
  state.currentRun = run;
  renderRun(run);
  await refreshRunDetails(run.id);
}

async function refreshRunDetails(runId) {
  const [events, artifacts] = await Promise.all([
    apiFetch(`/runs/${runId}/events`),
    apiFetch(`/runs/${runId}/artifacts`),
  ]);
  renderEvents(events);
  renderArtifacts(artifacts);
}

async function checkHealth() {
  try {
    const health = await apiFetch("/health");
    setApiStatus("ok", `${health.app_name} connected`);
  } catch (error) {
    setApiStatus("error", "API offline");
  }
}

async function apiFetch(path, options = {}) {
  state.apiBase = elements.apiBase.value.replace(/\/$/, "");
  const response = await fetch(`${state.apiBase}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

function connectWebSocket(runId) {
  closeWebSocket();

  const url = new URL(state.apiBase);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/runs/${runId}/events/ws`;

  state.websocket = new WebSocket(url.toString());
  elements.wsStatus.textContent = "Connecting";

  state.websocket.addEventListener("open", () => {
    elements.wsStatus.textContent = "Open";
  });

  state.websocket.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    elements.lastEvent.textContent = message.type || "stream update";
  });

  state.websocket.addEventListener("close", () => {
    elements.wsStatus.textContent = "Closed";
  });

  state.websocket.addEventListener("error", () => {
    elements.wsStatus.textContent = "Error";
  });
}

function closeWebSocket() {
  if (state.websocket) {
    state.websocket.close();
    state.websocket = null;
  }
}

function renderRun(run) {
  elements.runTitle.textContent = run.task;
  elements.runStatus.textContent = run.status;
  elements.runModel.textContent = run.model_profile;
  elements.refreshRun.disabled = false;
  elements.cancelRun.disabled = ["completed", "failed", "cancelled"].includes(run.status);
}

function renderEvents(events) {
  elements.eventsList.replaceChildren();
  elements.eventCount.textContent = String(events.length);

  if (events.length === 0) {
    elements.lastEvent.textContent = "No events";
    return;
  }

  elements.lastEvent.textContent = events[events.length - 1].type;

  for (const event of events) {
    const node = elements.eventTemplate.content.cloneNode(true);
    node.querySelector(".event-type").textContent = event.type;
    node.querySelector(".event-message").textContent = event.message;
    node.querySelector(".event-time").textContent = formatDate(event.created_at);
    elements.eventsList.append(node);
  }
}

function renderArtifacts(artifacts) {
  elements.artifactsList.replaceChildren();
  elements.artifactCount.textContent = String(artifacts.length);

  for (const artifact of artifacts) {
    const node = elements.artifactTemplate.content.cloneNode(true);
    node.querySelector(".artifact-kind").textContent = artifact.kind;
    node.querySelector(".artifact-path").textContent = artifact.path;
    elements.artifactsList.append(node);
  }
}

function setApiStatus(status, label) {
  elements.apiStatus.className = `status-dot status-${status}`;
  elements.apiStatusLabel.textContent = label;
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}
