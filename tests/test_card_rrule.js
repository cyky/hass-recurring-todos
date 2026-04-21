/**
 * Tests for RRULE generation/parsing logic from recurring-todos-card.js.
 *
 * Run: node --test tests/test_card_rrule.js
 */

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");

// Extract pure functions from the card (same logic, standalone for testing)
function buildRrule(freq, interval, days, ends) {
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

function parseRrule(rrule) {
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

  it("appends UNTIL in YYYYMMDD form", () => {
    assert.equal(
      buildRrule("weekly", 1, [], { type: "until", until: "2026-12-31" }),
      "FREQ=WEEKLY;UNTIL=20261231"
    );
  });

  it("appends COUNT", () => {
    assert.equal(
      buildRrule("monthly", 1, [], { type: "count", count: 5 }),
      "FREQ=MONTHLY;COUNT=5"
    );
  });

  it("combines interval, BYDAY, and COUNT", () => {
    assert.equal(
      buildRrule("weekly", 2, ["MO", "FR"], { type: "count", count: 3 }),
      "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,FR;COUNT=3"
    );
  });

  it("omits UNTIL when date missing", () => {
    assert.equal(
      buildRrule("daily", 1, [], { type: "until", until: "" }),
      "FREQ=DAILY"
    );
  });

  it("omits COUNT when zero", () => {
    assert.equal(
      buildRrule("daily", 1, [], { type: "count", count: 0 }),
      "FREQ=DAILY"
    );
  });
});

// --- parseRrule tests ---

describe("parseRrule", () => {
  const defaults = {
    freq: "none",
    interval: 1,
    days: [],
    ends: { type: "never", until: "", count: 1 },
  };

  it("returns defaults for null input", () => {
    assert.deepEqual(parseRrule(null), defaults);
  });

  it("returns defaults for empty string", () => {
    assert.deepEqual(parseRrule(""), defaults);
  });

  it("parses daily rule", () => {
    const result = parseRrule("FREQ=DAILY");
    assert.equal(result.freq, "daily");
    assert.equal(result.interval, 1);
    assert.equal(result.ends.type, "never");
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

  it("parses COUNT", () => {
    const result = parseRrule("FREQ=WEEKLY;COUNT=10");
    assert.equal(result.ends.type, "count");
    assert.equal(result.ends.count, 10);
  });

  it("parses UNTIL into YYYY-MM-DD", () => {
    const result = parseRrule("FREQ=MONTHLY;UNTIL=20270101");
    assert.equal(result.ends.type, "until");
    assert.equal(result.ends.until, "2027-01-01");
  });

  it("parses UNTIL with datetime suffix", () => {
    const result = parseRrule("FREQ=DAILY;UNTIL=20260101T000000Z");
    assert.equal(result.ends.type, "until");
    assert.equal(result.ends.until, "2026-01-01");
  });

  it("UNTIL wins when both UNTIL and COUNT present", () => {
    const result = parseRrule("FREQ=DAILY;UNTIL=20260101;COUNT=5");
    assert.equal(result.ends.type, "until");
    assert.equal(result.ends.until, "2026-01-01");
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

  it("weekly with days and count roundtrips", () => {
    const days = ["MO", "FR"];
    const ends = { type: "count", count: 3 };
    const rrule = buildRrule("weekly", 1, days, ends);
    const parsed = parseRrule(rrule);
    assert.equal(parsed.freq, "weekly");
    assert.deepEqual(parsed.days, days);
    assert.equal(parsed.ends.type, "count");
    assert.equal(parsed.ends.count, 3);
  });

  it("yearly with until roundtrips", () => {
    const ends = { type: "until", until: "2030-06-15" };
    const rrule = buildRrule("yearly", 1, [], ends);
    const parsed = parseRrule(rrule);
    assert.equal(parsed.freq, "yearly");
    assert.equal(parsed.ends.type, "until");
    assert.equal(parsed.ends.until, "2030-06-15");
  });
});
