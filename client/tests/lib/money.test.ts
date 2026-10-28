import assert from "node:assert/strict";
import { test } from "node:test";
import { formatDate, formatMoney, isCanonicalDecimal, PLACEHOLDER } from "../../src/lib/money.ts";

const NB = " ";

test("pads to the currency exponent and groups digits", () => {
  assert.equal(formatMoney("84250.75", "USD"), `USD${NB}84,250.75`);
  assert.equal(formatMoney("5", "EUR"), `EUR${NB}5.00`);
  assert.equal(formatMoney("0.5", "EUR"), `EUR${NB}0.50`);
  assert.equal(formatMoney("1234567", "ZAR"), `ZAR${NB}1,234,567.00`);
});

test("INR uses Indian digit grouping", () => {
  assert.equal(formatMoney("1234567.5", "INR"), `INR${NB}12,34,567.50`);
  assert.equal(formatMoney("150000", "INR"), `INR${NB}1,50,000.00`);
  assert.equal(formatMoney("999", "INR"), `INR${NB}999.00`);
});

test("trailing zeros beyond the exponent are trimmed, never rounded", () => {
  assert.equal(formatMoney("15000.00", "INR"), `INR${NB}15,000.00`);
  assert.equal(formatMoney("15000.000000", "INR"), `INR${NB}15,000.00`);
  // Digits beyond the exponent that are NOT zero are shown, not rounded away.
  assert.equal(formatMoney("10.005", "USD"), `USD${NB}10.005`);
  assert.equal(formatMoney("10.999", "USD"), `USD${NB}10.999`);
});

test("large and long values keep every digit (no floating point)", () => {
  assert.equal(formatMoney("999999999999999.9999999999", "USD"), `USD${NB}999,999,999,999,999.9999999999`);
  assert.equal(formatMoney("9007199254740993.01", "USD"), `USD${NB}9,007,199,254,740,993.01`);
  assert.equal(formatMoney("0.1", "USD"), `USD${NB}0.10`);
});

test("negative and zero values", () => {
  assert.equal(formatMoney("-1000", "USD"), `−USD${NB}1,000.00`);
  assert.equal(formatMoney("-0", "USD"), `USD${NB}0.00`);
  assert.equal(formatMoney("0", "USD"), `USD${NB}0.00`);
  assert.equal(formatMoney("-0.00", "USD"), `USD${NB}0.00`);
});

test("unknown currency: no padding or invented exponent, code still shown", () => {
  assert.equal(formatMoney("12.5", "JPY"), `JPY${NB}12.5`);
  assert.equal(formatMoney("12", "JPY"), `JPY${NB}12`);
});

test("non-canonical input is rejected to a placeholder, never guessed", () => {
  for (const bad of ["", "abc", "1e5", "1,000", "NaN", " 1", "1.", ".5", "+5", "--1", "1.2.3"]) {
    assert.equal(formatMoney(bad, "USD"), PLACEHOLDER, JSON.stringify(bad));
    assert.equal(isCanonicalDecimal(bad), false, JSON.stringify(bad));
  }
});

test("prototype-pollution style currency names are treated as unknown", () => {
  assert.equal(formatMoney("1", "constructor"), `constructor${NB}1`);
  assert.equal(formatMoney("1", "__proto__"), `__proto__${NB}1`);
});

test("formatDate is pure string handling", () => {
  assert.equal(formatDate("2026-10-24"), "24 Oct 2026");
  assert.equal(formatDate("2027-01-07"), "7 Jan 2027");
  assert.equal(formatDate("2026-13-01"), "2026-13-01");
  assert.equal(formatDate("not a date"), "not a date");
  assert.equal(formatDate("2026-10-00"), "2026-10-00");
});
