import assert from 'node:assert/strict'
import test from 'node:test'
import { captionClaim, clock, itemSecond, lineAt, mmss, signatureAt, snapshotAt } from '../js/replay.mjs'

const data = {
  video: { id: 'RugVB17uRVM', t0: 1000 },
  replay: { video: 'RugVB17uRVM', inicio: 340, fim: 800 },
  candidatos: { 1: { nome: 'Lula', tempo: { outro: 100 } }, 2: { nome: 'Flávio', tempo: {} } },
  fatos: [{ tema: 'economia', declaracoes: [
    { t: 1000, quem: '1', veredito: 'verdadeiro', vs: 400, afirmacao: 'A' },
    { t: 1000, quem: '2', veredito: 'falso', vs: 766, afirmacao: 'PT 20/24' },
    { t: 1000, quem: '1', veredito: 'em_revisao', vs: 500, afirmacao: 'R' },
  ] }],
  propostas: [{ t: 1000, quem: '2', titulo: 'P', vs: 380 }],
  ataques: [{ t: 61000, quem: '1', resumo: 'X' }],
  linhas: [{ s: 760, e: 763, quem: 'other', text: 'Candidato Flávio, dois minutos.' }, { s: 763.7, e: 770, quem: '2', text: 'O PT já governa' }],
}

test('mostra só o que já foi dito e recalcula placar', () => {
  const early = snapshotAt(data, 390)
  assert.equal(early.fatos.length, 0)
  assert.equal(early.candidatos[2].propostas, 1)
  assert.equal(early.candidatos[1].verdadeiro, 0)
  const mid = snapshotAt(data, 600)
  assert.equal(mid.candidatos[1].verdadeiro, 1)
  assert.equal(mid.candidatos[2].falso, 0)
  assert.equal(mid.fatos[0].declaracoes.length, 2)
  const late = snapshotAt(data, 770)
  assert.equal(late.candidatos[2].falso, 1)
  assert.equal(late.linhas, undefined)
  // voltar no tempo esconde de novo
  assert.equal(snapshotAt(data, 765.9).candidatos[2].falso, 0)
})

test('sem vs usa t relativo a t0 + inicio', () => {
  assert.equal(itemSecond(data.ataques[0], data), 400)
})

test('legenda segue a fala e assinatura muda', () => {
  assert.equal(lineAt(data, 761).quem, 'other')
  assert.equal(lineAt(data, 765).text, 'O PT já governa')
  assert.equal(lineAt(data, 790), null)
  assert.notEqual(signatureAt(data, 765), signatureAt(data, 767))
})

test('relógio simulado e seek', () => {
  let now = 0
  const c = clock({ now: () => now, start: 340, rate: 2 })
  now = 1000
  assert.equal(c.get(), 342)
  c.seek(700)
  now = 1500
  assert.equal(c.get(), 701)
  assert.equal(mmss(766), '12:46')
})

test('itens no replay usam o tempo do vídeo', async () => {
  const { hhmm } = await import('../js/placar.mjs')
  const snap = snapshotAt(data, 800)
  assert.equal(snap.fatos[0].declaracoes.find((c) => c.afirmacao === 'PT 20/24').t, 766000)
  assert.equal(hhmm(766000), '12:46')
  assert.equal(hhmm(Date.UTC(2026, 9, 18, 23, 30)), '20:30')
})

test('seek para frente e para trás em qualquer ordem dá o mesmo placar', () => {
  const at = (s) => JSON.stringify(snapshotAt(data, s).candidatos)
  const seq = [340, 900, 400, 770, 765, 1200, 341]
  const fresh = Object.fromEntries(seq.map((s) => [s, at(s)]))
  for (const s of [...seq].reverse()) assert.equal(at(s), fresh[s])
})

test('replay não desenha iframe dentro do placar (o player fica fora e não é recriado)', async () => {
  const { renderBoard } = await import('../js/placar.mjs')
  const html = renderBoard({ snapshot: snapshotAt(data, 770), replay: data, replaySec: 770, replayLine: lineAt(data, 765), filter: {}, fresh: new Set(), mode: 'live', now: 0 })
  assert.ok(!html.includes('<iframe'))
  assert.ok(!html.includes('id="ytreplay"'))
  assert.ok(html.includes('REPLAY') && html.includes('PT 20/24'))
  assert.ok(!html.includes('O PT já governa'), 'legenda não mostra transcrição crua')
})

test('legenda: checando até vv, some se chegou depois de 15 s', () => {
  const d = {
    legenda_max_s: 15, candidatos: { 1: { nome: 'Lula' } },
    fatos: [{ tema: 'x', declaracoes: [
      { id: 'c1', t: 0, quem: '1', veredito: 'falso', vs: 100, va: 108, vv: 115, lat: 8, afirmacao: 'Rápida' },
      { id: 'c2', t: 0, quem: '1', veredito: 'verdadeiro', vs: 200, va: 230, vv: 240, lat: 30, afirmacao: 'Lenta' },
    ] }],
  }
  assert.equal(captionClaim(d, 107), null)
  assert.equal(captionClaim(d, 108).id, 'c1')
  assert.equal(snapshotAt(d, 110).fatos[0].declaracoes[0].veredito, 'checando')
  assert.equal(snapshotAt(d, 110).candidatos[1].falso, 0)
  assert.equal(snapshotAt(d, 116).candidatos[1].falso, 1)
  assert.equal(captionClaim(d, 235), null) // lenta: só na lista
  assert.equal(snapshotAt(d, 235).fatos[0].declaracoes.length, 2)
})

test('cartão vira uma vez de checando para veredito', async () => {
  const { flipState } = await import('../js/placar.mjs')
  const memo = new Map()
  assert.equal(flipState('k', true, 0, memo).face, 'front')
  assert.equal(flipState('k', false, 1000, memo).face, 'flip')
  assert.equal(flipState('k', false, 1500, memo).delay, 500)
  assert.equal(flipState('k', false, 3000, memo).face, 'back')
  assert.equal(flipState('z', false, 0, memo).face, 'back') // já chegou pronto: sem animação
})
