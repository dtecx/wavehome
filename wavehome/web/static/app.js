const state = {
  config: null,
  capabilities: null,
  presets: [],
  selectedRuleId: null,
  view: "blocks",
};

const $ = (selector) => document.querySelector(selector);

function showMessage(text, type = "info") {
  const box = $("#message");
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

function numberValue(value, fallback = 0) {
  if (value === undefined || value === null || value === "") return fallback;
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function uniqueRuleId(base) {
  const existing = new Set((state.config?.rules || []).map((rule) => rule.id));
  const root = slug(base);
  let candidate = root;
  let suffix = 2;
  while (existing.has(candidate)) {
    candidate = `${root}_${suffix}`;
    suffix += 1;
  }
  return candidate;
}

function triggerMeta(kind) {
  return state.capabilities?.trigger_blocks?.[kind] || { label: kind, description: "" };
}

function actionMeta(kind) {
  return state.capabilities?.action_blocks?.[kind] || { label: kind, description: "" };
}

function gestureLabel(key) {
  const meta = state.capabilities?.gestures?.[key];
  return meta?.label || key || "gesture";
}

function gestureOptions(selected) {
  const gestures = state.capabilities?.gestures || {};
  return Object.entries(gestures)
    .map(([key, meta]) => {
      const label = `${meta.label || key} (${key})`;
      return `<option value="${escapeHtml(key)}" ${key === selected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function kindOptions(kinds, selected, metaReader) {
  return (kinds || [])
    .map((kind) => {
      const meta = metaReader(kind);
      return `<option value="${escapeHtml(kind)}" ${kind === selected ? "selected" : ""}>${escapeHtml(meta.label || kind)}</option>`;
    })
    .join("");
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
  if (kind === "smart_home.set_power") {
    return { kind, device_id: "replace-with-device-id", on: true };
  }
  if (kind === "smart_home.set_brightness") {
    return { kind, device_id: "replace-with-device-id", percent: 60 };
  }
  if (kind === "smart_home.set_color") {
    return { kind, device_id: "replace-with-device-id", rgb: [255, 255, 255] };
  }
  if (kind === "smart_home.activate_scene") {
    return { kind, scene_id: "replace-with-scene-id" };
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
  const id = uniqueRuleId("new_scenario");
  return {
    id,
    name: "New scenario",
    enabled: true,
    trigger: defaultTrigger("hold"),
    action: defaultAction("virtual_lamp.toggle"),
    safety: defaultSafety(),
  };
}

function ensureRuleShape(rule) {
  rule.id ||= uniqueRuleId(rule.name || "scenario");
  rule.name ||= rule.id;
  rule.enabled = rule.enabled !== false;
  rule.trigger ||= defaultTrigger("hold");
  rule.action ||= defaultAction("virtual_lamp.toggle");
  rule.safety ||= {};
  rule.safety.cooldown_ms ??= 0;
  rule.safety.command_mode ||= { required: false };
  rule.safety.confirmation ||= { required: false, gesture: "TWO_THUMBS_UP", timeout_ms: 4000 };
}

function selectedRule() {
  const rules = state.config?.rules || [];
  if (!rules.length) return null;
  return rules.find((rule) => rule.id === state.selectedRuleId) || rules[0];
}

function selectRule(ruleId) {
  state.selectedRuleId = ruleId;
  render();
}

function syncRawOnly() {
  if ($("#raw-json")) {
    $("#raw-json").value = JSON.stringify(state.config, null, 2);
  }
}

function triggerSummary(trigger) {
  if (!trigger) return "No trigger";

  if (trigger.kind === "sequence") {
    const steps = (trigger.steps || []).map((step) => gestureLabel(step.gesture)).join(" -> ");
    return steps || "Empty sequence";
  }

  if (trigger.kind === "armed_hold") {
    return `${gestureLabel(trigger.arm_gesture)} arms ${gestureLabel(trigger.gesture)}`;
  }

  if (trigger.kind === "repeat_hold") {
    return `${gestureLabel(trigger.gesture)} repeats`;
  }

  if (trigger.kind === "value_control") {
    return `${gestureLabel(trigger.gesture)} sends value`;
  }

  if (trigger.kind === "motion") {
    return gestureLabel(trigger.gesture);
  }

  return `${gestureLabel(trigger.gesture)} for ${numberValue(trigger.hold_ms, 0)} ms`;
}

function actionSummary(action) {
  if (!action) return "No action";
  const meta = actionMeta(action.kind);

  if (action.kind === "virtual_lamp.brightness_step") {
    return `${meta.label}: ${numberValue(action.direction, 1) > 0 ? "up" : "down"} ${numberValue(action.step_percent, 10)}%`;
  }

  if (action.kind === "virtual_lamp.brightness_set") {
    return `${meta.label}: ${numberValue(action.percent, 50)}%`;
  }

  if (action.kind === "smart_home.set_power") {
    return `${meta.label}: ${action.device_id || "device"} ${action.on === false ? "off" : "on"}`;
  }

  if (action.kind === "smart_home.set_brightness") {
    return `${meta.label}: ${action.device_id || "device"} ${numberValue(action.percent, 60)}%`;
  }

  if (action.kind === "smart_home.set_color") {
    return `${meta.label}: ${action.device_id || "device"}`;
  }

  if (action.kind === "smart_home.activate_scene") {
    return `${meta.label}: ${action.scene_id || "scene"}`;
  }

  return meta.label || action.kind;
}

function safetySummary(rule) {
  const safety = rule.safety || {};
  const chips = [];
  if (safety.command_mode?.required) chips.push("Command mode");
  if (safety.confirmation?.required) chips.push(`Confirm ${gestureLabel(safety.confirmation.gesture)}`);
  if (numberValue(safety.cooldown_ms, 0) > 0) chips.push(`${safety.cooldown_ms} ms cooldown`);
  return chips.length ? chips : ["Direct"];
}

function renderRuleCard(rule, index) {
  ensureRuleShape(rule);
  const isSelected = selectedRule()?.id === rule.id;
  const trigger = rule.trigger || {};
  const action = rule.action || {};
  return `
    <article class="scenario-card ${isSelected ? "selected" : ""} ${rule.enabled ? "" : "disabled"}" data-rule-id="${escapeHtml(rule.id)}">
      <button type="button" class="card-select" data-op="select-rule" data-rule-id="${escapeHtml(rule.id)}" aria-label="Select ${escapeHtml(rule.name)}"></button>
      <div class="scenario-card-head">
        <div>
          <p class="scenario-id">${escapeHtml(rule.id)}</p>
          <h3>${escapeHtml(rule.name || rule.id)}</h3>
        </div>
        <label class="switch inline"><input type="checkbox" data-scope="rule" data-index="${index}" data-field="enabled" ${rule.enabled ? "checked" : ""}> Enabled</label>
      </div>

      <div class="block-stack">
        <div class="logic-block when">
          <span class="block-label">When</span>
          <strong>${escapeHtml(triggerMeta(trigger.kind).label || trigger.kind)}</strong>
          <p>${escapeHtml(triggerSummary(trigger))}</p>
        </div>
        <div class="logic-block do">
          <span class="block-label">Do</span>
          <strong>${escapeHtml(actionMeta(action.kind).label || action.kind)}</strong>
          <p>${escapeHtml(actionSummary(action))}</p>
        </div>
        <div class="logic-block safe">
          <span class="block-label">Safe</span>
          <div class="chip-list compact">
            ${safetySummary(rule).map((chip) => `<span class="chip">${escapeHtml(chip)}</span>`).join("")}
          </div>
        </div>
      </div>

      <div class="card-actions">
        <button type="button" data-op="move-rule-up" data-index="${index}" ${index === 0 ? "disabled" : ""}>Up</button>
        <button type="button" data-op="move-rule-down" data-index="${index}" ${index === (state.config.rules.length - 1) ? "disabled" : ""}>Down</button>
        <button type="button" data-op="duplicate-rule" data-index="${index}">Duplicate</button>
        <button type="button" class="danger" data-op="delete-rule" data-index="${index}">Delete</button>
      </div>
    </article>
  `;
}

function renderRules() {
  const rules = state.config?.rules || [];
  const selected = selectedRule();
  if (selected && selected.id !== state.selectedRuleId) {
    state.selectedRuleId = selected.id;
  }
  $("#rules").innerHTML = rules.map(renderRuleCard).join("") || `
    <div class="empty">No scenarios yet.</div>
  `;
  $("#rule-count").textContent = `${rules.length} scenario${rules.length === 1 ? "" : "s"}`;
}

function renderPresetList() {
  const presets = state.presets || [];
  $("#presets").innerHTML = presets
    .map((preset, index) => `
      <article class="preset-card">
        <div>
          <strong>${escapeHtml(preset.name)}</strong>
          <p>${escapeHtml(preset.description || "")}</p>
        </div>
        <button type="button" data-op="add-preset" data-preset="${index}">Add</button>
      </article>
    `)
    .join("") || `<p class="muted">No presets found.</p>`;
}

function renderGesturePalette() {
  const gestures = state.capabilities?.gestures || {};
  $("#gesture-palette").innerHTML = Object.entries(gestures)
    .map(([key, meta]) => `
      <span class="gesture-chip" title="${escapeHtml(meta.description || key)}">
        <strong>${escapeHtml(meta.label || key)}</strong>
        <small>${escapeHtml(key)}</small>
      </span>
    `)
    .join("");
}

function inspectorField(label, html) {
  return `<label>${escapeHtml(label)}${html}</label>`;
}

function renderSequenceFields(rule, index) {
  const trigger = rule.trigger;
  const steps = trigger.steps || [];
  return `
    <div class="field-grid two">
      ${inspectorField("Max total ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="max_total_ms" value="${numberValue(trigger.max_total_ms, 6000)}">`)}
      ${inspectorField("Max gap ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="max_gap_ms" value="${numberValue(trigger.max_gap_ms, 1800)}">`)}
    </div>
    <div class="steps-list">
      ${steps.map((step, stepIndex) => `
        <div class="step-editor">
          <span>${stepIndex + 1}</span>
          <select data-scope="step" data-index="${index}" data-step="${stepIndex}" data-field="gesture">${gestureOptions(step.gesture)}</select>
          <input type="number" min="0" data-scope="step" data-index="${index}" data-step="${stepIndex}" data-field="hold_ms" value="${numberValue(step.hold_ms, 0)}" aria-label="Step hold milliseconds">
          <button type="button" data-op="remove-step" data-index="${index}" data-step="${stepIndex}">Remove</button>
        </div>
      `).join("")}
    </div>
    <button type="button" data-op="add-step" data-index="${index}">Add step</button>
  `;
}

function renderTriggerFields(rule, index) {
  const trigger = rule.trigger;
  const kind = trigger.kind || "hold";

  if (kind === "sequence") return renderSequenceFields(rule, index);

  if (kind === "armed_hold") {
    return `
      <div class="field-grid two">
        ${inspectorField("Arm gesture", `<select data-scope="trigger" data-index="${index}" data-field="arm_gesture">${gestureOptions(trigger.arm_gesture)}</select>`)}
        ${inspectorField("Target gesture", `<select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select>`)}
      </div>
      <div class="field-grid three">
        ${inspectorField("Arm timeout ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="arm_timeout_ms" value="${numberValue(trigger.arm_timeout_ms, 8000)}">`)}
        ${inspectorField("First hold ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 600)}">`)}
        ${inspectorField("Repeat ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 900)}">`)}
      </div>
    `;
  }

  if (kind === "repeat_hold") {
    return `
      <div class="field-grid three">
        ${inspectorField("Gesture", `<select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select>`)}
        ${inspectorField("First hold ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 900)}">`)}
        ${inspectorField("Repeat ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 900)}">`)}
      </div>
    `;
  }

  if (kind === "value_control") {
    return `
      <div class="field-grid two">
        ${inspectorField("Gesture", `<select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select>`)}
        ${inspectorField("Repeat ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="repeat_ms" value="${numberValue(trigger.repeat_ms, 250)}">`)}
      </div>
    `;
  }

  if (kind === "motion") {
    return inspectorField("Motion gesture", `<select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select>`);
  }

  return `
    <div class="field-grid two">
      ${inspectorField("Gesture", `<select data-scope="trigger" data-index="${index}" data-field="gesture">${gestureOptions(trigger.gesture)}</select>`)}
      ${inspectorField("Hold ms", `<input type="number" min="0" data-scope="trigger" data-index="${index}" data-field="hold_ms" value="${numberValue(trigger.hold_ms, 1000)}">`)}
    </div>
  `;
}

function rgbValue(action) {
  return Array.isArray(action.rgb) ? action.rgb.join(",") : "";
}

function renderActionFields(rule, index) {
  const action = rule.action;
  const kind = action.kind;

  if (kind === "workflow.enter_command_mode") {
    return inspectorField("Duration ms", `<input type="number" min="0" data-scope="action" data-index="${index}" data-field="duration_ms" value="${numberValue(action.duration_ms, 10000)}">`);
  }

  if (kind === "virtual_lamp.brightness_step") {
    return `
      <div class="field-grid two">
        ${inspectorField("Direction", `
          <select data-scope="action" data-index="${index}" data-field="direction">
            <option value="1" ${numberValue(action.direction, 1) >= 0 ? "selected" : ""}>Increase</option>
            <option value="-1" ${numberValue(action.direction, 1) < 0 ? "selected" : ""}>Decrease</option>
          </select>
        `)}
        ${inspectorField("Step percent", `<input type="number" min="0" max="100" data-scope="action" data-index="${index}" data-field="step_percent" value="${numberValue(action.step_percent, 10)}">`)}
      </div>
    `;
  }

  if (kind === "virtual_lamp.brightness_set") {
    return inspectorField("Brightness percent", `<input type="number" min="0" max="100" data-scope="action" data-index="${index}" data-field="percent" value="${numberValue(action.percent, 50)}">`);
  }

  if (kind === "virtual_lamp.color_set") {
    return inspectorField("RGB", `<input type="text" data-scope="action" data-index="${index}" data-field="rgb" value="${escapeHtml(rgbValue(action))}" placeholder="255,255,255">`);
  }

  if (kind === "smart_home.set_power") {
    return `
      <div class="field-grid two">
        ${inspectorField("Device ID", `<input data-scope="action" data-index="${index}" data-field="device_id" value="${escapeHtml(action.device_id || "")}">`)}
        ${inspectorField("Power", `
          <select data-scope="action" data-index="${index}" data-field="on">
            <option value="true" ${action.on !== false ? "selected" : ""}>On</option>
            <option value="false" ${action.on === false ? "selected" : ""}>Off</option>
          </select>
        `)}
      </div>
    `;
  }

  if (kind === "smart_home.set_brightness") {
    return `
      <div class="field-grid two">
        ${inspectorField("Device ID", `<input data-scope="action" data-index="${index}" data-field="device_id" value="${escapeHtml(action.device_id || "")}">`)}
        ${inspectorField("Brightness percent", `<input type="number" min="0" max="100" data-scope="action" data-index="${index}" data-field="percent" value="${numberValue(action.percent, 60)}">`)}
      </div>
    `;
  }

  if (kind === "smart_home.set_color") {
    return `
      <div class="field-grid two">
        ${inspectorField("Device ID", `<input data-scope="action" data-index="${index}" data-field="device_id" value="${escapeHtml(action.device_id || "")}">`)}
        ${inspectorField("RGB", `<input type="text" data-scope="action" data-index="${index}" data-field="rgb" value="${escapeHtml(rgbValue(action))}" placeholder="255,255,255">`)}
      </div>
    `;
  }

  if (kind === "smart_home.activate_scene") {
    return inspectorField("Scene ID", `<input data-scope="action" data-index="${index}" data-field="scene_id" value="${escapeHtml(action.scene_id || "")}">`);
  }

  return `<p class="muted">No extra fields.</p>`;
}

function renderInspector() {
  const rules = state.config?.rules || [];
  const rule = selectedRule();
  const index = rules.indexOf(rule);

  if (!rule) {
    $("#inspector").innerHTML = `
      <section class="inspector-card">
        <h2>Scenario</h2>
        <p class="muted">No scenario selected.</p>
      </section>
    `;
    return;
  }

  ensureRuleShape(rule);
  const triggerKinds = state.capabilities?.trigger_kinds || [];
  const actionKinds = state.capabilities?.action_kinds || [];
  const confirmation = rule.safety.confirmation || { required: false };
  const commandMode = rule.safety.command_mode || { required: false };

  $("#inspector").innerHTML = `
    <section class="inspector-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Selected</p>
          <h2>${escapeHtml(rule.name || rule.id)}</h2>
        </div>
      </div>

      <div class="field-grid one">
        ${inspectorField("Scenario name", `<input data-scope="rule" data-index="${index}" data-field="name" value="${escapeHtml(rule.name || "")}">`)}
        ${inspectorField("Scenario ID", `<input data-scope="rule" data-index="${index}" data-field="id" value="${escapeHtml(rule.id || "")}">`)}
      </div>
    </section>

    <section class="inspector-card accent-when">
      <h2>When</h2>
      ${inspectorField("Trigger block", `<select data-scope="trigger-kind" data-index="${index}">${kindOptions(triggerKinds, rule.trigger.kind, triggerMeta)}</select>`)}
      ${renderTriggerFields(rule, index)}
    </section>

    <section class="inspector-card accent-do">
      <h2>Do</h2>
      ${inspectorField("Action block", `<select data-scope="action-kind" data-index="${index}">${kindOptions(actionKinds, rule.action.kind, actionMeta)}</select>`)}
      ${renderActionFields(rule, index)}
    </section>

    <section class="inspector-card accent-safe">
      <h2>Safety</h2>
      <div class="field-grid one">
        ${inspectorField("Cooldown ms", `<input type="number" min="0" data-scope="safety" data-index="${index}" data-field="cooldown_ms" value="${numberValue(rule.safety.cooldown_ms, 0)}">`)}
        <label class="switch"><input type="checkbox" data-scope="command-mode" data-index="${index}" ${commandMode.required ? "checked" : ""}> Require command mode</label>
        <label class="switch"><input type="checkbox" data-scope="confirmation-required" data-index="${index}" ${confirmation.required ? "checked" : ""}> Require confirmation</label>
      </div>
      <div class="field-grid two">
        ${inspectorField("Confirm gesture", `<select data-scope="confirmation" data-index="${index}" data-field="gesture">${gestureOptions(confirmation.gesture || "TWO_THUMBS_UP")}</select>`)}
        ${inspectorField("Timeout ms", `<input type="number" min="0" data-scope="confirmation" data-index="${index}" data-field="timeout_ms" value="${numberValue(confirmation.timeout_ms, 4000)}">`)}
      </div>
    </section>
  `;
}

function renderRaw() {
  $("#raw-json").value = JSON.stringify(state.config, null, 2);
}

function renderView() {
  const showJson = state.view === "json";
  $("#block-view").classList.toggle("hidden", showJson);
  $("#json-view").classList.toggle("hidden", !showJson);
  $("#blocks-tab").classList.toggle("active", !showJson);
  $("#json-tab").classList.toggle("active", showJson);
}

function render() {
  renderPresetList();
  renderGesturePalette();
  renderRules();
  renderInspector();
  renderRaw();
  renderView();
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
  state.selectedRuleId = (rules.rules || [])[0]?.id || null;
  render();
  showMessage("Loaded rules.", "ok");
}

function configFromRaw() {
  return JSON.parse($("#raw-json").value);
}

async function saveRules() {
  const config = configFromRaw();
  const saved = await fetchJson("/api/rules", {
    method: "PUT",
    body: JSON.stringify(config),
  });
  state.config = saved;
  if (!selectedRule()) state.selectedRuleId = saved.rules?.[0]?.id || null;
  render();
  showMessage("Saved rules.", "ok");
}

async function validateRules() {
  await fetchJson("/api/rules/validate", {
    method: "POST",
    body: JSON.stringify(configFromRaw()),
  });
  showMessage("Rules are valid.", "ok");
}

async function resetRules() {
  if (!confirm("Reset editable rules to defaults?")) return;
  const reset = await fetchJson("/api/rules/reset", { method: "POST" });
  state.config = reset;
  state.selectedRuleId = reset.rules?.[0]?.id || null;
  render();
  showMessage("Rules reset to defaults.", "ok");
}

function setActionValue(action, field, value, element) {
  if (field === "rgb") {
    const channels = value
      .split(",")
      .map((part) => Number(part.trim()))
      .filter((part) => Number.isFinite(part));
    if (channels.length === 3) action.rgb = channels;
    else delete action.rgb;
    return;
  }

  if (field === "direction" || element.type === "number") {
    action[field] = numberValue(value);
    return;
  }

  if (field === "on") {
    action.on = value === "true";
    return;
  }

  action[field] = value;
}

function updateNested(scope, element) {
  const index = Number(element.dataset.index);
  const rule = state.config.rules[index];
  const field = element.dataset.field;
  const value = element.type === "checkbox" ? element.checked : element.value;

  if (scope === "rule") {
    const previousId = rule.id;
    rule[field] = field === "enabled" ? element.checked : value;
    if (field === "id" && state.selectedRuleId === previousId) {
      state.selectedRuleId = value;
    }
  } else if (scope === "trigger") {
    rule.trigger[field] = element.type === "number" ? numberValue(value) : value;
  } else if (scope === "action") {
    setActionValue(rule.action, field, value, element);
  } else if (scope === "safety") {
    rule.safety[field] = element.type === "number" ? numberValue(value) : value;
  } else if (scope === "confirmation") {
    rule.safety.confirmation ||= { required: false };
    rule.safety.confirmation[field] = element.type === "number" ? numberValue(value) : value;
  }

  syncRawOnly();
  renderRules();
}

function handleFieldChange(event) {
  const element = event.target;
  const scope = element.dataset.scope;
  if (!scope || !state.config) return;

  const index = Number(element.dataset.index);
  const rule = state.config.rules[index];

  if (scope === "trigger-kind") {
    rule.trigger = defaultTrigger(element.value);
    syncRawOnly();
    render();
    return;
  }

  if (scope === "action-kind") {
    rule.action = defaultAction(element.value);
    syncRawOnly();
    render();
    return;
  }

  if (scope === "step") {
    const stepIndex = Number(element.dataset.step);
    const field = element.dataset.field;
    rule.trigger.steps[stepIndex][field] = element.type === "number" ? numberValue(element.value) : element.value;
    syncRawOnly();
    renderRules();
    return;
  }

  if (scope === "command-mode") {
    rule.safety.command_mode ||= { required: false };
    rule.safety.command_mode.required = element.checked;
    syncRawOnly();
    renderRules();
    return;
  }

  if (scope === "confirmation-required") {
    rule.safety.confirmation ||= { required: false, gesture: "TWO_THUMBS_UP", timeout_ms: 4000 };
    rule.safety.confirmation.required = element.checked;
    syncRawOnly();
    renderRules();
    return;
  }

  updateNested(scope, element);
}

function insertRule(rule, index = null) {
  state.config.rules ||= [];
  if (index === null) state.config.rules.push(rule);
  else state.config.rules.splice(index, 0, rule);
  state.selectedRuleId = rule.id;
  render();
}

function moveRule(index, direction) {
  const nextIndex = index + direction;
  const rules = state.config.rules;
  if (nextIndex < 0 || nextIndex >= rules.length) return;
  const [rule] = rules.splice(index, 1);
  rules.splice(nextIndex, 0, rule);
  render();
}

function handleClick(event) {
  const button = event.target.closest("button[data-op]");
  if (!button || !state.config) return;
  const op = button.dataset.op;
  const index = Number(button.dataset.index);

  if (op === "select-rule") {
    selectRule(button.dataset.ruleId);
  } else if (op === "add-rule") {
    insertRule(defaultRule());
  } else if (op === "delete-rule") {
    const [removed] = state.config.rules.splice(index, 1);
    if (removed?.id === state.selectedRuleId) {
      state.selectedRuleId = state.config.rules[Math.min(index, state.config.rules.length - 1)]?.id || null;
    }
    render();
  } else if (op === "duplicate-rule") {
    const copy = clone(state.config.rules[index]);
    copy.id = uniqueRuleId(copy.id);
    copy.name = `${copy.name || copy.id} copy`;
    insertRule(copy, index + 1);
  } else if (op === "move-rule-up") {
    moveRule(index, -1);
  } else if (op === "move-rule-down") {
    moveRule(index, 1);
  } else if (op === "add-step") {
    state.config.rules[index].trigger.steps ||= [];
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
    insertRule(rule);
  }
  syncRawOnly();
}

function bindToolbar() {
  $("#reload").addEventListener("click", () => loadAll().catch((error) => showMessage(error.message, "error")));
  $("#save").addEventListener("click", () => saveRules().catch((error) => showMessage(error.message, "error")));
  $("#validate").addEventListener("click", () => validateRules().catch((error) => showMessage(error.message, "error")));
  $("#reset").addEventListener("click", () => resetRules().catch((error) => showMessage(error.message, "error")));
  $("#format").addEventListener("click", () => {
    try {
      state.config = configFromRaw();
      state.selectedRuleId = selectedRule()?.id || state.config.rules?.[0]?.id || null;
      render();
      showMessage("Formatted JSON.", "ok");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      state.view = tab.dataset.view;
      renderView();
    });
  });
  document.addEventListener("change", handleFieldChange);
  document.addEventListener("input", (event) => {
    if (event.target.matches("input[data-scope]")) {
      handleFieldChange(event);
    }
  });
  document.addEventListener("click", handleClick);
}

bindToolbar();
loadAll().catch((error) => showMessage(error.message, "error"));
