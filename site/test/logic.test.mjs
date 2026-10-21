import assert from 'node:assert/strict'
import test from 'node:test'
import { errorIndex, mentiromentro } from '../js/score.mjs'
import { buildView, timelineOf } from '../js/snapshot.mjs'
import { placarUrl } from '../js/poll.mjs'
import { applyEvent } from '../js/events.mjs'

test('meio ponto e arredondamento iguais ao app', () => {
  const index = errorIndex({ verdadeiro: 1, impreciso: 1, falso: 1 })
  assert.equal(index.erro, 0.5)
  assert.equal(index.verdadeiroPct, 33)
  const reading = mentiromentro('A', 'B', { verdadeiro: 3, impreciso: 0, falso: 0 }, { verdadeiro: 2, impreciso: 0, falso: 2 })
  assert.equal(reading.angle, 45)
  assert.equal(reading.call, 'right')
  const waiting = mentiromentro('A', 'B', { verdadeiro: 2 }, { falso: 10 })
  assert.equal(waiting.angle, 0)
  assert.equal(waiting.call, 'waiting')
})

test('a linha do tempo agrupa de 5 em 5 minutos', () => {
  const view = buildView({
    atualizado: 300000,
    video: { t0: 0, comeco: 0 },
    candidatos: {
      1: { nome: 'Lula', verdadeiro: 0, impreciso: 0, falso: 0 },
      2: { nome: 'Flávio', verdadeiro: 0, impreciso: 0, falso: 1 },
    },
    fatos: [],
    propostas: [],
    ataques: [],
    linha: { 0: { p1: 1 }, 6: { a2: 2 } },
  })
  const columns = timelineOf(view.snapshot)
  assert.equal(columns.length, 2)
  assert.equal(columns[0].by['1'].proposals, 1)
  assert.equal(columns[1].by['2'].attacks, 2)
  assert.equal(view.reading.call, 'waiting')
})

test('o cache-bust cai em baldes de 3 segundos', () => {
  assert.equal(placarUrl('http://127.0.0.1:8787/', 6000), 'http://127.0.0.1:8787/placar.json?t=2')
  assert.equal(placarUrl('http://127.0.0.1:8787/', 8999), 'http://127.0.0.1:8787/placar.json?t=2')
})

test('evento de veredito atualiza o fato e um buraco pede resync', () => {
  const snapshot = {
    atualizado: 1,
    candidatos: { 2: { nome: 'B', falso: 0 } },
    fatos: [{ tema: 'gastos', atualizado: 10, declaracoes: [{ t: 10, quem: '2', afirmacao: 'x', veredito: 'em_revisao' }] }],
    propostas: [],
    ataques: [],
  }
  const step = applyEvent(snapshot, {
    v: 1, debate_id: 'd', seq: 1, t: 10, type: 'claim.updated', quem: '2',
    payload: { afirmacao: 'x', veredito: 'falso', motivo: 'dados' },
  }, 1)
  assert.equal(step.resync, false)
  assert.equal(step.snapshot.fatos[0].declaracoes[0].veredito, 'falso')
  const hole = applyEvent(step.snapshot, { v: 1, seq: 9, t: 11, type: 'debate.status', payload: {} }, step.seq)
  assert.equal(hole.resync, true)
})
