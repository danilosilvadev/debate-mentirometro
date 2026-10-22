import test from 'node:test'
import assert from 'node:assert/strict'
import { lastVerified, debateClock } from '../js/placar.mjs'
const f = { titulo: 'IBGE', url: 'https://sidra.ibge.gov.br/x' }
const it = (t, veredito, fonte) => ({ kind: 'claim', t, quem: '1', text: 'x' + t, claim: { veredito, ...(fonte ? { fonte } : {}) } })
test('legenda: última checagem comprovada por fonte', () => {
  const items = [it(1000, 'falso', f), it(2000, 'verdadeiro', f), it(3000, 'falso'), it(4000, 'checando', f), { kind: 'proposta', t: 5000 }]
  assert.equal(lastVerified(items).t, 2000)
  assert.equal(lastVerified(items, 1500).t, 1000)
  assert.equal(lastVerified(items, 500), null)
  assert.equal(lastVerified([]), null)
})
test('legenda: minuto:segundo do debate', () => {
  assert.equal(debateClock({ t: 65000 }, {}, true), '01:05')
  assert.equal(debateClock({ t: 3725000 }, {}, true), '1:02:05')
  assert.equal(debateClock({ t: 1_000_000 + 125000 }, { video: { comeco: 1_000_000 } }, false), '02:05')
})
