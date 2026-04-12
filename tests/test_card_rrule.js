/**
 * Tests for RRULE generation/parsing logic from recurring-todos-card.js.
 *
 * Run: node --test tests/test_card_rrule.js
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");

// Extract pure functions from the card (same logic, standalone for testing)
function buildRrule(freq, interval, days) {
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

function parseRrule(rrule) {
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

// --- buildRrule tests ---

describe("buildRrule", () => {
  it("returns empty string for none frequency", () => {
    assert.equal(buildRrule("none", 1, []), "");
  });

  it("generates daily rule", () => {
    assert.equal(buildRrule("daily", 1, []), "FREQ=DAILY");
  });

  it("generates daily rule with interval", () => {
    assert.equal(buildRrule("daily", 3, []), "FREQ=DAILY;INTERVAL=3");
  });

  it("generates weekly rule with days", () => {
    assert.equal(
      buildRrule("weekly", 1, ["MO", "WE", "FR"]),
      "FREQ=WEEKLY;BYDAY=MO,WE,FR"
    );
  });

  it("generates weekly rule with interval and days", () => {
    assert.equal(
      buildRrule("weekly", 2, ["TU", "TH"]),
      "FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH"
    );
  });

  it("generates monthly rule", () => {
    assert.equal(buildRrule("monthly", 1, []), "FREQ=MONTHLY");
  });

  it("generates monthly rule with interval", () => {
    assert.equal(buildRrule("monthly", 2, []), "FREQ=MONTHLY;INTERVAL=2");
  });

  it("generates yearly rule", () => {
    assert.equal(buildRrule("yearly", 1, []), "FREQ=YEARLY");
  });

  it("ignores days for non-weekly frequencies", () => {
    assert.equal(buildRrule("daily", 1, ["MO"]), "FREQ=DAILY");
  });
});

// --- parseRrule tests ---

describe("parseRrule", () => {
  it("returns defaults for null input", () => {
    assert.deepEqual(parseRrule(null), { freq: "none", interval: 1, days: [] });
  });

  it("returns defaults for empty string", () => {
    assert.deepEqual(parseRrule(""), { freq: "none", interval: 1, days: [] });
  });

  it("parses daily rule", () => {
    const result = parseRrule("FREQ=DAILY");
    assert.equal(result.freq, "daily");
    assert.equal(result.interval, 1);
  });

  it("parses weekly rule with days", () => {
    const result = parseRrule("FREQ=WEEKLY;BYDAY=MO,WE");
    assert.equal(result.freq, "weekly");
    assert.deepEqual(result.days, ["MO", "WE"]);
  });

  it("parses rule with interval", () => {
    const result = parseRrule("FREQ=MONTHLY;INTERVAL=3");
    assert.equal(result.freq, "monthly");
    assert.equal(result.interval, 3);
  });
});

// --- Roundtrip tests ---

describe("roundtrip", () => {
  it("daily roundtrips", () => {
    const rrule = buildRrule("daily", 1, []);
    const parsed = parseRrule(rrule);
    assert.equal(parsed.freq, "daily");
    assert.equal(parsed.interval, 1);
  });

  it("weekly with days roundtrips", () => {
    const days = ["MO", "FR"];
    const rrule = buildRrule("weekly", 1, days);
    const parsed = parseRrule(rrule);
    assert.equal(parsed.freq, "weekly");
    assert.deepEqual(parsed.days, days);
  });

  it("monthly with interval roundtrips", () => {
    const rrule = buildRrule("monthly", 3, []);
    const parsed = parseRrule(rrule);
    assert.equal(parsed.freq, "monthly");
    assert.equal(parsed.interval, 3);
  });
});
