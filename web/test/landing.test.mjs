import { test } from "node:test"; import assert from "node:assert/strict";
import { normBR, validEmail, countdown, validate } from "../landing/logic.mjs";
test("normBR", () => {
  assert.equal(normBR("(11) 91234-5678"), "+5511912345678");
  assert.equal(normBR("+55 21 3123-4567"), "+552131234567");
  assert.equal(normBR("011912345678"), "+5511912345678");
  assert.equal(normBR("1191234"), null); assert.equal(normBR("11812345678"), null);
});
test("email", () => { assert.ok(validEmail("a@b.co")); assert.ok(!validEmail("a@b")); assert.ok(!validEmail("x y@b.com")); });
test("countdown", () => {
  const s = Date.parse("2026-10-23T21:20:00-03:00");
  assert.deepEqual(countdown(s, s - 90061000), { live: false, d: 1, h: 1, m: 1, s: 1 });
  assert.equal(countdown(s, s + 5).live, true);
});
test("validate consent", () => {
  assert.match(validate({ email: "a@b.co", cEmail: false }).err, /autoriza/);
  assert.equal(validate({ wa: "11912345678", cWa: true }).wa, "+5511912345678");
  assert.match(validate({}).err, /Informe/);
});
