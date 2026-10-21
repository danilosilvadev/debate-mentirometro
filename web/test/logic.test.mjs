import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import {
  changedStamp,
  createFeed,
  errorIndex,
  feedUrl,
  mentiromentro,
  renderBoard,
  resolveFeed,
  timelineOf,
} from '../js/placar.mjs'

test('meio ponto e 45 graus iguais ao app', () => {
  const left = errorIndex({ verdadeiro: 3 })
  const right = errorIndex({ verdadeiro: 2, falso: 2 })
  assert.equal(left.erro, 0)
  assert.equal(right.erro, 0.5)
  assert.equal(right.erroPct, 50)
  const reading = mentiromentro('Lula', 'Flávio Bolsonaro', { verdadeiro: 3 }, { verdadeiro: 2, falso: 2 })
  assert.equal(reading.angle, 45)
  assert.equal(reading.call, 'right')
  assert.equal(reading.headline, 'Flávio Bolsonaro está errando mais')
  const tie = mentiromentro('A', 'B', { verdadeiro: 3 }, { verdadeiro: 3 })
  assert.equal(tie.headline, 'Empate técnico')
  const wait = mentiromentro('A', 'B', { verdadeiro: 1 }, { falso: 1 })
  assert.equal(wait.call, 'waiting')
  assert.equal(wait.angle, 0)
})

test('a linha do tempo agrupa de 5 em 5 minutos', () => {
  const origin = 1_000_000
  const board = timelineOf({
    video: { comeco: origin },
    candidatos: { 1: { nome: 'Ana' }, 2: { nome: 'Bia' } },
    linha: { 0: { a1: 1 }, 4: { p2: 1 }, 5: { a2: 2 } },
  })
  assert.equal(board.rows[0].columns.length, 2)
  assert.equal(board.rows[0].columns[0].attacks, 1)
  assert.equal(board.rows[1].columns[0].proposals, 1)
  assert.equal(board.rows[1].columns[1].attacks, 2)
  assert.equal(board.rows[0].columns[1].startMs, origin + 300000)
})

test('o endereço do placar aceita base, arquivo e ?d=', () => {
  assert.equal(feedUrl({ base: 'http://127.0.0.1:8787/', now: 6000 }), 'http://127.0.0.1:8787/placar.json?t=2')
  assert.equal(feedUrl({ base: 'http://127.0.0.1:8787/placar.json', now: 8999 }), 'http://127.0.0.1:8787/placar.json?t=2')
  assert.equal(
    feedUrl({ base: 'https://dados.example/', archive: '2026-10-18', now: 0 }),
    'https://dados.example/placar-2026-10-18.json?t=0',
  )
  assert.equal(feedUrl({ base: 'https://dados.example/', archive: '../x', now: 0 }), 'https://dados.example/placar.json?t=0')
  assert.equal(feedUrl({ demo: true, now: 3000 }), 'demo/placar.json?t=1')
  assert.equal(feedUrl({ demo: true, archive: '2026-10-18', now: 0 }), 'demo/placar-2026-10-18.json?t=0')
  assert.equal(resolveFeed('?demo=1', 'https://dados.example/', 0).mode, 'demo')
  assert.equal(resolveFeed('', '', 0).mode, 'demo')
  const live = resolveFeed('?src=http://127.0.0.1:8787/placar.json', '', 0)
  assert.equal(live.mode, 'live')
  assert.equal(live.url, 'http://127.0.0.1:8787/placar.json?t=0')
  const past = resolveFeed('?d=2026-10-18', 'https://dados.example', 0)
  assert.equal(past.url, 'https://dados.example/placar-2026-10-18.json?t=0')
})

test('só redesenha quando atualizado muda', async () => {
  const bodies = [
    { atualizado: 10, candidatos: {} },
    { atualizado: 10, candidatos: {} },
    { atualizado: 11, candidatos: {} },
  ]
  let fetches = 0
  let calls = 0
  const feed = createFeed({
    urlFor: () => 'placar.json',
    fetchImpl: async () => ({ ok: true, json: async () => bodies[fetches++] }),
    onData: () => { calls += 1 },
  })
  await feed.tick()
  await feed.tick()
  await feed.tick()
  assert.equal(calls, 2)
  assert.equal(changedStamp(10, { atualizado: 10 }), false)
})

test('o polling não busca com a aba escondida', async () => {
  let hidden = true
  let fetches = 0
  const feed = createFeed({
    urlFor: () => 'placar.json',
    isHidden: () => hidden,
    fetchImpl: async () => {
      fetches += 1
      return { ok: true, json: async () => ({ atualizado: fetches }) }
    },
    onData() {},
  })
  await feed.tick()
  assert.equal(fetches, 0)
  hidden = false
  await feed.tick()
  assert.equal(fetches, 1)
  feed.pause()
  await feed.tick()
  assert.equal(fetches, 2)
})

test('a simulação desenha o placar e esconde script', async () => {
  const snapshot = JSON.parse(await readFile(new URL('../demo/placar.json', import.meta.url), 'utf8'))
  const html = renderBoard({
    mode: 'demo',
    snapshot,
    filter: {},
    view: 'placar',
    open: new Set(),
    fresh: new Set(),
    now: snapshot.atualizado,
    pageUrl: 'http://127.0.0.1/',
    sourceLabel: 'demo/placar.json',
  })
  assert.match(html, /Mentirômetro/)
  assert.match(html, /Flávio Bolsonaro está errando mais/)
  assert.match(html, /Fatos checados/)
  assert.match(html, /Como funciona/)
  assert.match(html, /É uma checagem automática e pode errar/)
  assert.doesNotMatch(html, /<script/i)
  assert.match(html, /exemplo\.com/)
  const proposals = renderBoard({ mode: 'demo', snapshot, view: 'propostas', now: snapshot.atualizado, pageUrl: 'http://x/' })
  assert.match(proposals, /Ampliar vagas em creche/)
  assert.match(proposals, /Citada 2 vezes/)
})
