/**
 * Recurring Todos — Custom Lovelace Card (LitElement)
 *
 * Displays a task list with due dates, overdue highlighting,
 * add/edit forms with recurrence UI, and completion history.
 *
 * Uses LitElement for efficient DOM diffing — form inputs survive
 * HA's frequent hass state pushes without being destroyed.
 */

(async () => {

const DAYS_OF_WEEK = [
  { value: "MO", label: "Mon" },
  { value: "TU", label: "Tue" },
  { value: "WE", label: "Wed" },
  { value: "TH", label: "Thu" },
  { value: "FR", label: "Fri" },
  { value: "SA", label: "Sat" },
  { value: "SU", label: "Sun" },
];

// Wait for HA to register its Lit-based elements before we can access Lit.
// Card JS may load before HA's own elements are defined.
await customElements.whenDefined("ha-panel-lovelace");
const { LitElement, html, css } = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);

// ============================================================
// Card Editor
// ============================================================

class RecurringTodosCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
    };
  }

  constructor() {
    super();
    this._config = {};
  }

  setConfig(config) {
    this._config = { ...config };
  }

  static get styles() {
    return css`
      .editor {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 16px 0;
      }
      .row {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      label {
        font-size: 0.85em;
        color: var(--secondary-text-color, #727272);
        font-weight: 500;
      }
      input {
        padding: 8px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        font-size: 0.95em;
        background: var(
          --ha-card-background,
          var(--card-background-color, #fff)
        );
        color: var(--primary-text-color, #212121);
      }
    `;
  }

  render() {
    if (!this.hass) return html``;

    return html`
      <div class="editor">
        <div class="row">
          <label>Entity</label>
          <ha-entity-picker
            .hass=${this.hass}
            .value=${this._config.entity || ""}
            .includeDomains=${["todo"]}
            @value-changed=${this._entityChanged}
          ></ha-entity-picker>
        </div>
        <div class="row">
          <label>Title (optional)</label>
          <input
            type="text"
            .value=${this._config.title || ""}
            placeholder="Uses entity name if empty"
            @input=${this._titleChanged}
          />
        </div>
      </div>
    `;
  }

  _entityChanged(ev) {
    this._config = { ...this._config, entity: ev.detail.value };
    this._dispatch();
  }

  _titleChanged(ev) {
    this._config = { ...this._config, title: ev.target.value };
    this._dispatch();
  }

  _dispatch() {
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }
}

// ============================================================
// Main Card
// ============================================================

class RecurringTodosCard extends LitElement {
  static get properties() {
    return {
      hass: { attribute: false },
      _config: { state: true },
      _view: { state: true },
      _editTask: { state: true },
      _historyTask: { state: true },
      _formData: { state: true },
    };
  }

  constructor() {
    super();
    this._config = {};
    this._view = "list";
    this._editTask = null;
    this._historyTask = null;
    this._formData = {};
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = config;
  }

  getCardSize() {
    return 4;
  }

  static getConfigElement() {
    return document.createElement("recurring-todos-card-editor");
  }

  static getStubConfig() {
    return { entity: "" };
  }

  shouldUpdate(changedProps) {
    // When on a form view, skip updates caused only by hass changes
    // (belt-and-suspenders — Lit's diffing already preserves inputs)
    if (
      (this._view === "add" || this._view === "edit") &&
      changedProps.size === 1 &&
      changedProps.has("hass")
    ) {
      return false;
    }
    return true;
  }

  // --- Data helpers ---

  _getState() {
    if (!this.hass || !this._config.entity) return null;
    return this.hass.states[this._config.entity];
  }

  _getTasks() {
    const state = this._getState();
    if (!state || !state.attributes) return [];
    return state.attributes.todo_items || [];
  }

  _getOverdueTasks() {
    const state = this._getState();
    if (!state || !state.attributes) return [];
    return state.attributes.overdue_tasks || [];
  }

  _getTaskRrule(uid) {
    const state = this._getState();
    if (!state || !state.attributes || !state.attributes.tasks_detail)
      return null;
    const detail = state.attributes.tasks_detail.find((t) => t.uid === uid);
    return detail ? detail.rrule : null;
  }

  _isOverdue(task) {
    const overdueList = this._getOverdueTasks();
    return overdueList.some((t) => t.uid === task.uid);
  }

  _daysUntilDue(task) {
    if (!task.due) return null;
    const due = new Date(task.due + "T00:00:00");
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.round((due - today) / (1000 * 60 * 60 * 24));
  }

  // --- RRULE helpers ---

  _buildRrule(freq, interval, days) {
    if (freq === "none") return "";
    let rule = "FREQ=" + freq.toUpperCase();
    if (interval && interval > 1) {
      rule += ";INTERVAL=" + String(interval);
    }
    if (freq === "weekly" && days && days.length > 0) {
      rule += ";BYDAY=" + days.join(",");
    }
    return rule;
  }

  _parseRrule(rrule) {
    const result = { freq: "none", interval: 1, days: [] };
    if (!rrule) return result;

    const parts = rrule.split(";");
    for (const part of parts) {
      const [key, val] = part.split("=");
      if (key === "FREQ") result.freq = val.toLowerCase();
      if (key === "INTERVAL") result.interval = parseInt(val, 10);
      if (key === "BYDAY") result.days = val.split(",");
    }
    return result;
  }

  // --- Service calls ---

  async _completeTask(uid) {
    await this.hass.callService("recurring_todos", "complete_task", {
      entity_id: this._config.entity,
      task_uid: uid,
    });
  }

  async _snoozeTask(uid, days = 1) {
    await this.hass.callService("recurring_todos", "snooze_task", {
      entity_id: this._config.entity,
      task_uid: uid,
      days: days,
    });
  }

  async _createTask(data) {
    const serviceData = {
      entity_id: this._config.entity,
      name: data.name,
    };
    if (data.description) serviceData.description = data.description;
    if (data.due_date) serviceData.due_date = data.due_date;
    if (data.rrule) serviceData.rrule = data.rrule;

    await this.hass.callService("recurring_todos", "create_task", serviceData);
  }

  async _updateTask(uid, data) {
    const serviceData = {
      entity_id: this._config.entity,
      task_uid: uid,
    };
    if (data.name !== undefined) serviceData.name = data.name;
    if (data.description !== undefined)
      serviceData.description = data.description;
    if (data.due_date !== undefined) serviceData.due_date = data.due_date;
    if (data.rrule !== undefined) serviceData.rrule = data.rrule;

    await this.hass.callService("recurring_todos", "update_task", serviceData);
  }

  async _deleteTask(uid) {
    await this.hass.callService("todo", "remove_item", {
      entity_id: this._config.entity,
      item: uid,
    });
  }

  // --- Navigation ---

  _goList() {
    this._view = "list";
    this._editTask = null;
    this._historyTask = null;
    this._formData = {};
  }

  _goAdd() {
    this._formData = { freq: "none", interval: 1, days: [] };
    this._view = "add";
  }

  _goEdit(task) {
    const rrule = this._parseRrule(this._getTaskRrule(task.uid));
    this._formData = {
      name: task.summary || "",
      description: task.description || "",
      due_date: task.due || "",
      freq: rrule.freq,
      interval: rrule.interval,
      days: [...rrule.days],
    };
    this._editTask = task;
    this._view = "edit";
  }

  _goHistory(task) {
    this._historyTask = task;
    this._view = "history";
  }

  // --- Form handlers ---

  _onFormInput(field, ev) {
    this._formData = { ...this._formData, [field]: ev.target.value };
  }

  _onFreqChange(ev) {
    this._formData = { ...this._formData, freq: ev.target.value };
  }

  _onIntervalChange(ev) {
    this._formData = {
      ...this._formData,
      interval: parseInt(ev.target.value, 10) || 1,
    };
  }

  _onDayToggle(dayValue, ev) {
    const days = [...(this._formData.days || [])];
    if (ev.target.checked) {
      if (!days.includes(dayValue)) days.push(dayValue);
    } else {
      const idx = days.indexOf(dayValue);
      if (idx >= 0) days.splice(idx, 1);
    }
    this._formData = { ...this._formData, days };
  }

  async _onFormSubmit(ev) {
    ev.preventDefault();
    const fd = this._formData;
    const builtRrule = this._buildRrule(
      fd.freq || "none",
      fd.interval || 1,
      fd.days || []
    );

    const data = {
      name: fd.name || "",
      description: fd.description || "",
      due_date: fd.due_date || "",
      rrule: builtRrule,
    };

    if (this._view === "edit" && this._editTask) {
      await this._updateTask(this._editTask.uid, data);
    } else {
      await this._createTask(data);
    }
    this._goList();
  }

  // --- Render ---

  render() {
    const state = this._getState();

    if (!state) {
      return html`
        <ha-card>
          <div class="card-content">
            Entity not found: ${this._config.entity}
          </div>
        </ha-card>
      `;
    }

    const title =
      this._config.title ||
      state.attributes.friendly_name ||
      "Recurring Todos";

    return html`
      <ha-card>
        <div class="card-header">
          <span class="title">${title}</span>
          ${this._view === "list"
            ? html`<button class="btn-add" id="btn-add" @click=${this._goAdd}>
                +
              </button>`
            : html`<button
                class="btn-back"
                id="btn-back"
                @click=${this._goList}
              >
                \u2190
              </button>`}
        </div>
        <div class="card-content">
          ${this._view === "list"
            ? this._renderList()
            : this._view === "add"
              ? this._renderForm(null)
              : this._view === "edit"
                ? this._renderForm(this._editTask)
                : this._renderHistory()}
        </div>
      </ha-card>
    `;
  }

  _renderList() {
    const tasks = this._getTasks();
    if (tasks.length === 0) {
      return html`<div class="empty">No tasks yet</div>`;
    }

    const sorted = [...tasks].sort((a, b) => {
      if (!a.due && !b.due) return 0;
      if (!a.due) return 1;
      if (!b.due) return -1;
      return a.due.localeCompare(b.due);
    });

    return html`${sorted.map((task) => this._renderTask(task))}`;
  }

  _renderTask(task) {
    const overdue = this._isOverdue(task);
    const daysUntil = this._daysUntilDue(task);
    const completed = task.status === "completed";

    let dueText = "";
    if (daysUntil !== null) {
      if (daysUntil < 0) dueText = Math.abs(daysUntil) + "d overdue";
      else if (daysUntil === 0) dueText = "Today";
      else if (daysUntil === 1) dueText = "Tomorrow";
      else dueText = daysUntil + "d";
    }

    return html`
      <div
        class="task ${overdue ? "overdue" : ""} ${completed ? "completed" : ""}"
      >
        <div class="task-main">
          <button
            class="btn-complete"
            title="Complete"
            @click=${(e) => {
              e.stopPropagation();
              this._completeTask(task.uid);
            }}
          >
            ${completed ? "\u2611" : "\u2610"}
          </button>
          <div class="task-info">
            <span class="task-name">${task.summary}</span>
            ${task.description
              ? html`<span class="task-desc">${task.description}</span>`
              : ""}
          </div>
          ${daysUntil !== null
            ? html`<span class="due-label ${overdue ? "overdue" : ""}"
                >${dueText}</span
              >`
            : ""}
        </div>
        <div class="task-actions">
          <button
            class="btn-action"
            title="Snooze 1 day"
            @click=${(e) => {
              e.stopPropagation();
              this._snoozeTask(task.uid);
            }}
          >
            \u23F0
          </button>
          <button
            class="btn-action"
            title="Edit"
            @click=${(e) => {
              e.stopPropagation();
              this._goEdit(task);
            }}
          >
            \u270F
          </button>
          <button
            class="btn-action"
            title="History"
            @click=${(e) => {
              e.stopPropagation();
              this._goHistory(task);
            }}
          >
            \uD83D\uDCCB
          </button>
          <button
            class="btn-action"
            title="Delete"
            @click=${(e) => {
              e.stopPropagation();
              this._deleteTask(task.uid);
            }}
          >
            \uD83D\uDDD1
          </button>
        </div>
      </div>
    `;
  }

  _renderForm(task) {
    const isEdit = !!task;
    const fd = this._formData;

    return html`
      <form id="task-form" @submit=${this._onFormSubmit}>
        <label>
          Name
          <input
            type="text"
            .value=${fd.name || ""}
            @input=${(e) => this._onFormInput("name", e)}
            required
          />
        </label>
        <label>
          Description
          <input
            type="text"
            .value=${fd.description || ""}
            @input=${(e) => this._onFormInput("description", e)}
          />
        </label>
        <label>
          Due date
          <input
            type="date"
            .value=${fd.due_date || ""}
            @input=${(e) => this._onFormInput("due_date", e)}
          />
        </label>
        <fieldset class="recurrence">
          <legend>Recurrence</legend>
          <label>
            Frequency
            <select .value=${fd.freq || "none"} @change=${this._onFreqChange}>
              ${["none", "daily", "weekly", "monthly", "yearly"].map(
                (opt) =>
                  html`<option value=${opt} ?selected=${fd.freq === opt}>
                    ${opt.charAt(0).toUpperCase() + opt.slice(1)}
                  </option>`
              )}
            </select>
          </label>
          <label class="interval-label">
            Every N
            <input
              type="number"
              min="1"
              max="99"
              .value=${String(fd.interval || 1)}
              @input=${this._onIntervalChange}
            />
          </label>
          <div
            class="days-select"
            id="days-select"
            style="display: ${fd.freq === "weekly" ? "flex" : "none"}"
          >
            ${DAYS_OF_WEEK.map(
              (d) => html`
                <label class="day-chip">
                  <input
                    type="checkbox"
                    .checked=${(fd.days || []).includes(d.value)}
                    @change=${(e) => this._onDayToggle(d.value, e)}
                  />
                  <span>${d.label}</span>
                </label>
              `
            )}
          </div>
        </fieldset>
        <div class="form-actions">
          <button type="submit" class="btn-submit">
            ${isEdit ? "Update" : "Add"} Task
          </button>
        </div>
      </form>
    `;
  }

  _renderHistory() {
    const task = this._historyTask;
    if (!task) {
      return html`<div>No task selected</div>`;
    }

    return html`
      <div class="history-view">
        <h3>${task.summary}</h3>
        <div class="history-meta">
          <span>Status: ${task.status}</span>
          ${task.due ? html`<span>Due: ${task.due}</span>` : ""}
        </div>
        ${task.description
          ? html`<p class="history-desc">${task.description}</p>`
          : ""}
        <div class="history-note">
          Completion history is stored in the backend. Access via Developer
          Tools &gt; States for the full record.
        </div>
      </div>
    `;
  }

  // --- Styles ---

  static get styles() {
    return css`
      :host {
        --card-bg: var(
          --ha-card-background,
          var(--card-background-color, #fff)
        );
        --text-primary: var(--primary-text-color, #212121);
        --text-secondary: var(--secondary-text-color, #727272);
        --accent: var(--primary-color, #03a9f4);
        --error: var(--error-color, #db4437);
        --divider: var(--divider-color, #e0e0e0);
      }
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 16px 0;
        font-size: 1.2em;
        font-weight: 500;
        color: var(--text-primary);
      }
      .card-content {
        padding: 12px 16px 16px;
      }
      .btn-add,
      .btn-back {
        background: none;
        border: none;
        font-size: 1.4em;
        cursor: pointer;
        color: var(--accent);
        padding: 4px 8px;
        border-radius: 4px;
      }
      .btn-add:hover,
      .btn-back:hover {
        background: rgba(0, 0, 0, 0.05);
      }
      .empty {
        text-align: center;
        color: var(--text-secondary);
        padding: 24px 0;
      }
      .task {
        border-bottom: 1px solid var(--divider);
        padding: 8px 0;
      }
      .task:last-child {
        border-bottom: none;
      }
      .task-main {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .task-info {
        flex: 1;
        min-width: 0;
        display: flex;
        flex-direction: column;
      }
      .task-name {
        color: var(--text-primary);
        font-size: 0.95em;
      }
      .task-desc {
        color: var(--text-secondary);
        font-size: 0.8em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .task.completed .task-name {
        text-decoration: line-through;
        opacity: 0.6;
      }
      .task.overdue {
        background: rgba(219, 68, 55, 0.06);
        margin: 0 -16px;
        padding: 8px 16px;
      }
      .due-label {
        font-size: 0.8em;
        color: var(--text-secondary);
        white-space: nowrap;
      }
      .due-label.overdue {
        color: var(--error);
        font-weight: 500;
      }
      .task-actions {
        display: flex;
        gap: 4px;
        padding-left: 36px;
        margin-top: 4px;
      }
      .btn-complete {
        background: none;
        border: none;
        font-size: 1.2em;
        cursor: pointer;
        padding: 2px;
        line-height: 1;
        color: var(--text-secondary);
      }
      .btn-action {
        background: none;
        border: none;
        font-size: 0.85em;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
        color: var(--text-secondary);
      }
      .btn-action:hover {
        background: rgba(0, 0, 0, 0.05);
      }
      form {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      form label {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 0.85em;
        color: var(--text-secondary);
      }
      form input[type="text"],
      form input[type="date"],
      form input[type="number"],
      form select {
        padding: 8px;
        border: 1px solid var(--divider);
        border-radius: 4px;
        font-size: 0.95em;
        background: var(--card-bg);
        color: var(--text-primary);
      }
      fieldset.recurrence {
        border: 1px solid var(--divider);
        border-radius: 4px;
        padding: 12px;
      }
      fieldset.recurrence legend {
        font-size: 0.85em;
        color: var(--text-secondary);
        padding: 0 4px;
      }
      .interval-label input {
        width: 60px;
      }
      .days-select {
        flex-wrap: wrap;
        gap: 4px;
        margin-top: 8px;
      }
      .day-chip {
        flex-direction: row !important;
        align-items: center;
        gap: 2px !important;
        background: rgba(0, 0, 0, 0.05);
        padding: 4px 8px;
        border-radius: 12px;
        cursor: pointer;
        font-size: 0.85em;
      }
      .day-chip input {
        display: none;
      }
      .day-chip:has(input:checked) {
        background: var(--accent);
        color: #fff;
      }
      .form-actions {
        display: flex;
        justify-content: flex-end;
      }
      .btn-submit {
        background: var(--accent);
        color: #fff;
        border: none;
        padding: 8px 20px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.95em;
      }
      .btn-submit:hover {
        opacity: 0.9;
      }
      .history-view h3 {
        margin: 0 0 8px;
        color: var(--text-primary);
      }
      .history-meta {
        display: flex;
        gap: 16px;
        font-size: 0.85em;
        color: var(--text-secondary);
        margin-bottom: 8px;
      }
      .history-desc {
        font-size: 0.9em;
        color: var(--text-primary);
        margin: 8px 0;
      }
      .history-note {
        font-size: 0.8em;
        color: var(--text-secondary);
        font-style: italic;
        margin-top: 12px;
        padding: 8px;
        background: rgba(0, 0, 0, 0.03);
        border-radius: 4px;
      }
    `;
  }
}

// ============================================================
// Registration
// ============================================================

customElements.define("recurring-todos-card-editor", RecurringTodosCardEditor);
customElements.define("recurring-todos-card", RecurringTodosCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "recurring-todos-card",
  name: "Recurring Todos",
  description:
    "Task list with recurring due dates, overdue highlighting, and completion history.",
});

})();
