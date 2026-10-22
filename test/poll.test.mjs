import { test } from "node:test"; import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { pollPcts, pollError, postDebate } from "../landing/logic.mjs";
test("pollPcts soma 100 e trata zero", () => {
  assert.deepEqual(pollPcts({ lula: 0, flavio: 0, empate: 0 }), { n: 0, lula: 0, flavio: 0, empate: 0 });
  const p = pollPcts({ lula: 1, flavio: 1, empate: 1 }); assert.equal(p.lula + p.flavio + p.empate, 100); assert.equal(p.n, 3);
  assert.deepEqual(pollPcts({ lula: 3, flavio: 1, empate: 0 }), { n: 4, lula: 75, flavio: 25, empate: 0 });
  assert.equal(pollPcts({ lula: "2", flavio: -5 }).lula, 100);
});
test("pollError", () => { assert.match(pollError("devagar"), /minuto/); assert.match(pollError("encerrado"), /encerrad/); assert.match(pollError("x"), /Tente/); });
test("postDebate só com resultado", () => {
  assert.equal(postDebate(null, "lula"), null);
  assert.match(postDebate("lula", "lula"), /Lula.*acertou/);
  assert.match(postDebate("flavio", "lula"), /Flávio.*Não foi/);
  assert.match(postDebate("empate"), /empate/);
});
test("html: textos, ids e alt", () => {
  const h = readFileSync(new URL("../landing/index.html", import.meta.url), "utf8");
  for (const s of ["Quem vai mentir mais?", "MENTIRÔMETRO", 'id="sc-1"', 'id="sc-2"', 'id="sc-label"', "começa sexta, 21h20",
    "Cada frase na balança. Ao vivo.", "A gente checa. Você vê quem mente mais.", "Quem leva o Troféu Pinóquio?",
    "Faça seu palpite: quem vai mentir mais no debate? Na sexta, o Mentirômetro decide.", "Os dois empatam",
    "É só palpite, de brincadeira: não tem aposta nem dinheiro. Um palpite por navegador.", "mics-640.webp", "mics-960.jpg", "trofeu-320.webp", "trofeu-480.jpg", 'id="poll-post"'])
    assert.ok(h.includes(s), s);
  assert.ok(/alt="Ilustração de dois microfones/.test(h));
});
test("css: cores e corte rígido do Flávio", () => {
  const c = readFileSync(new URL("../landing/landing.css", import.meta.url), "utf8");
  assert.ok(c.includes("#2FBF71 50%,#F5D33B 50%")); assert.ok(c.includes("#E5484D"));
  assert.match(c, /prefers-reduced-motion: reduce\) \{ \.bh-art img \{ animation: none/);
});
