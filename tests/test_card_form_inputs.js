/**
 * Regression test: add/edit-task form must not rely on lazy-loaded HA elements
 * for its visible inputs. `ha-textfield` is registered only after HA loads its
 * forms module, which does not happen on dashboards that do not already use
 * those elements. When the card renders `<ha-textfield>` before HA registers
 * it, the element stays as an inert unknown HTMLElement with no shadow DOM —
 * the Name, Description, and Due date inputs disappear, leaving only the
 * native "Repeats" checkbox visible. See screenshot in regression report.
 *
 * Native `<input>` elements always render, so the form must use them for
 * required user-input fields.
 *
 * Run: node --test tests/test_card_form_inputs.js
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SRC = fs.readFileSync(
  path.join(__dirname, "..", "custom_components", "recurring_todos", "www", "recurring-todos-card.js"),
  "utf8",
);

function sliceClass(src, name) {
  const start = src.indexOf(`class ${name}`);
  assert.ok(start >= 0, `class ${name} not found`);
  let depth = 0;
  let i = src.indexOf("{", start);
  const begin = i;
  for (; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return src.slice(begin, i + 1);
    }
  }
  throw new Error(`unterminated class ${name}`);
}

describe("task form inputs", () => {
  const cardBody = sliceClass(SRC, "RecurringTodosCard");

  it("main card does not createElement('ha-textfield')", () => {
    assert.ok(
      !cardBody.includes('createElement("ha-textfield")') &&
        !cardBody.includes("createElement('ha-textfield')"),
      "RecurringTodosCard uses <ha-textfield> for form inputs, but HA does not pre-register that element on dashboards. It stays as an inert unknown element with no shadow DOM, so the Name/Description/Due date fields render invisible. Use native <input> instead.",
    );
  });
});
