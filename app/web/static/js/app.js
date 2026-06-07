const ids = ["hardware","ferrumMode","port","baud","netHost","netPort","netUuid","pattern","amplitude","delay","verticalPressureEnabled","pressureAmplitude","pressureDelay","triggerMode","triggerButton"];
const elements = Object.fromEntries(ids.map(id => [id, document.getElementById(id)]));
const language = document.getElementById("language");
const saveButton = document.getElementById("saveConfig");
const formState = document.getElementById("formState");
let state = {};
let applying = false;
let initialized = false;
let dirty = false;

function strings() {
  return window.WEB_I18N[language.value] || window.WEB_I18N.en;
}

function translate(code) {
  const values = window.WEB_I18N[code] || window.WEB_I18N.en;
  document.documentElement.lang = code.replace("_", "-");
  document.querySelectorAll("[data-i18n]").forEach(node => {
    const value = values[node.dataset.i18n];
    if (value) node.textContent = value;
  });
  renderDirtyState();
}

function setValue(element, value) {
  if (value !== undefined && value !== null) element.value = String(value);
}

function populateForm(next) {
  applying = true;
  setValue(language, next.language || "en");
  translate(language.value);
  setValue(elements.hardware, next.hardware);
  setValue(elements.ferrumMode, next.ferrum_mode || "serial");
  elements.port.innerHTML = "";
  (next.ports || []).forEach(port => {
    const option = document.createElement("option");
    option.value = port.device;
    option.textContent = `${port.device} · ${port.description}`;
    elements.port.appendChild(option);
  });
  setValue(elements.port, next.com_port);
  setValue(elements.baud, next.baud_rate);
  setValue(elements.netHost, next.net_host);
  setValue(elements.netPort, next.net_port);
  setValue(elements.netUuid, next.net_uuid);
  setValue(elements.pattern, next.pattern);
  setValue(elements.amplitude, next.amplitude);
  setValue(elements.delay, next.delay_ms);
  elements.verticalPressureEnabled.checked = Boolean(next.vertical_pressure_enabled);
  setValue(elements.pressureAmplitude, next.vertical_pressure_amplitude);
  setValue(elements.pressureDelay, next.vertical_pressure_delay_ms);
  setValue(elements.triggerMode, next.trigger_mode);
  setValue(elements.triggerButton, next.trigger_button);
  applying = false;
  initialized = true;
  dirty = false;
  updateConnectionFields();
  updatePressureFields();
  renderDirtyState();
}

function updateConnectionFields() {
  const ferrum = elements.hardware.value === "ferrum";
  const net = ferrum && elements.ferrumMode.value === "net";
  document.getElementById("modeField").classList.toggle("field-hidden", !ferrum);
  document.getElementById("serialPortField").classList.toggle("field-hidden", net);
  document.getElementById("baudField").classList.toggle("field-hidden", net);
  document.getElementById("netHostField").classList.toggle("field-hidden", !net);
  document.getElementById("netPortField").classList.toggle("field-hidden", !net);
  document.getElementById("netUuidField").classList.toggle("field-hidden", !net);
}

function updatePressureFields() {
  const enabled = elements.verticalPressureEnabled.checked;
  elements.pressureAmplitude.disabled = !enabled;
  elements.pressureDelay.disabled = !enabled;
}

function updateLiveStatus(next) {
  state = next;
  applyTheme(next.web_theme);
  document.getElementById("connectionStatus").textContent = next.connection_status || "Offline";
  document.getElementById("runStatus").textContent = next.run_status || "Idle";
  const text = strings();
  document.getElementById("connectAction").textContent = next.connected ? text.disconnect : text.connect;
  document.getElementById("startAction").textContent = next.armed ? text.stop : text.start;
}

function applyTheme(theme) {
  if (!theme) return;
  const root = document.documentElement.style;
  if (theme.background) root.setProperty("--bg", theme.background);
  if (theme.panel) root.setProperty("--panel", theme.panel);
  if (theme.text) root.setProperty("--text", theme.text);
  if (theme.muted) root.setProperty("--muted", theme.muted);
  if (theme.accent) {
    root.setProperty("--cyan", theme.accent);
    root.setProperty("--blue", theme.accent);
  }
}

function renderDirtyState(mode = "") {
  const text = strings();
  saveButton.classList.toggle("dirty", dirty);
  saveButton.disabled = !dirty || mode === "saving";
  if (mode === "saving") formState.textContent = text.saving;
  else if (mode === "saved") formState.textContent = text.saved;
  else formState.textContent = dirty ? text.unsaved : text.noChanges;
}

function markDirty() {
  if (applying) return;
  dirty = true;
  renderDirtyState();
}

async function loadState() {
  try {
    const response = await fetch("/api/state", {cache: "no-store"});
    const next = await response.json();
    if (!initialized) populateForm(next);
    updateLiveStatus(next);
  } catch (_) {
    document.getElementById("connectionStatus").textContent = "WebUI offline";
  }
}

async function saveConfig() {
  if (!dirty) return;
  renderDirtyState("saving");
  await fetch("/api/config", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({
      language: language.value,
      hardware: elements.hardware.value,
      ferrum_mode: elements.ferrumMode.value,
      com_port: elements.port.value,
      baud_rate: Number(elements.baud.value),
      net_host: elements.netHost.value,
      net_port: Number(elements.netPort.value),
      net_uuid: elements.netUuid.value,
      pattern: elements.pattern.value,
      amplitude: Number(elements.amplitude.value),
      delay_ms: Number(elements.delay.value),
      vertical_pressure_enabled: elements.verticalPressureEnabled.checked,
      vertical_pressure_amplitude: Number(elements.pressureAmplitude.value),
      vertical_pressure_delay_ms: Number(elements.pressureDelay.value),
      trigger_mode: elements.triggerMode.value,
      trigger_button: Number(elements.triggerButton.value)
    })
  });
  dirty = false;
  renderDirtyState("saved");
  setTimeout(loadState, 160);
}

language.addEventListener("change", () => {
  translate(language.value);
  markDirty();
});
ids.forEach(id => elements[id].addEventListener("change", () => {
  if (id === "hardware" || id === "ferrumMode") updateConnectionFields();
  if (id === "verticalPressureEnabled") updatePressureFields();
  markDirty();
}));
elements.amplitude.addEventListener("input", markDirty);
elements.delay.addEventListener("input", markDirty);
elements.pressureAmplitude.addEventListener("input", markDirty);
elements.pressureDelay.addEventListener("input", markDirty);
elements.netHost.addEventListener("input", markDirty);
elements.netPort.addEventListener("input", markDirty);
elements.netUuid.addEventListener("input", markDirty);
saveButton.addEventListener("click", saveConfig);

document.getElementById("connectAction").addEventListener("click", async () => {
  await fetch("/api/action", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({action:state.connected?"disconnect":"connect"})
  });
  setTimeout(loadState, 180);
});
document.getElementById("startAction").addEventListener("click", async () => {
  await fetch("/api/action", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({action:state.armed?"stop":"start"})
  });
  setTimeout(loadState, 180);
});

loadState();
setInterval(loadState, 750);
