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
import { pollPct, pollLabel, validPick } from "../landing/logic.mjs";
test("pollPct soma 100 e trata vazio", () => {
  assert.deepEqual(pollPct({}), { total: 0, lula: 0, flavio: 0, empate: 0 });
  const p = pollPct({ lula: 1, flavio: 1, empate: 1 }); assert.equal(p.lula + p.flavio + p.empate, 100); assert.equal(p.total, 3);
  assert.deepEqual(pollPct({ lula: 3, flavio: 1, empate: 0 }), { total: 4, lula: 75, flavio: 25, empate: 0 });
  assert.equal(pollPct({ lula: -5, flavio: "2" }).flavio, 100);
});
test("pollLabel / validPick", () => {
  assert.equal(pollLabel(1), "1 palpite"); assert.equal(pollLabel(1234), "1.234 palpites");
  assert.ok(validPick("empate")); assert.ok(!validPick("bolsonaro")); assert.ok(!validPick(undefined));
});
test("landing tem a enquete do Troféu Pinóquio com resultados escondidos", async () => {
  const { readFileSync } = await import("node:fs");
  const html = readFileSync(new URL("../landing/index.html", import.meta.url), "utf8");
  for (const k of ['data-pick="lula"', 'data-pick="flavio"', 'data-pick="empate"', 'id="pres" ', "trofeu-640.webp", 'data-hook="resultado-vs-palpite"']) assert.ok(html.includes(k), k);
  assert.match(html, /class="pres hidden"/);
  const css = readFileSync(new URL("../landing/landing.css", import.meta.url), "utf8");
  assert.match(css, /#2FBF71 50%,#F5D33B 50%/);
});
