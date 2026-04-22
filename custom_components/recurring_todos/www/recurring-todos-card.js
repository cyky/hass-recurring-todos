const DAYS_OF_WEEK = [
  { value: "MO", label: "Mon" },
  { value: "TU", label: "Tue" },
  { value: "WE", label: "Wed" },
  { value: "TH", label: "Thu" },
  { value: "FR", label: "Fri" },
  { value: "SA", label: "Sat" },
  { value: "SU", label: "Sun" },
];

const REQUIRED_HA_ELEMENTS = [
  "ha-card",
  "ha-icon",
  "ha-icon-button",
  "ha-textfield",
  "ha-button",
  "ha-form",
];

let _haElementsReady = null;
function haElementsReady() {
  if (_haElementsReady === null) {
    _haElementsReady = Promise.all(
      REQUIRED_HA_ELEMENTS.map((name) => customElements.whenDefined(name))
    );
  }
  return _haElementsReady;
}

class RecurringTodosCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
    this._view = "list"; // list | add | edit | history
    this._editTask = null;
    this._historyTask = null;
    this._renderScheduled = false;
    this._lastStateSig = null;
  }

  _stateSignature() {
    const state = this._getState();
    if (!state) return "none";
    const items = state.attributes?.todo_items || [];
    const detail = state.attributes?.tasks_detail || [];
    return JSON.stringify({ items, detail });
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("Please define an entity");
    }
    this._config = config;
    this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._view === "add" || this._view === "edit") return;
    const sig = this._stateSignature();
    if (sig === this._lastStateSig) return;
    this._lastStateSig = sig;
    this._scheduleRender();
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

  _scheduleRender() {
    if (this._renderScheduled) return;
    if (!this._hass || !this._config.entity) return;
    this._renderScheduled = true;
    haElementsReady().then(() => {
      this._renderScheduled = false;
      this._render();
    });
  }

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

  _getTaskDetail(uid) {
    const state = this._getState();
    if (!state?.attributes?.tasks_detail) return null;
    return state.attributes.tasks_detail.find((t) => t.uid === uid) || null;
  }

  _isOverdue(task) {
    const overdueList = this._getOverdueTasks();
    return overdueList.some((t) => t.uid === task.uid);
  }

  _daysUntilDue(task) {
    if (!task.due) return null;
    const [y, m, d] = task.due.split("-").map(Number);
    if (!y || !m || !d) return null;
    const due = new Date(y, m - 1, d);
    if (isNaN(due.getTime())) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.round((due - today) / (1000 * 60 * 60 * 24));
  }

  _buildRrule(freq, interval, days, ends) {
    if (freq === "none") return "";
    let rule = "FREQ=" + freq.toUpperCase();
    if (interval && interval > 1) {
      rule += ";INTERVAL=" + String(interval);
    }
    if (freq === "weekly" && days && days.length > 0) {
      rule += ";BYDAY=" + days.join(",");
    }
    if (ends && ends.type === "until" && ends.until) {
      rule += ";UNTIL=" + ends.until.replace(/-/g, "");
    } else if (ends && ends.type === "count" && ends.count > 0) {
      rule += ";COUNT=" + String(ends.count);
    }
    return rule;
  }

  _parseRrule(rrule) {
    const result = {
      freq: "none",
      interval: 1,
      days: [],
      ends: { type: "never", until: "", count: 1 },
    };
    if (!rrule) return result;

    const parts = rrule.split(";");
    let sawUntil = false;
    for (const part of parts) {
      const [key, val] = part.split("=");
      if (key === "FREQ") result.freq = val.toLowerCase();
      if (key === "INTERVAL") result.interval = parseInt(val, 10);
      if (key === "BYDAY") result.days = val.split(",");
      if (key === "UNTIL") {
        const digits = val.slice(0, 8);
        if (/^\d{8}$/.test(digits)) {
          result.ends = {
            type: "until",
            until: digits.slice(0, 4) + "-" + digits.slice(4, 6) + "-" + digits.slice(6, 8),
            count: 1,
          };
          sawUntil = true;
        }
      }
      if (key === "COUNT" && !sawUntil) {
        result.ends = { type: "count", until: "", count: parseInt(val, 10) || 1 };
      }
    }
    return result;
  }

  _freqUnitLabel(freq, plural = true) {
    const map = plural
      ? { daily: "days", weekly: "weeks", monthly: "months", yearly: "years" }
      : { daily: "day", weekly: "week", monthly: "month", yearly: "year" };
    return map[freq] || "";
  }

  _iconButton(icon, { title, className, onClick } = {}) {
    const btn = document.createElement("ha-icon-button");
    if (className) btn.className = className;
    if (title) {
      btn.setAttribute("label", title);
      btn.setAttribute("title", title);
    }
    if (onClick) btn.addEventListener("click", onClick);
    const iconEl = document.createElement("ha-icon");
    iconEl.setAttribute("icon", icon);
    btn.appendChild(iconEl);
    return btn;
  }

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

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const root = this.shadowRoot;

    while (root.firstChild) root.removeChild(root.firstChild);

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

    const header = document.createElement("div");
    header.className = "card-header";

    const title = document.createElement("span");
    title.className = "title";
    title.textContent = this._config.title || state.attributes.friendly_name || "Recurring Todos";
    header.appendChild(title);

    if (this._view === "list") {
      header.appendChild(this._iconButton("mdi:plus", {
        className: "header-btn",
        title: "Add task",
        onClick: () => { this._view = "add"; this._render(); },
      }));
    } else {
      header.appendChild(this._iconButton("mdi:arrow-left", {
        className: "header-btn",
        title: "Back",
        onClick: () => { this._view = "list"; this._editTask = null; this._historyTask = null; this._render(); },
      }));
    }

    card.appendChild(header);

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
      const hasRrule = !!this._getTaskRrule(task.uid);

      const taskEl = document.createElement("div");
      taskEl.className = "task"
        + (overdue ? " overdue" : "")
        + (completed ? " completed" : "")
        + (daysUntil === 0 && !overdue ? " due-today" : "")
        + (daysUntil === 1 ? " due-tomorrow" : "");

      const main = document.createElement("div");
      main.className = "task-main";

      main.appendChild(this._iconButton(
        completed ? "mdi:checkbox-marked" : "mdi:checkbox-blank-outline",
        { className: "btn-complete", title: "Complete", onClick: () => this._completeTask(task.uid) }
      ));

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

      const dueBadges = document.createElement("div");
      dueBadges.className = "due-badges";

      if (hasRrule) {
        const recurIcon = document.createElement("ha-icon");
        recurIcon.className = "recurring-badge";
        recurIcon.setAttribute("icon", "mdi:repeat");
        dueBadges.appendChild(recurIcon);
      }

      if (daysUntil !== null) {
        let dueText = "";
        if (daysUntil < 0) dueText = Math.abs(daysUntil) + "d overdue";
        else if (daysUntil === 0) dueText = "Today";
        else if (daysUntil === 1) dueText = "Tomorrow";
        else dueText = daysUntil + "d";

        const dueLabel = document.createElement("span");
        dueLabel.className = "due-label"
          + (overdue ? " overdue" : "")
          + (daysUntil === 0 && !overdue ? " due-today" : "");
        dueLabel.textContent = dueText;
        dueBadges.appendChild(dueLabel);
      }
      main.appendChild(dueBadges);
      taskEl.appendChild(main);

      const actions = document.createElement("div");
      actions.className = "task-actions";

      actions.appendChild(this._iconButton("mdi:alarm", {
        title: "Snooze 1 day",
        onClick: () => this._snoozeTask(task.uid),
      }));
      actions.appendChild(this._iconButton("mdi:pencil", {
        title: "Edit",
        onClick: () => { this._editTask = task; this._view = "edit"; this._render(); },
      }));
      actions.appendChild(this._iconButton("mdi:history", {
        title: "History",
        onClick: () => { this._historyTask = task; this._view = "history"; this._render(); },
      }));
      actions.appendChild(this._iconButton("mdi:delete", {
        title: "Delete",
        onClick: () => this._showDeleteConfirm(actions, task.uid),
      }));

      taskEl.appendChild(actions);
      container.appendChild(taskEl);
    }
  }

  _showDeleteConfirm(actionsEl, uid) {
    while (actionsEl.firstChild) actionsEl.removeChild(actionsEl.firstChild);

    const confirmText = document.createElement("span");
    confirmText.className = "confirm-text";
    confirmText.textContent = "Delete?";
    actionsEl.appendChild(confirmText);

    actionsEl.appendChild(this._iconButton("mdi:check", {
      className: "confirm-yes",
      title: "Confirm delete",
      onClick: () => this._deleteTask(uid),
    }));
    actionsEl.appendChild(this._iconButton("mdi:close", {
      className: "confirm-no",
      title: "Cancel",
      onClick: () => this._render(),
    }));
  }

  _buildForm(container, task) {
    const rrule = this._parseRrule(task ? this._getTaskRrule(task.uid) : null);
    const isEdit = !!task;

    const form = document.createElement("div");
    form.className = "form";

    const nameInput = document.createElement("ha-textfield");
    nameInput.setAttribute("label", "Name");
    nameInput.setAttribute("required", "");
    nameInput.value = task?.summary || "";
    form.appendChild(nameInput);

    const descInput = document.createElement("ha-textfield");
    descInput.setAttribute("label", "Description");
    descInput.value = task?.description || "";
    form.appendChild(descInput);

    const dueInput = document.createElement("ha-textfield");
    dueInput.setAttribute("label", "Due date");
    dueInput.setAttribute("type", "date");
    dueInput.value = task?.due || "";
    form.appendChild(dueInput);

    const fieldset = document.createElement("div");
    fieldset.className = "recurrence";

    const repeatsRow = document.createElement("label");
    repeatsRow.className = "repeats-toggle";
    const repeatsCb = document.createElement("input");
    repeatsCb.type = "checkbox";
    repeatsCb.checked = rrule.freq !== "none";
    repeatsRow.appendChild(repeatsCb);
    const repeatsText = document.createElement("span");
    repeatsText.textContent = "Repeats";
    repeatsRow.appendChild(repeatsText);
    fieldset.appendChild(repeatsRow);

    const details = document.createElement("div");
    details.className = "recurrence-details";
    details.style.display = repeatsCb.checked ? "flex" : "none";

    const everyRow = document.createElement("div");
    everyRow.className = "every-row";
    const everyLabel = document.createElement("span");
    everyLabel.textContent = "Every";
    everyRow.appendChild(everyLabel);

    const intervalInput = document.createElement("input");
    intervalInput.className = "interval-input";
    intervalInput.type = "number";
    intervalInput.min = "1";
    intervalInput.max = "99";
    intervalInput.value = String(rrule.interval);
    everyRow.appendChild(intervalInput);

    const unitSelect = document.createElement("select");
    unitSelect.className = "freq-select";
    const UNIT_OPTIONS = [
      { freq: "daily", label: "day" },
      { freq: "weekly", label: "week" },
      { freq: "monthly", label: "month" },
      { freq: "yearly", label: "year" },
    ];
    const activeFreq = rrule.freq === "none" ? "weekly" : rrule.freq;
    const updateUnitLabels = () => {
      const n = parseInt(intervalInput.value, 10) || 1;
      for (let i = 0; i < UNIT_OPTIONS.length; i++) {
        unitSelect.options[i].textContent = n > 1 ? UNIT_OPTIONS[i].label + "s" : UNIT_OPTIONS[i].label;
      }
    };
    for (const opt of UNIT_OPTIONS) {
      const o = document.createElement("option");
      o.value = opt.freq;
      o.textContent = opt.label;
      unitSelect.appendChild(o);
    }
    unitSelect.value = activeFreq;
    updateUnitLabels();
    everyRow.appendChild(unitSelect);
    details.appendChild(everyRow);

    const daysDiv = document.createElement("div");
    daysDiv.className = "days-select";
    daysDiv.style.display = activeFreq === "weekly" ? "flex" : "none";
    const dayCheckboxes = [];
    for (const d of DAYS_OF_WEEK) {
      const chip = document.createElement("label");
      chip.className = "day-chip";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = d.value;
      if (rrule.days.includes(d.value)) cb.checked = true;
      dayCheckboxes.push(cb);
      chip.appendChild(cb);
      const span = document.createElement("span");
      span.textContent = d.label;
      chip.appendChild(span);
      daysDiv.appendChild(chip);
    }
    details.appendChild(daysDiv);

    const endsLegend = document.createElement("div");
    endsLegend.className = "ends-legend";
    endsLegend.textContent = "Ends";
    details.appendChild(endsLegend);

    const endsGroup = document.createElement("div");
    endsGroup.className = "ends-group";

    const endsRadios = {};
    const makeEndsRow = (type, labelText, extraEl) => {
      const row = document.createElement("label");
      row.className = "ends-row";
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "ends-" + (isEdit ? task.uid : "new");
      radio.value = type;
      endsRadios[type] = radio;
      row.appendChild(radio);
      const text = document.createElement("span");
      text.textContent = labelText;
      row.appendChild(text);
      if (extraEl) row.appendChild(extraEl);
      endsGroup.appendChild(row);
    };

    const untilInput = document.createElement("input");
    untilInput.type = "date";
    untilInput.className = "ends-until";
    untilInput.value = rrule.ends.until || "";

    const countInput = document.createElement("input");
    countInput.type = "number";
    countInput.min = "1";
    countInput.max = "999";
    countInput.className = "ends-count";
    countInput.value = String(rrule.ends.count || 1);
    const countSuffix = document.createElement("span");
    countSuffix.className = "ends-count-suffix";
    countSuffix.textContent = "occurrences";
    const countWrap = document.createElement("span");
    countWrap.className = "ends-count-wrap";
    countWrap.appendChild(countInput);
    countWrap.appendChild(countSuffix);

    makeEndsRow("never", "Never");
    makeEndsRow("until", "On", untilInput);
    makeEndsRow("count", "After", countWrap);

    endsRadios[rrule.ends.type].checked = true;
    const syncEndsEnabled = () => {
      untilInput.disabled = !endsRadios.until.checked;
      countInput.disabled = !endsRadios.count.checked;
    };
    syncEndsEnabled();
    for (const r of Object.values(endsRadios)) {
      r.addEventListener("change", syncEndsEnabled);
    }
    untilInput.addEventListener("focus", () => {
      endsRadios.until.checked = true;
      syncEndsEnabled();
    });
    countInput.addEventListener("focus", () => {
      endsRadios.count.checked = true;
      syncEndsEnabled();
    });

    details.appendChild(endsGroup);
    fieldset.appendChild(details);
    form.appendChild(fieldset);

    repeatsCb.addEventListener("change", () => {
      details.style.display = repeatsCb.checked ? "flex" : "none";
    });
    unitSelect.addEventListener("change", () => {
      daysDiv.style.display = unitSelect.value === "weekly" ? "flex" : "none";
    });
    intervalInput.addEventListener("input", updateUnitLabels);

    const formActions = document.createElement("div");
    formActions.className = "form-actions";
    const submitBtn = document.createElement("ha-button");
    submitBtn.setAttribute("raised", "");
    submitBtn.textContent = (isEdit ? "Update" : "Add") + " Task";
    formActions.appendChild(submitBtn);
    form.appendChild(formActions);

    const submit = async () => {
      if (!nameInput.value || !nameInput.value.trim()) {
        nameInput.setAttribute("error", "");
        nameInput.focus();
        return;
      }
      const days = dayCheckboxes.filter((cb) => cb.checked).map((cb) => cb.value);
      const interval = parseInt(intervalInput.value, 10) || 1;
      let freq = "none";
      let ends = { type: "never" };
      if (repeatsCb.checked) {
        freq = unitSelect.value;
        if (endsRadios.until.checked) {
          if (!untilInput.value) {
            untilInput.focus();
            return;
          }
          ends = { type: "until", until: untilInput.value };
        } else if (endsRadios.count.checked) {
          const n = parseInt(countInput.value, 10);
          if (!n || n < 1) {
            countInput.focus();
            return;
          }
          ends = { type: "count", count: n };
        }
      }
      const data = {
        name: nameInput.value.trim(),
        description: descInput.value || "",
        due_date: dueInput.value || "",
        rrule: this._buildRrule(freq, interval, days, ends),
      };

      if (isEdit) {
        await this._updateTask(task.uid, data);
      } else {
        await this._createTask(data);
      }
      this._view = "list";
      this._editTask = null;
      this._render();
    };

    submitBtn.addEventListener("click", submit);
    for (const el of [nameInput, descInput, dueInput, intervalInput, untilInput, countInput]) {
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          submit();
        }
      });
    }

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

    const detail = this._getTaskDetail(task.uid);
    const history = detail?.completion_history || [];

    if (history.length === 0) {
      const empty = document.createElement("div");
      empty.className = "history-note";
      empty.textContent = "No completions yet.";
      view.appendChild(empty);
    } else {
      const heading = document.createElement("h4");
      heading.className = "history-heading";
      heading.textContent = "Completions (" + history.length + ")";
      view.appendChild(heading);

      const list = document.createElement("ul");
      list.className = "history-list";
      const recent = [...history].reverse().slice(0, 50);
      for (const entry of recent) {
        const li = document.createElement("li");
        const date = new Date(entry.completed_at);
        li.textContent = date.toLocaleDateString(undefined, {
          year: "numeric",
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
        list.appendChild(li);
      }
      view.appendChild(list);

      if (history.length > 50) {
        const more = document.createElement("div");
        more.className = "history-note";
        more.textContent = "Showing 50 of " + history.length + " completions.";
        view.appendChild(more);
      }
    }

    container.appendChild(view);
  }

  _getStyles() {
    return `
      :host {
        --text-primary: var(--primary-text-color, #212121);
        --text-secondary: var(--secondary-text-color, #727272);
        --accent: var(--primary-color, #03a9f4);
        --error: var(--error-color, #db4437);
        --warning: var(--warning-color, #ffa600);
        --divider: var(--divider-color, #e0e0e0);
        --card-background: var(--input-fill-color, var(--card-background-color, #f5f5f5));
      }
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 8px 4px 16px;
        font-size: 1.2em;
        font-weight: 500;
        color: var(--text-primary);
      }
      .card-header .header-btn {
        color: var(--accent);
      }
      .card-content {
        padding: 8px 16px 16px;
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
        gap: 4px;
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
      .task.due-today {
        background: rgba(255, 166, 0, 0.08);
        margin: 0 -16px;
        padding: 8px 16px;
      }
      .task.due-tomorrow {
        background: rgba(255, 166, 0, 0.04);
        margin: 0 -16px;
        padding: 8px 16px;
      }
      .due-badges {
        display: flex;
        align-items: center;
        gap: 4px;
        flex-shrink: 0;
      }
      .recurring-badge {
        --mdc-icon-size: 14px;
        color: var(--text-secondary);
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
      .due-label.due-today {
        color: var(--warning);
        font-weight: 500;
      }
      .task.completed .btn-complete {
        color: var(--accent);
      }
      .task-actions {
        display: flex;
        align-items: center;
        gap: 0;
        padding-left: 40px;
        margin-top: 2px;
      }
      .task-actions ha-icon-button {
        --mdc-icon-button-size: 36px;
        --mdc-icon-size: 18px;
      }
      .confirm-text {
        font-size: 0.85em;
        color: var(--error);
        font-weight: 500;
        line-height: 36px;
        margin-right: 4px;
      }
      .confirm-yes {
        color: var(--error);
      }
      .confirm-no {
        color: var(--text-secondary);
      }
      .form {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .form ha-textfield {
        width: 100%;
      }
      .recurrence {
        border: 1px solid var(--divider);
        border-radius: 4px;
        padding: 12px;
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .repeats-toggle {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.95em;
        color: var(--text-primary);
        cursor: pointer;
      }
      .recurrence-details {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .every-row {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--text-primary);
        font-size: 0.95em;
      }
      .interval-input {
        width: 64px;
        padding: 8px 10px;
        font-size: 1em;
        color: var(--text-primary);
        background: var(--card-background);
        border: 1px solid var(--divider);
        border-radius: 4px;
        color-scheme: light dark;
      }
      .freq-select {
        padding: 8px 10px;
        font-size: 1em;
        color: var(--text-primary);
        background: var(--card-background);
        border: 1px solid var(--divider);
        border-radius: 4px;
        color-scheme: light dark;
      }
      .ends-legend {
        font-size: 0.85em;
        color: var(--text-secondary);
      }
      .ends-group {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .ends-row {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--text-primary);
        font-size: 0.9em;
        cursor: pointer;
      }
      .ends-until,
      .ends-count {
        padding: 6px 8px;
        font-size: 0.95em;
        color: var(--text-primary);
        background: var(--card-background);
        border: 1px solid var(--divider);
        border-radius: 4px;
        color-scheme: light dark;
      }
      .ends-count {
        width: 64px;
      }
      .ends-count-wrap {
        display: inline-flex;
        align-items: center;
        gap: 6px;
      }
      .ends-count-suffix {
        font-size: 0.9em;
        color: var(--text-secondary);
      }
      .ends-until:disabled,
      .ends-count:disabled {
        opacity: 0.5;
      }
      .days-select {
        flex-wrap: wrap;
        gap: 4px;
      }
      .day-chip {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        background: var(--secondary-background-color, rgba(128,128,128,0.15));
        padding: 4px 8px;
        border-radius: 12px;
        cursor: pointer;
        font-size: 0.85em;
        color: var(--text-primary);
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
      .history-heading {
        font-size: 0.9em;
        font-weight: 500;
        color: var(--text-primary);
        margin: 12px 0 4px;
      }
      .history-list {
        list-style: none;
        padding: 0;
        margin: 4px 0;
      }
      .history-list li {
        padding: 6px 0;
        border-bottom: 1px solid var(--divider);
        font-size: 0.85em;
        color: var(--text-primary);
      }
      .history-list li:last-child {
        border-bottom: none;
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
    this._renderScheduled = false;
  }

  setConfig(config) {
    this._config = { ...config };
    this._scheduleRender();
  }

  set hass(hass) {
    this._hass = hass;
    this._scheduleRender();
  }

  _scheduleRender() {
    if (this._renderScheduled) return;
    if (!this._hass) return;
    this._renderScheduled = true;
    haElementsReady().then(() => {
      this._renderScheduled = false;
      this._render();
    });
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
        gap: 12px;
        padding: 8px 0;
      }
    `;
    root.appendChild(style);

    const editor = document.createElement("div");
    editor.className = "editor";

    const schema = [
      { name: "entity", required: true, selector: { entity: { domain: "todo" } } },
      { name: "title", selector: { text: {} } },
    ];
    const labels = { entity: "Entity", title: "Title (optional)" };

    const form = document.createElement("ha-form");
    form.hass = this._hass;
    form.schema = schema;
    form.data = { entity: this._config.entity || "", title: this._config.title || "" };
    form.computeLabel = (s) => labels[s.name] || s.name;
    form.addEventListener("value-changed", (ev) => {
      const v = ev.detail.value || {};
      this._config = { ...this._config, entity: v.entity || "", title: v.title || "" };
      this._dispatch();
    });
    editor.appendChild(form);

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

if (!customElements.get("recurring-todos-card-editor")) {
  customElements.define("recurring-todos-card-editor", RecurringTodosCardEditor);
}
if (!customElements.get("recurring-todos-card")) {
  customElements.define("recurring-todos-card", RecurringTodosCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "recurring-todos-card")) {
  window.customCards.push({
    type: "recurring-todos-card",
    name: "Recurring Todos",
    description: "Task list with recurring due dates, overdue highlighting, and completion history.",
  });
}
