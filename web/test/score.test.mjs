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
