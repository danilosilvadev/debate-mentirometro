import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { handle, localCheck, resetToken } from './core.mjs'

const fx = (n) => JSON.parse(readFileSync(new URL(`./fixtures/${n}.json`, import.meta.url)))
const ENV = { LIVEPIX_CLIENT_ID: 'mock-client', LIVEPIX_CLIENT_SECRET: 'x', GROQ_API_KEY: 'g' }

function fakeFetch(msg, modOk = true) {
  const calls = []
  const f = async (url, init = {}) => {
    calls.push(String(url))
    const j = (b, s = 200) => ({ ok: s < 300, status: s, json: async () => b })
    if (String(url).includes('oauth2/token')) return j({ access_token: 'tok', expires_in: 3600 })
    if (String(url).includes('/v2/messages/')) {
      assert.equal(init.headers.Authorization, 'Bearer tok')
      return msg ? j(msg) : j({}, 404)
    }
    if (String(url).includes('groq')) return j({ choices: [{ message: { content: JSON.stringify({ ok: modOk, motivo: modOk ? 'ok' : 'ofensa' }) } }] })
    throw new Error('url inesperada ' + url)
  }
  f.calls = calls
  return f
}

test('webhook válido: busca a mensagem na API, modera e grava aprovado', async () => {
  resetToken()
  const rows = []
  const fetch = fakeFetch(fx('message_ok'))
  const out = await handle(fx('webhook_message'), ENV, { fetch, insert: async (r) => rows.push(r), debate: 'globo' })
  assert.equal(out.status, 200)
  assert.equal(rows[0].status, 'aprovado')
  assert.equal(rows[0].valor_centavos, 1000)
  assert.equal(rows[0].livepix_id, 'msg0000000001')
  assert.ok(fetch.calls.some((u) => u.endsWith('/v2/messages/msg0000000001')))
})

test('corpo do webhook não é confiável: texto vem da API, cliente errado é recusado', async () => {
  resetToken()
  const rows = []
  const forged = { ...fx('webhook_message'), clientId: 'outro' }
  const out = await handle(forged, ENV, { fetch: fakeFetch(fx('message_ok')), insert: async (r) => rows.push(r) })
  assert.equal(out.status, 403)
  assert.equal(rows.length, 0)
  const miss = await handle(fx('webhook_message'), ENV, { fetch: fakeFetch(null), insert: async (r) => rows.push(r) })
  assert.equal(miss.body.ignorado, 'mensagem não existe')
  assert.equal(rows.length, 0)
})

test('moderação: link, flagged e IA rejeitam; sem segredos responde 503', async () => {
  resetToken()
  const rows = []
  const link = structuredClone(fx('message_ok')); link.data.message = 'vejam www.golpe.xyz'
  await handle(fx('webhook_message'), ENV, { fetch: fakeFetch(link), insert: async (r) => rows.push(r) })
  const flag = structuredClone(fx('message_ok')); flag.data.flagged = true
  await handle(fx('webhook_message'), ENV, { fetch: fakeFetch(flag), insert: async (r) => rows.push(r) })
  await handle(fx('webhook_message'), ENV, { fetch: fakeFetch(fx('message_ok'), false), insert: async (r) => rows.push(r) })
  assert.deepEqual(rows.map((r) => r.status), ['rejeitado', 'rejeitado', 'rejeitado'])
  assert.equal(localCheck('a', 'ok'), null)
  const none = await handle(fx('webhook_message'), {}, { fetch: fakeFetch(null), insert: async () => {} })
  assert.equal(none.status, 503)
})

test('outros eventos são ignorados com 200', async () => {
  const sub = { ...fx('webhook_message'), resource: { id: 'abcdef12', type: 'subscription' } }
  const out = await handle(sub, ENV, { fetch: fakeFetch(null), insert: async () => { throw new Error('não grava') } })
  assert.equal(out.body.ignorado, true)
})
