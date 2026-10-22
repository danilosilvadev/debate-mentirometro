// Banner de patrocínio: aparece a cada interval_min por duration_s. ?adnow=1 força exibição.
// Conteúdo e horários em web/ads.json.
export const DEFAULTS = { enabled: true, interval_min: 10, duration_s: 40, position: 'bottom-left', headline: 'Apoie o Mentirômetro', slides: [], slide_s: 6 }

export function normalize(cfg) {
  const c = { ...DEFAULTS, ...(cfg && typeof cfg === 'object' ? cfg : {}) }
  c.interval_min = Number(c.interval_min) > 0 ? Number(c.interval_min) : DEFAULTS.interval_min
  c.duration_s = Number(c.duration_s) > 0 ? Number(c.duration_s) : DEFAULTS.duration_s
  c.slide_s = Number(c.slide_s) > 0 ? Number(c.slide_s) : DEFAULTS.slide_s
  if (c.position !== 'bottom-right') c.position = 'bottom-left'
  c.slides = (Array.isArray(c.slides) ? c.slides : []).filter(s => s && s.title).slice(0, 2)
    .map(s => ({ title: String(s.title), url: s.url ? String(s.url) : '#', ...(s.image ? { image: String(s.image) } : {}) }))
  c.headline = String(c.headline || DEFAULTS.headline)
  return c
}

// Visível se, dentro de cada ciclo de interval_min, estamos nos primeiros duration_s (após a 1ª volta).
export function isVisible(cfg, elapsedMs, force = false) {
  if (force) return true
  if (!cfg.enabled || !cfg.slides.length) return false
  const period = cfg.interval_min * 60000
  if (elapsedMs < period) return false
  return (elapsedMs % period) < cfg.duration_s * 1000
}

export function forced(search) { return new URLSearchParams(search || '').get('adnow') === '1' }

const esc = s => String(s).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]))

export function bannerHtml(cfg) {
  const slides = cfg.slides.map((s, i) => `<a class="ad-slide${i ? '' : ' on'}" href="${esc(s.url)}" target="_blank" rel="noopener sponsored">` +
    (s.image ? `<img src="${esc(s.image)}" alt="">` : '') + `<span>${esc(s.title)}</span></a>`).join('')
  const dots = cfg.slides.length > 1 ? `<span class="ad-dots">${cfg.slides.map((_, i) => `<i class="${i ? '' : 'on'}"></i>`).join('')}</span>` : ''
  return `<div class="ad-top"><span class="ad-lbl">Publicidade</span>${dots}<button class="ad-x" type="button" aria-label="Fechar anúncio">✕</button></div>` +
    `<div class="ad-h">${esc(cfg.headline)}</div><div class="ad-slides">${slides}</div>`
}

export async function start({ url = 'ads.json', doc = globalThis.document, now = () => Date.now() } = {}) {
  if (!doc) return
  let cfg
  try { const r = await fetch(url, { cache: 'no-cache' }); cfg = normalize(r.ok ? await r.json() : {}) } catch { cfg = normalize({}) }
  const force = forced(globalThis.location?.search)
  if (!cfg.slides.length) return
  const t0 = now()
  const el = doc.createElement('aside')
  el.className = `adb ${cfg.position}`
  el.setAttribute('aria-label', 'Publicidade')
  el.innerHTML = bannerHtml(cfg)
  doc.body.appendChild(el)
  let closedCycle = -1, idx = 0
  el.querySelector('.ad-x').addEventListener('click', () => {
    closedCycle = Math.floor((now() - t0) / (cfg.interval_min * 60000)); el.classList.remove('show'); el.dataset.closed = '1'
  })
  const tick = () => {
    const el2 = now() - t0, cyc = Math.floor(el2 / (cfg.interval_min * 60000))
    const vis = (force && closedCycle < 0) || (isVisible(cfg, el2) && cyc !== closedCycle)
    el.classList.toggle('show', vis)
  }
  const rot = () => {
    const ss = el.querySelectorAll('.ad-slide'), ds = el.querySelectorAll('.ad-dots i')
    if (ss.length < 2) return
    idx = (idx + 1) % ss.length
    ss.forEach((s, i) => s.classList.toggle('on', i === idx)); ds.forEach((d, i) => d.classList.toggle('on', i === idx))
  }
  tick(); setInterval(tick, 1000); setInterval(rot, cfg.slide_s * 1000)
}

if (globalThis.document && !globalThis.__ADS_NO_AUTOSTART) start()
