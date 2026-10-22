import assert from 'node:assert/strict'
import test from 'node:test'
import { brl, eventsBetween, gateReady, tapLimiter, totalsAt, validEmail } from '../js/interact.mjs'

test('e-mail e consentimento obrigatórios; rede só se configurado', () => {
  assert.ok(validEmail('a@b.com.br') && !validEmail('a@b') && !validEmail('x y@b.com'))
  assert.ok(!gateReady({ email: 'a@b.com', consent: false, clicked: 0, requireSocial: false }))
  assert.ok(gateReady({ email: 'a@b.com', consent: true, clicked: 0, requireSocial: false }))
  assert.ok(!gateReady({ email: 'a@b.com', consent: true, clicked: 0, requireSocial: true }))
})

test('limite local de toques', () => {
  const allow = tapLimiter(3, 1000)
  assert.deepEqual([allow(0), allow(10), allow(20), allow(30), allow(1100)], [true, true, true, false, true])
})

test('replay de eventos: contadores e eventos entre segundos', () => {
  const ev = { votos: [{ s: 10, side: '1', n: 2 }, { s: 20, side: '2', n: 1 }], superchats: [{ s: 15, nome: 'A', mensagem: 'oi', valor_centavos: 1000 }] }
  assert.deepEqual(totalsAt(ev, 15), { 1: 2, 2: 0 })
  assert.deepEqual(totalsAt(ev, 25), { 1: 2, 2: 1 })
  const b = eventsBetween(ev, 12, 20)
  assert.equal(b.votos.length, 1)
  assert.equal(b.chats.length, 1)
  assert.match(brl(1000), /R\$\s?10,00/)
})
