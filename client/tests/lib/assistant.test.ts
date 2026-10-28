import assert from "node:assert/strict";
import { test } from "node:test";
import { ASSISTANT_DISCLOSURE, missingFields, nextQuestion, summarize } from "../../src/lib/assistant.ts";
import { emptyForm, sampleForm } from "../../src/lib/form.ts";

test("the assistant asks for the first missing required field, in order", () => {
  assert.equal(nextQuestion(emptyForm())?.field, "balance");
  assert.equal(nextQuestion({ ...sampleForm(), reserve: "" })?.field, "reserve");
  assert.equal(nextQuestion(sampleForm()), null);
  assert.deepEqual(missingFields(sampleForm()), []);
});

test("it says the engine decides, that it is not an AI model, and never states a verdict", () => {
  assert.match(ASSISTANT_DISCLOSURE, /not an AI model/);
  assert.match(ASSISTANT_DISCLOSURE, /engine alone determines/);
  const text = [ASSISTANT_DISCLOSURE, ...summarize(sampleForm()).map((l) => `${l.label} ${l.value}`)].join(" ").toLowerCase();
  for (const word of ["you can afford", "you cannot afford", "safe to buy", "should buy", "should wait"]) assert.equal(text.includes(word), false, word);
});

test("the summary reads entered values back as formatted text", () => {
  const lines = Object.fromEntries(summarize(sampleForm()).map((l) => [l.label, l.value]));
  assert.equal(lines["Purchase amount"], "INR\u00a012,000.00");
  assert.equal(summarize(emptyForm()).find((l) => l.label === "Purchase amount")?.value, "not entered yet");
});
