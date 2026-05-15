/**
 * Regression test: REQUIRED_HA_ELEMENTS must only list elements used in the
 * main card render path. The card blocks rendering on
 * customElements.whenDefined() for each entry, so editor-only elements
 * (e.g. ha-form) would stall the dashboard card forever — HA does not
 * register editor-only elements until the config UI is opened.
 *
 * Run: node --test tests/test_card_required_elements.js
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SRC = fs.readFileSync(
  path.join(__dirname, "..", "custom_components", "recurring_todos", "www", "recurring-todos-card.js"),
  "utf8",
);

function extractRequired(src) {
  const m = src.match(/REQUIRED_HA_ELEMENTS\s*=\s*\[([\s\S]*?)\]/);
  assert.ok(m, "REQUIRED_HA_ELEMENTS array not found");
  return [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]);
}

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

describe("REQUIRED_HA_ELEMENTS gate", () => {
  const required = extractRequired(SRC);
  const cardBody = sliceClass(SRC, "RecurringTodosCard");
  const editorBody = sliceClass(SRC, "RecurringTodosCardEditor");

  it("is non-empty", () => {
    assert.ok(required.length > 0);
  });

  for (const tag of required) {
    it(`'${tag}' is used by the main card (not only the editor)`, () => {
      const usedInCard = cardBody.includes(`"${tag}"`);
      const usedInEditor = editorBody.includes(`"${tag}"`);
      assert.ok(
        usedInCard,
        `'${tag}' is in REQUIRED_HA_ELEMENTS but never used in RecurringTodosCard` +
          (usedInEditor
            ? ` (only used in editor — would stall dashboard render because HA does not pre-register editor-only elements)`
            : ""),
      );
    });
  }
});
