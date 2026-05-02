const state = {
  config: null,
  capabilities: null,
  presets: [],
};

const $ = (selector) => document.querySelector(selector);
const messageBox = () => $("#message");

function showMessage(text, type = "info") {
  const box = messageBox();
  box.textContent = text;
  box.className = `message ${type}`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : response.statusText;
    throw new Error(detail);
  }
  return data;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function slug(value) {
  const cleaned = String(value || "rule")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return cleaned || "rule";
}

function uniqueRuleId(base) {
  const existing = new Set((state.config?.rules || []).map((rule) => rule.id));
  let candidate = slug(base);
  let suffix = 2;
  while (existing.has(candidate)) {
    candidate = `${slug(base)}_${suffix}`;
    suffix += 1;
  }
  return candidate;
}

function gestureOptions(selected) {
  const gestures = state.capabilities?.gestures || {};
  return Object.entries(gestures)
    .map(([key, meta]) => {
      const label = `${key} — ${meta.label || key}`;
      return `<option value="${escapeHtml(key)}" ${key === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function kindOptions(kinds, selected) {
  return (kinds || [])
    .map((kind) => `<option value="${escapeHtml(kind)}" ${kind === selected ? "selected" : ""}>${escapeHtml(kind)}</option>`)
    .join("");
}

function numberValue(value, fallback = 0) {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function defaultTrigger(kind) {
  if (kind === "sequence") {
    return {
      kind,
      steps: [
        { gesture: "OPEN_PALM", hold_ms: 250 },
        { gesture: "FIST", hold_ms: 250 },
      ],
      max_total_ms: 6000,
      max_gap_ms: 1800,
    };
  }
  if (kind === "repeat_hold") {
    return { kind, gesture: "THUMB_UP", hold_ms: 900, repeat_ms: 900 };
  }
  if (kind === "armed_hold") {
    return {
      kind,
      arm_gesture: "FIST",
      gesture: "THUMB_UP",
      arm_timeout_ms: 8000,
      hold_ms: 600,
      repeat_ms: 900,
    };
  }
  if (kind === "motion") {
    return { kind, gesture: "SWIPE_UP" };
  }
  if (kind === "value_control") {
    return { kind, gesture: "PEACE", repeat_ms: 250 };
  }
  return { kind: "hold", gesture: "OPEN_PALM", hold_ms: 1000 };
}

function defaultAction(kind) {
  if (kind === "workflow.enter_command_mode") {
    return { kind, duration_ms: 10000 };
  }
  if (kind === "virtual_lamp.brightness_step") {
    return { kind, direction: 1, step_percent: 10 };
  }
  if (kind === "virtual_lamp.brightness_set") {
    return { kind, percent: 50 };
  }
  if (kind === "virtual_lamp.color_set") {
    return { kind, rgb: [255, 255, 255] };
  }
  return { kind };
}

function defaultSafety() {
  return {
    cooldown_ms: 1000,
    command_mode: { required: true },
    confirmation: { required: false, gesture: "TWO_THUMBS_UP", timeout_ms: 4000 },
  };
}

function defaultRule() {
  const id = uniqueRuleId("new_rule");
  return {
    id,
    name: "New rule",
    enabled: true,
    trigger: defaultTrigger("hold"),
    action: defaultAction("virtual_lamp.toggle"),
    safety: defaultSafety(),
  };
}

function ensureRuleShape(rule) {
  rule.enabled = rule.enabled !== false;
  rule.trigger ||= defaultTrigger("hold");
  rule.action ||= defaultAction("virtual_lamp.toggle");
  rule.safety ||= {};
  rule.safety.cooldown_ms ??= 0;
  rule.safety.command_mode ||= { required: false };
  rule.safety.confirmation ||= { required: false, gesture: "TWO_THUMBS_UP", timeout_ms: 4000 };
}

function renderPresetList() {
  const presets = state.presets || [];
  $("#presets").innerHTML = presets
    .map((preset, index) => `
      <article class="preset-card">
        <strong>${escapeHtml(preset.name)}</strong>
        <p>${escapeHtml(preset.description || "")}</p>
        <button type="button" data-op="add-preset" data-preset="${index}">Add preset</button>
      </article>
    `)
    .join("");
}

function renderCapabilities() {
  const catalog = state.capabilities || {};
  const gestures = catalog.gestures || {};
  $("#capabilities").innerHTML = `
    <details>
      <summary>Available gestures (${Object.keys(gestures).length})</summary>
      <div class="chip-list">
        ${Object.entries(gestures)
          .map(([key, meta]) => `<span class="chip" title="${escapeHtml(meta.description || "")}">${escapeHtml(key)}</span>`)
          .join("")}
      </div>
    </details>
    <details>
      <summary>Trigger blocks</summary>
      <div class="chip-list">${(catalog.trigger_kinds || []).map((kind) => `<span class="chip">${escapeHtml(kind)}</span>`).join("")}</div>
    </details>
    <details>
      <summary>Action blocks</summary>
      <div class="chip-list">${(catalog.action_kinds || []).map((kind) => `<span class="chip">${escapeHtml(kind)}</span>`).join("")}</div>
    </details>
  `;
}

function renderTriggerFields(rule, index) {
  const trigger = rule.trigger || defaultTrigger("hold");
  const kind = trigger.kind || "hold";
  if (kind === "sequence") {
    const steps = trigger.steps || [];
    return `
      <div class="field-row">
        <label>Max total ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="max_total_ms" value="${numberValue(trigger.max_total_ms, 6000)}"></label>
        <label>Max gap ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="max_gap_ms" value="${numberValue(trigger.max_gap_ms, 1800)}"></label>
      </div>
      <div class="steps">
        ${steps
          .map((step, stepIndex) => `
            <div class="step-row">
              <span class="step-index">${stepIndex + 1}</span>
              <select data-scope="step" data-index="${index}" data-step="${stepIndex}" data-field="gesture">${gestureOptions(step.gesture)}</select>
              <input type="number" min="0" data-scope="step" data-index="${index}" data-step="${stepIndex}" data-field="hold_ms" value="${numberValue(step.hold_ms, 0)}" title="Hold time in ms">
              <button type="button" data-op="remove-step" data-index="${index}" data-step="${stepIndex}">Remove</button>
            </div>
          `)
          .join("")}
      </div>
      <button type="button" data-op="add-step" data-index="${index}">Add sequence step</button>
    `;
  }

  if (kind === "armed_hold") {
    return `
      <div class="field-row">
        <label>Arm gesture <select data-scope="trigger" data-index="${index}" data-field="arm_gesture">${gestureOptions(trigger.arm_gesture)}</select></label>
        <label>Target gesture <select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select></label>
      </div>
      <div class="field-row">
        <label>Arm timeout ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="arm_timeout_ms" value="${numberValue(trigger.arm_timeout_ms, 8000)}"></label>
        <label>First hold ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 600)}"></label>
        <label>Repeat ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 900)}"></label>
      </div>
    `;
  }

  if (kind === "repeat_hold") {
    return `
      <div class="field-row">
        <label>Gesture <select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select></label>
        <label>First hold ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 900)}"></label>
        <label>Repeat ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 900)}"></label>
      </div>
    `;
  }

  if (kind === "value_control") {
    return `
      <div class="field-row">
        <label>Gesture <select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select></label>
        <label>Repeat ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 250)}"></label>
      </div>
    `;
  }

  if (kind === "motion") {
    return `
      <div class="field-row">
        <label>Motion gesture <select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select></label>
      </div>
    `;
  }

  return `
    <div class="field-row">
      <label>Gesture <select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select></label>
      <label>Hold ms <input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 1000)}"></label>
    </div>
  `;
}

function renderActionFields(rule, index) {
  const action = rule.action || defaultAction("virtual_lamp.toggle");
  const kind = action.kind;
  if (kind === "workflow.enter_command_mode") {
    return `<label>Duration ms <input type="number" min="0" data-scope="action" data-index="${index}" data-field="duration_ms" value="${numberValue(action.duration_ms, 10000)}"></label>`;
  }
  if (kind === "virtual_lamp.brightness_step") {
    return `
      <div class="field-row">
        <label>Direction
          <select data-scope="action" data-index="${index}" data-field="direction">
            <option value="1" ${numberValue(action.direction, 1) >= 0 ? "selected" : ""}>increase</option>
            <option value="-1" ${numberValue(action.direction, 1) < 0 ? "selected" : ""}>decrease</option>
          </select>
        </label>
        <label>Step % <input type="number" min="0" max="100" data-scope="action" data-index="${index}" data-field="step_percent" value="${numberValue(action.step_percent, 10)}"></label>
      </div>
    `;
  }
  if (kind === "virtual_lamp.brightness_set") {
    return `<label>Brightness % <input type="number" min="0" max="100" data-scope="action" data-index="${index}" data-field="percent" value="${numberValue(action.percent, 50)}"></label>`;
  }
  if (kind === "virtual_lamp.color_set") {
    const rgb = Array.isArray(action.rgb) ? action.rgb.join(",") : "";
    return `<label>RGB override <input type="text" data-scope="action" data-index="${index}" data-field="rgb" value="${escapeHtml(rgb)}" placeholder="leave empty for gesture value"></label>`;
  }
  return `<p class="muted">This action has no extra fields.</p>`;
}

function renderRule(rule, index) {
  ensureRuleShape(rule);
  const triggerKinds = state.capabilities?.trigger_kinds || [];
  const actionKinds = state.capabilities?.action_kinds || [];
  const confirmation = rule.safety.confirmation || { required: false };
  const commandMode = rule.safety.command_mode || { required: false };
  return `
    <article class="rule-card ${rule.enabled ? "" : "disabled"}">
      <div class="rule-top">
        <label class="switch"><input type="checkbox" data-scope="rule" data-index="${index}" data-field="enabled" ${rule.enabled ? "checked" : ""}> Enabled</label>
        <div class="rule-actions">
          <button type="button" data-op="duplicate-rule" data-index="${index}">Duplicate</button>
          <button type="button" class="danger" data-op="delete-rule" data-index="${index}">Delete</button>
        </div>
      </div>

      <div class="field-row">
        <label>Rule ID <input data-scope="rule" data-index="${index}" data-field="id" value="${escapeHtml(rule.id)}"></label>
        <label>Name <input data-scope="rule" data-index="${index}" data-field="name" value="${escapeHtml(rule.name || rule.id)}"></label>
      </div>

      <section class="block trigger-block">
        <h3>When</h3>
        <label>Trigger type <select data-scope="trigger-kind" data-index="${index}">${kindOptions(triggerKinds, rule.trigger.kind)}</select></label>
        ${renderTriggerFields(rule, index)}
      </section>

      <section class="block action-block">
        <h3>Do</h3>
        <label>Action <select data-scope="action-kind" data-index="${index}">${kindOptions(actionKinds, rule.action.kind)}</select></label>
        ${renderActionFields(rule, index)}
      </section>

      <section class="block safety-block">
        <h3>Safety</h3>
        <div class="field-row">
          <label>Cooldown ms <input type="number" min="0" data-scope="safety" data-index="${index}" data-field="cooldown_ms" value="${numberValue(rule.safety.cooldown_ms, 0)}"></label>
          <label class="switch"><input type="checkbox" data-scope="command-mode" data-index="${index}" ${commandMode.required ? "checked" : ""}> Require command mode</label>
        </div>
        <div class="field-row">
          <label class="switch"><input type="checkbox" data-scope="confirmation-required" data-index="${index}" ${confirmation.required ? "checked" : ""}> Require confirmation</label>
          <label>Confirm gesture <select data-scope="confirmation" data-index="${index}" data-field="gesture">${gestureOptions(confirmation.gesture || "TWO_THUMBS_UP")}</select></label>
          <label>Timeout ms <input type="number" min="0" data-scope="confirmation" data-index="${index}" data-field="timeout_ms" value="${numberValue(confirmation.timeout_ms, 4000)}"></label>
        </div>
      </section>
    </article>
  `;
}

function renderRules() {
  const rules = state.config?.rules || [];
  $("#rules").innerHTML = rules.map(renderRule).join("") || `<p class="empty">No rules yet. Add a blank rule or a preset.</p>`;
  $("#rule-count").textContent = `${rules.length} rules`;
}

function renderRaw() {
  $("#raw-json").value = JSON.stringify(state.config, null, 2);
}

function render() {
  renderPresetList();
  renderCapabilities();
  renderRules();
  renderRaw();
}

async function loadAll() {
  showMessage("Loading dashboard data...");
  const [capabilities, rules, presets] = await Promise.all([
    fetchJson("/api/capabilities"),
    fetchJson("/api/rules"),
    fetchJson("/api/presets"),
  ]);
  state.capabilities = capabilities;
  state.config = rules;
  state.presets = presets;
  render();
  showMessage("Loaded rules.", "ok");
}

async function saveRules() {
  const textarea = $("#raw-json");
  const config = JSON.parse(textarea.value);
  const saved = await fetchJson("/api/rules", {
    method: "PUT",
    body: JSON.stringify(config),
  });
  state.config = saved;
  render();
  showMessage("Saved rules.", "ok");
}

async function validateRules() {
  const config = JSON.parse($("#raw-json").value);
  await fetchJson("/api/rules/validate", {
    method: "POST",
    body: JSON.stringify(config),
  });
  showMessage("Rules are valid.", "ok");
}

async function resetRules() {
  if (!confirm("Reset editable rules to defaults?")) return;
  const reset = await fetchJson("/api/rules/reset", { method: "POST" });
  state.config = reset;
  render();
  showMessage("Rules reset to defaults.", "ok");
}

function syncRawOnly() {
  $("#raw-json").value = JSON.stringify(state.config, null, 2);
}

function updateNested(scope, element) {
  const index = Number(element.dataset.index);
  const rule = state.config.rules[index];
  const field = element.dataset.field;
  const value = element.type === "checkbox" ? element.checked : element.value;

  if (scope === "rule") {
    rule[field] = field === "enabled" ? element.checked : value;
  } else if (scope === "trigger") {
    rule.trigger[field] = element.type === "number" ? numberValue(value) : value;
  } else if (scope === "action") {
    if (field === "rgb") {
      const channels = value.split(",").map((part) => Number(part.trim())).filter((part) => Number.isFinite(part));
      if (channels.length === 3) rule.action.rgb = channels;
      else delete rule.action.rgb;
    } else {
      rule.action[field] = element.type === "number" || field === "direction" ? numberValue(value) : value;
    }
  } else if (scope === "safety") {
    rule.safety[field] = element.type === "number" ? numberValue(value) : value;
  } else if (scope === "confirmation") {
    rule.safety.confirmation ||= { required: false };
    rule.safety.confirmation[field] = element.type === "number" ? numberValue(value) : value;
  }
  syncRawOnly();
}

function handleChange(event) {
  const element = event.target;
  const scope = element.dataset.scope;
  if (!scope || !state.config) return;
  const index = Number(element.dataset.index);
  const rule = state.config.rules[index];

  if (scope === "trigger-kind") {
    rule.trigger = defaultTrigger(element.value);
    render();
    return;
  }
  if (scope === "action-kind") {
    rule.action = defaultAction(element.value);
    render();
    return;
  }
  if (scope === "step") {
    const stepIndex = Number(element.dataset.step);
    const field = element.dataset.field;
    rule.trigger.steps[stepIndex][field] = element.type === "number" ? numberValue(element.value) : element.value;
    syncRawOnly();
    return;
  }
  if (scope === "command-mode") {
    rule.safety.command_mode ||= { required: false };
    rule.safety.command_mode.required = element.checked;
    syncRawOnly();
    return;
  }
  if (scope === "confirmation-required") {
    rule.safety.confirmation ||= { required: false, gesture: "TWO_THUMBS_UP", timeout_ms: 4000 };
    rule.safety.confirmation.required = element.checked;
    syncRawOnly();
    return;
  }
  updateNested(scope, element);
}

function handleClick(event) {
  const button = event.target.closest("button[data-op]");
  if (!button || !state.config) return;
  const op = button.dataset.op;
  const index = Number(button.dataset.index);

  if (op === "add-rule") {
    state.config.rules.push(defaultRule());
    render();
  } else if (op === "delete-rule") {
    state.config.rules.splice(index, 1);
    render();
  } else if (op === "duplicate-rule") {
    const copy = clone(state.config.rules[index]);
    copy.id = uniqueRuleId(copy.id);
    copy.name = `${copy.name || copy.id} copy`;
    state.config.rules.splice(index + 1, 0, copy);
    render();
  } else if (op === "add-step") {
    state.config.rules[index].trigger.steps.push({ gesture: "OPEN_PALM", hold_ms: 250 });
    render();
  } else if (op === "remove-step") {
    const step = Number(button.dataset.step);
    state.config.rules[index].trigger.steps.splice(step, 1);
    render();
  } else if (op === "add-preset") {
    const preset = state.presets[Number(button.dataset.preset)];
    const rule = clone(preset.rule);
    rule.id = uniqueRuleId(rule.id);
    state.config.rules.push(rule);
    render();
  }
}

function bindToolbar() {
  $("#reload").addEventListener("click", () => loadAll().catch((error) => showMessage(error.message, "error")));
  $("#save").addEventListener("click", () => saveRules().catch((error) => showMessage(error.message, "error")));
  $("#validate").addEventListener("click", () => validateRules().catch((error) => showMessage(error.message, "error")));
  $("#reset").addEventListener("click", () => resetRules().catch((error) => showMessage(error.message, "error")));
  $("#format").addEventListener("click", () => {
    try {
      state.config = JSON.parse($("#raw-json").value);
      render();
      showMessage("Formatted JSON.", "ok");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
  document.addEventListener("change", handleChange);
  document.addEventListener("input", (event) => {
    if (event.target.matches("input[data-scope]")) handleChange(event);
  });
  document.addEventListener("click", handleClick);
}

bindToolbar();
loadAll().catch((error) => showMessage(error.message, "error"));
