import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { normalize, isVisible, forced, bannerHtml, DEFAULTS } from '../js/ads.mjs'
test('ads: padrões e ads.json', () => {
  const d = normalize({})
  assert.equal(d.interval_min, 10); assert.equal(d.duration_s, 40); assert.equal(d.position, 'bottom-left')
  assert.equal(normalize({ position: 'top' }).position, 'bottom-left')
  assert.equal(normalize({ position: 'bottom-right' }).position, 'bottom-right')
  assert.equal(normalize({ interval_min: -1 }).interval_min, DEFAULTS.interval_min)
  const j = normalize(JSON.parse(readFileSync(new URL('../ads.json', import.meta.url))))
  assert.equal(j.slides.length, 2); assert.equal(j.headline, 'Apoie o Mentirômetro')
})
test('ads: agenda a cada 10 min por 40 s', () => {
  const c = normalize({ slides: [{ title: 'a' }] }), m = 60000
  assert.equal(isVisible(c, 0), false); assert.equal(isVisible(c, 5 * m), false)
  assert.equal(isVisible(c, 10 * m), true); assert.equal(isVisible(c, 10 * m + 39000), true)
  assert.equal(isVisible(c, 10 * m + 40000), false); assert.equal(isVisible(c, 20 * m + 1000), true)
  assert.equal(isVisible(normalize({ slides: [] }), 10 * m), false)
})
test('ads: adnow força e html seguro', () => {
  assert.equal(forced('?replay=x&adnow=1'), true); assert.equal(forced('?replay=x'), false)
  assert.equal(isVisible(normalize({}), 0, true), true)
  const h = bannerHtml(normalize({ headline: '<b>', slides: [{ title: 'a', url: 'https://x' }, { title: 'b' }] }))
  assert.match(h, /Publicidade/); assert.match(h, /rel="noopener sponsored"/); assert.match(h, /target="_blank"/); assert.ok(!h.includes('<b>'))
})
