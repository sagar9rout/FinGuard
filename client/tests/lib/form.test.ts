import assert from "node:assert/strict";
import { test } from "node:test";
import { emptyForm, sampleForm, toRequest, validateForm } from "../../src/lib/form.ts";

test("the sample form is valid and the empty form is not", () => {
  assert.deepEqual(validateForm(sampleForm()), {});
  const e = validateForm(emptyForm());
  for (const k of ["balance", "reserve", "purchaseAmount"] as const) assert.ok(e[k], k);
});

test("money must be plain decimal text: no commas, signs, exponents or symbols", () => {
  for (const bad of ["1,000", "-5", "+5", "1e3", "₹100", "12.", ".5", "0x10", "1 000"]) {
    assert.ok(validateForm({ ...sampleForm(), purchaseAmount: bad }).purchaseAmount, bad);
  }
  assert.equal(validateForm({ ...sampleForm(), purchaseAmount: "0.00" }).purchaseAmount, "The purchase amount must be greater than zero.");
});

test("dates must be real calendar dates and the deadline cannot precede the analysis date", () => {
  assert.ok(validateForm({ ...sampleForm(), asOf: "2026-02-30" }).asOf);
  assert.equal(validateForm({ ...sampleForm(), asOf: "2028-02-29" }).asOf, undefined);
  assert.ok(validateForm({ ...sampleForm(), desiredBy: "2026-10-01" }).desiredBy);
});

test("at least one payment approach is required", () => {
  const v = sampleForm();
  const none = { ...v, methods: { ...v.methods, full_payment: false, installments: false, partial: false, wait: false, full_payment_with_spending_changes: false } };
  assert.ok(validateForm(none).methods);
});

test("the request keeps money as strings and omits blank optional fields", () => {
  const req = toRequest(sampleForm());
  assert.equal(typeof req.profile.current_available_balance, "string");
  assert.equal(typeof req.purchase.amount, "string");
  const blank = toRequest({ ...sampleForm(), desiredBy: "", balanceAsOf: "", maxInstallmentDays: "" });
  assert.equal("desired_completion_date" in blank.purchase, false);
  assert.equal("balance_as_of" in blank.profile, false);
  assert.equal("max_installment_term_days" in blank.preferences, false);
});
