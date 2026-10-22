import test from 'node:test'
import assert from 'node:assert/strict'
import { sideScore } from '../js/placar.mjs'
const f = { titulo: 'IBGE', url: 'https://sidra.ibge.gov.br/x' }
test('placar Verdades vs Mentiras só conta vereditos com fonte', () => {
  const claims = [
    { quem: '1', veredito: 'verdadeiro', fonte: f },
    { quem: '1', veredito: 'verdadeiro' },
    { quem: '1', veredito: 'falso', fonte: f },
    { quem: '1', veredito: 'falso', fonte: { url: 'javascript:x' } },
    { quem: '1', veredito: 'impreciso', fonte: f },
    { quem: '1', veredito: 'sem_dados' },
    { quem: '2', veredito: 'falso', fonte: f },
    { quem: '2', veredito: 'checando', fonte: f },
  ]
  assert.deepEqual(sideScore(claims, '1'), { verdades: 1, mentiras: 1, imprecisos: 1 })
  assert.deepEqual(sideScore(claims, '2'), { verdades: 0, mentiras: 1, imprecisos: 0 })
  assert.deepEqual(sideScore([], '1'), { verdades: 0, mentiras: 0, imprecisos: 0 })
})

import { lieBoard } from '../js/placar.mjs'
test('topo: mentiras com fonte, cabo de guerra e manchete', () => {
  const f = { titulo: 'IBGE', url: 'https://ibge.gov.br' }
  const c = (quem, veredito, fonte) => ({ quem, veredito, ...(fonte ? { fonte } : {}) })
  const L = { id: '1', nome: 'Lula' }, R = { id: '2', nome: 'Flávio Bolsonaro' }
  let b = lieBoard([], L, R); assert.equal(b.call, 'none'); assert.equal(b.headline, 'Nenhuma mentira ainda'); assert.equal(b.leftPct, 50)
  b = lieBoard([c('1', 'falso', f), c('2', 'falso', f), c('2', 'falso', f), c('2', 'falso'), c('1', 'verdadeiro', f)], L, R)
  assert.equal(b.left, 1); assert.equal(b.right, 2); assert.equal(b.call, 'right'); assert.equal(b.leftPct, 33)
  assert.equal(b.headline, 'Flávio Bolsonaro lidera o Troféu Pinóquio')
  assert.equal(lieBoard([c('1', 'falso', f), c('2', 'falso', f)], L, R).call, 'tie')
})
