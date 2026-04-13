/**
 * Recurring Todos — Custom Lovelace Card
 *
 * Displays a task list with due dates, overdue highlighting,
 * add/edit forms with recurrence UI, and completion history.
 *
 * Security: All user-supplied strings are escaped via _esc() which
 * uses textContent-based sanitization before insertion into templates.
 */

const DAYS_OF_WEEK = [
  { value: "MO", label: "Mon" },
  { value: "TU", label: "Tue" },
  { value: "WE", label: "Wed" },
  { value: "TH", label: "Thu" },
  { value: "FR", label: "Fri" },
  { value: "SA", label: "Sat" },
  { value: "SU", label: "Sun" },
];

class RecurringTodosCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._view = "list"; // list | add | edit | history
    this._editTask = null;
    this._historyTask = null;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    // Skip re-render while user is on a form to avoid destroying inputs mid-typing
    if (this._view === "add" || this._view === "edit") return;
    this._render();
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

  // --- Data helpers ---

  _getState() {
    if (!this._hass || !this._config.entity) return null;
    return this._hass.states[this._config.entity];
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
    if (!state || !state.attributes || !state.attributes.tasks_detail) return null;
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
    await this._hass.callService("recurring_todos", "complete_task", {
      entity_id: this._config.entity,
      task_uid: uid,
    });
  }

  async _snoozeTask(uid, days = 1) {
    await this._hass.callService("recurring_todos", "snooze_task", {
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

    await this._hass.callService("recurring_todos", "create_task", serviceData);
  }

  async _updateTask(uid, data) {
    const serviceData = {
      entity_id: this._config.entity,
      task_uid: uid,
    };
    if (data.name !== undefined) serviceData.name = data.name;
    if (data.description !== undefined) serviceData.description = data.description;
    if (data.due_date !== undefined) serviceData.due_date = data.due_date;
    if (data.rrule !== undefined) serviceData.rrule = data.rrule;

    await this._hass.callService("recurring_todos", "update_task", serviceData);
  }

  async _deleteTask(uid) {
    await this._hass.callService("todo", "remove_item", {
      entity_id: this._config.entity,
      item: uid,
    });
  }

  // --- Text sanitization ---

  /**
   * Escape user-supplied strings for safe insertion into HTML templates.
   * Uses textContent-based encoding to prevent XSS.
   */
  _esc(str) {
    if (!str) return "";
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  // --- Rendering via safe DOM construction ---

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const root = this.shadowRoot;

    // Clear previous content
    while (root.firstChild) root.removeChild(root.firstChild);

    // Add styles
    const style = document.createElement("style");
    style.textContent = this._getStyles();
    root.appendChild(style);

    const state = this._getState();
    const card = document.createElement("ha-card");

    if (!state) {
      const content = document.createElement("div");
      content.className = "card-content";
      content.textContent = "Entity not found: " + this._config.entity;
      card.appendChild(content);
      root.appendChild(card);
      return;
    }

    // Header
    const header = document.createElement("div");
    header.className = "card-header";

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = this._config.title || state.attributes.friendly_name || "Recurring Todos";
    header.appendChild(title);

    if (this._view === "list") {
      const btnAdd = document.createElement("button");
      btnAdd.className = "btn-add";
      btnAdd.id = "btn-add";
      btnAdd.textContent = "+";
      btnAdd.addEventListener("click", () => {
        this._view = "add";
        this._render();
      });
      header.appendChild(btnAdd);
    } else {
      const btnBack = document.createElement("button");
      btnBack.className = "btn-back";
      btnBack.id = "btn-back";
      btnBack.textContent = "\u2190";
      btnBack.addEventListener("click", () => {
        this._view = "list";
        this._editTask = null;
        this._historyTask = null;
        this._render();
      });
      header.appendChild(btnBack);
    }

    card.appendChild(header);

    // Content
    const content = document.createElement("div");
    content.className = "card-content";

    switch (this._view) {
      case "list":
        this._buildList(content);
        break;
      case "add":
        this._buildForm(content, null);
        break;
      case "edit":
        this._buildForm(content, this._editTask);
        break;
      case "history":
        this._buildHistory(content);
        break;
    }

    card.appendChild(content);
    root.appendChild(card);
  }

  _buildList(container) {
    const tasks = this._getTasks();
    if (tasks.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "No tasks yet";
      container.appendChild(empty);
      return;
    }

    const sorted = [...tasks].sort((a, b) => {
      if (!a.due && !b.due) return 0;
      if (!a.due) return 1;
      if (!b.due) return -1;
      return a.due.localeCompare(b.due);
    });

    for (const task of sorted) {
      const overdue = this._isOverdue(task);
      const daysUntil = this._daysUntilDue(task);
      const completed = task.status === "completed";

      const taskEl = document.createElement("div");
      taskEl.className = "task" + (overdue ? " overdue" : "") + (completed ? " completed" : "");

      // Main row
      const main = document.createElement("div");
      main.className = "task-main";

      const btnComplete = document.createElement("button");
      btnComplete.className = "btn-complete";
      btnComplete.title = "Complete";
      btnComplete.textContent = completed ? "\u2611" : "\u2610";
      btnComplete.addEventListener("click", (e) => {
        e.stopPropagation();
        this._completeTask(task.uid);
      });
      main.appendChild(btnComplete);

      const info = document.createElement("div");
      info.className = "task-info";

      const nameEl = document.createElement("span");
      nameEl.className = "task-name";
      nameEl.textContent = task.summary;
      info.appendChild(nameEl);

      if (task.description) {
        const descEl = document.createElement("span");
        descEl.className = "task-desc";
        descEl.textContent = task.description;
        info.appendChild(descEl);
      }
      main.appendChild(info);

      if (daysUntil !== null) {
        let dueText = "";
        if (daysUntil < 0) dueText = Math.abs(daysUntil) + "d overdue";
        else if (daysUntil === 0) dueText = "Today";
        else if (daysUntil === 1) dueText = "Tomorrow";
        else dueText = daysUntil + "d";

        const dueLabel = document.createElement("span");
        dueLabel.className = "due-label" + (overdue ? " overdue" : "");
        dueLabel.textContent = dueText;
        main.appendChild(dueLabel);
      }
      taskEl.appendChild(main);

      // Action row
      const actions = document.createElement("div");
      actions.className = "task-actions";

      const btnSnooze = document.createElement("button");
      btnSnooze.className = "btn-action";
      btnSnooze.title = "Snooze 1 day";
      btnSnooze.textContent = "\u23F0";
      btnSnooze.addEventListener("click", (e) => {
        e.stopPropagation();
        this._snoozeTask(task.uid);
      });
      actions.appendChild(btnSnooze);

      const btnEdit = document.createElement("button");
      btnEdit.className = "btn-action";
      btnEdit.title = "Edit";
      btnEdit.textContent = "\u270F";
      btnEdit.addEventListener("click", (e) => {
        e.stopPropagation();
        this._editTask = task;
        this._view = "edit";
        this._render();
      });
      actions.appendChild(btnEdit);

      const btnHistory = document.createElement("button");
      btnHistory.className = "btn-action";
      btnHistory.title = "History";
      btnHistory.textContent = "\uD83D\uDCCB";
      btnHistory.addEventListener("click", (e) => {
        e.stopPropagation();
        this._historyTask = task;
        this._view = "history";
        this._render();
      });
      actions.appendChild(btnHistory);

      const btnDelete = document.createElement("button");
      btnDelete.className = "btn-action";
      btnDelete.title = "Delete";
      btnDelete.textContent = "\uD83D\uDDD1";
      btnDelete.addEventListener("click", (e) => {
        e.stopPropagation();
        this._deleteTask(task.uid);
      });
      actions.appendChild(btnDelete);

      taskEl.appendChild(actions);
      container.appendChild(taskEl);
    }
  }

  _buildForm(container, task) {
    const rrule = task ? this._parseRrule(this._getTaskRrule(task.uid)) : { freq: "none", interval: 1, days: [] };
    const isEdit = !!task;

    const form = document.createElement("form");
    form.id = "task-form";

    // Name
    const nameLabel = document.createElement("label");
    nameLabel.textContent = "Name";
    const nameInput = document.createElement("input");
    nameInput.type = "text";
    nameInput.name = "name";
    nameInput.value = task?.summary || "";
    nameInput.required = true;
    nameLabel.appendChild(nameInput);
    form.appendChild(nameLabel);

    // Description
    const descLabel = document.createElement("label");
    descLabel.textContent = "Description";
    const descInput = document.createElement("input");
    descInput.type = "text";
    descInput.name = "description";
    descInput.value = task?.description || "";
    descLabel.appendChild(descInput);
    form.appendChild(descLabel);

    // Due date
    const dueLabel = document.createElement("label");
    dueLabel.textContent = "Due date";
    const dueInput = document.createElement("input");
    dueInput.type = "date";
    dueInput.name = "due_date";
    dueInput.value = task?.due || "";
    dueLabel.appendChild(dueInput);
    form.appendChild(dueLabel);

    // Recurrence fieldset
    const fieldset = document.createElement("fieldset");
    fieldset.className = "recurrence";
    const legend = document.createElement("legend");
    legend.textContent = "Recurrence";
    fieldset.appendChild(legend);

    const freqLabel = document.createElement("label");
    freqLabel.textContent = "Frequency";
    const freqSelect = document.createElement("select");
    freqSelect.name = "freq";
    for (const opt of ["none", "daily", "weekly", "monthly", "yearly"]) {
      const option = document.createElement("option");
      option.value = opt;
      option.textContent = opt.charAt(0).toUpperCase() + opt.slice(1);
      if (rrule.freq === opt) option.selected = true;
      freqSelect.appendChild(option);
    }
    freqLabel.appendChild(freqSelect);
    fieldset.appendChild(freqLabel);

    const intervalLabel = document.createElement("label");
    intervalLabel.className = "interval-label";
    intervalLabel.textContent = "Every N";
    const intervalInput = document.createElement("input");
    intervalInput.type = "number";
    intervalInput.name = "interval";
    intervalInput.min = "1";
    intervalInput.max = "99";
    intervalInput.value = String(rrule.interval);
    intervalLabel.appendChild(intervalInput);
    fieldset.appendChild(intervalLabel);

    // Day-of-week multi-select
    const daysDiv = document.createElement("div");
    daysDiv.className = "days-select";
    daysDiv.id = "days-select";
    daysDiv.style.display = rrule.freq === "weekly" ? "flex" : "none";

    for (const d of DAYS_OF_WEEK) {
      const chip = document.createElement("label");
      chip.className = "day-chip";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.name = "days";
      cb.value = d.value;
      if (rrule.days.includes(d.value)) cb.checked = true;
      chip.appendChild(cb);
      const span = document.createElement("span");
      span.textContent = d.label;
      chip.appendChild(span);
      daysDiv.appendChild(chip);
    }
    fieldset.appendChild(daysDiv);
    form.appendChild(fieldset);

    // Toggle days visibility on freq change
    freqSelect.addEventListener("change", () => {
      daysDiv.style.display = freqSelect.value === "weekly" ? "flex" : "none";
    });

    // Submit
    const formActions = document.createElement("div");
    formActions.className = "form-actions";
    const submitBtn = document.createElement("button");
    submitBtn.type = "submit";
    submitBtn.className = "btn-submit";
    submitBtn.textContent = (isEdit ? "Update" : "Add") + " Task";
    formActions.appendChild(submitBtn);
    form.appendChild(formActions);

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const freq = fd.get("freq");
      const interval = parseInt(fd.get("interval"), 10) || 1;
      const days = fd.getAll("days");
      const builtRrule = this._buildRrule(freq, interval, days);

      const data = {
        name: fd.get("name"),
        description: fd.get("description") || "",
        due_date: fd.get("due_date") || "",
        rrule: builtRrule,
      };

      if (isEdit) {
        await this._updateTask(task.uid, data);
      } else {
        await this._createTask(data);
      }
      this._view = "list";
      this._editTask = null;
      this._render();
    });

    container.appendChild(form);
  }

  _buildHistory(container) {
    const task = this._historyTask;
    if (!task) {
      const msg = document.createElement("div");
      msg.textContent = "No task selected";
      container.appendChild(msg);
      return;
    }

    const view = document.createElement("div");
    view.className = "history-view";

    const h3 = document.createElement("h3");
    h3.textContent = task.summary;
    view.appendChild(h3);

    const meta = document.createElement("div");
    meta.className = "history-meta";
    const statusSpan = document.createElement("span");
    statusSpan.textContent = "Status: " + task.status;
    meta.appendChild(statusSpan);
    if (task.due) {
      const dueSpan = document.createElement("span");
      dueSpan.textContent = "Due: " + task.due;
      meta.appendChild(dueSpan);
    }
    view.appendChild(meta);

    if (task.description) {
      const desc = document.createElement("p");
      desc.className = "history-desc";
      desc.textContent = task.description;
      view.appendChild(desc);
    }

    const note = document.createElement("div");
    note.className = "history-note";
    note.textContent = "Completion history is stored in the backend. Access via Developer Tools > States for the full record.";
    view.appendChild(note);

    container.appendChild(view);
  }

  // --- Styles ---

  _getStyles() {
    return `
      :host {
        --card-bg: var(--ha-card-background, var(--card-background-color, #fff));
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
      .btn-add, .btn-back {
        background: none;
        border: none;
        font-size: 1.4em;
        cursor: pointer;
        color: var(--accent);
        padding: 4px 8px;
        border-radius: 4px;
      }
      .btn-add:hover, .btn-back:hover {
        background: rgba(0,0,0,0.05);
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
        background: rgba(0,0,0,0.05);
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
        background: rgba(0,0,0,0.05);
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
        background: rgba(0,0,0,0.03);
        border-radius: 4px;
      }
    `;
  }
}

class RecurringTodosCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const root = this.shadowRoot;

    while (root.firstChild) root.removeChild(root.firstChild);

    const style = document.createElement("style");
    style.textContent = `
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
        background: var(--ha-card-background, var(--card-background-color, #fff));
        color: var(--primary-text-color, #212121);
      }
    `;
    root.appendChild(style);

    const editor = document.createElement("div");
    editor.className = "editor";

    // Entity picker
    const entityRow = document.createElement("div");
    entityRow.className = "row";
    const entityLabel = document.createElement("label");
    entityLabel.textContent = "Entity";
    entityRow.appendChild(entityLabel);

    const entityPicker = document.createElement("ha-entity-picker");
    entityPicker.hass = this._hass;
    entityPicker.value = this._config.entity || "";
    entityPicker.includeDomains = ["todo"];
    entityPicker.addEventListener("value-changed", (ev) => {
      this._config = { ...this._config, entity: ev.detail.value };
      this._dispatch();
    });
    entityRow.appendChild(entityPicker);
    editor.appendChild(entityRow);

    // Title override
    const titleRow = document.createElement("div");
    titleRow.className = "row";
    const titleLabel = document.createElement("label");
    titleLabel.textContent = "Title (optional)";
    titleRow.appendChild(titleLabel);

    const titleInput = document.createElement("input");
    titleInput.type = "text";
    titleInput.value = this._config.title || "";
    titleInput.placeholder = "Uses entity name if empty";
    titleInput.addEventListener("input", (ev) => {
      this._config = { ...this._config, title: ev.target.value };
      this._dispatch();
    });
    titleRow.appendChild(titleInput);
    editor.appendChild(titleRow);

    root.appendChild(editor);
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

customElements.define("recurring-todos-card-editor", RecurringTodosCardEditor);
customElements.define("recurring-todos-card", RecurringTodosCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "recurring-todos-card",
  name: "Recurring Todos",
  description: "Task list with recurring due dates, overdue highlighting, and completion history.",
});
