/**
 * Regression test: card render must not be gated on customElements.whenDefined()
 * for HA elements. Doing so stalls the dashboard whenever an awaited element
 * (e.g. ha-textfield, ha-form) isn't pre-registered — HA loads form-only
 * elements lazily, so the gate's promise never resolves and the card never
 * paints. Web components upgrade in place anyway: createElement returns an
 * unknown element that becomes the right one once HA registers it.
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

describe("card render gate", () => {
  it("does not call customElements.whenDefined() anywhere", () => {
    assert.ok(
      !SRC.includes("whenDefined("),
      "customElements.whenDefined() is back — it will stall card render if HA hasn't pre-registered the awaited element. Render unconditionally and rely on web component upgrade instead.",
    );
  });

  it("does not declare a REQUIRED_HA_ELEMENTS list", () => {
    assert.ok(
      !SRC.includes("REQUIRED_HA_ELEMENTS"),
      "REQUIRED_HA_ELEMENTS reintroduced — same stall risk as the whenDefined() gate.",
    );
  });
});
