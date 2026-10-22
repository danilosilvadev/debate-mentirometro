import test from 'node:test'
import assert from 'node:assert/strict'
import { shownVerdict, sourcesOf } from '../js/placar.mjs'
test('veredito sem fonte vira sem_dados', () => {
  assert.equal(shownVerdict({ veredito: 'falso' }), 'sem_dados')
  assert.equal(shownVerdict({ veredito: 'falso', fonte: { url: 'javascript:x' } }), 'sem_dados')
  assert.equal(shownVerdict({ veredito: 'falso', fonte: { titulo: 'IBGE', url: 'https://sidra.ibge.gov.br/x' } }), 'falso')
  assert.equal(shownVerdict({ veredito: 'checando' }), 'checando')
})
test('fontes oficiais primeiro', () => {
  const s = sourcesOf({ fonte: { titulo: 'G1', url: 'https://g1.globo.com/a' }, fontes: [{ titulo: 'BCB', url: 'https://www.bcb.gov.br/b' }] })
  assert.equal(s[0].titulo, 'BCB'); assert.equal(s[0].oficial, true); assert.equal(s.length, 2)
})
