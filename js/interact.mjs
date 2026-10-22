// Interação: portão de e-mail (sempre), votos e super chat (só ao vivo), e no replay a
// reprodução dos eventos gravados (votos, super chats, contadores) no tempo do vídeo.
// Fica num nó próprio (#ix), fora de #app, para não ser apagado a cada repintura.

const W = typeof window !== 'undefined' ? window : {}
const GATE_KEY = 'placar_gate_v1'
const CLIENT_KEY = 'placar_client_v1'
const GREEN = '#2FBF71'
const YELLOW = '#F5D33B'
const RED = '#E5484D'

export const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]+\.[a-z]{2,}$/i
export function validEmail(v) { return typeof v === 'string' && v.length <= 254 && EMAIL_RE.test(v.trim()) }

export function gateReady({ email, consent, clicked, requireSocial }) {
  return validEmail(email) && consent === true && (!requireSocial || clicked > 0)
}

// Limite local de cliques: no máximo `max` em `windowMs` (o servidor tem o seu).
export function tapLimiter(max = 6, windowMs = 1000) {
  const hits = []
  return (now = Date.now()) => {
    while (hits.length && now - hits[0] > windowMs) hits.shift()
    if (hits.length >= max) return false
    hits.push(now)
    return true
  }
}

// Replay: contadores e eventos novos entre dois segundos do vídeo.
export function eventsBetween(eventos, from, to) {
  const votos = (eventos?.votos || []).filter((v) => v.s > from && v.s <= to)
  const chats = (eventos?.superchats || []).filter((c) => c.s > from && c.s <= to)
  return { votos, chats }
}
export function totalsAt(eventos, sec) {
  const t = { 1: 0, 2: 0 }
  for (const v of eventos?.votos || []) if (v.s <= sec) t[v.side] = (t[v.side] || 0) + (v.n || 1)
  return t
}

export function brl(cents) { return (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) }

function esc(v) { return String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])) }

function clientId() {
  try {
    let id = localStorage.getItem(CLIENT_KEY)
    if (!id) { id = (crypto.randomUUID?.() || String(Math.random()).slice(2) + Date.now()).replace(/-/g, ''); localStorage.setItem(CLIENT_KEY, id) }
    return id
  } catch { return 'anon' + Math.floor(Math.random() * 1e12) }
}

function sb() {
  const c = W.PLACAR_SUPABASE || {}
  return c.url && c.key ? c : null
}
async function rpc(fn, body) {
  const c = sb()
  if (!c) throw new Error('sem supabase')
  const r = await fetch(`${c.url}/rest/v1/rpc/${fn}`, { method: 'POST', headers: { apikey: c.key, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const data = await r.json().catch(() => null)
  if (!r.ok) throw new Error(data?.message || `erro ${r.status}`)
  return data
}
async function select(path) {
  const c = sb()
  const r = await fetch(`${c.url}/rest/v1/${path}`, { headers: { apikey: c.key } })
  return r.ok ? r.json() : []
}

// ---------- UI ----------
function root() {
  let el = document.getElementById('ix')
  if (!el) { el = document.createElement('div'); el.id = 'ix'; document.body.appendChild(el) }
  return el
}

function float(btn, side) {
  const r = btn.getBoundingClientRect()
  const n = document.createElement('span')
  n.className = `ix-like s${side}`
  n.style.left = `${r.left + r.width / 2 + (Math.random() * 24 - 12)}px`
  n.style.top = `${r.top}px`
  n.style.setProperty('--dx', `${Math.random() * 60 - 30}px`)
  n.style.setProperty('--rot', `${Math.random() * 40 - 20}deg`)
  n.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 21s-7.5-4.6-9.6-9.2C.9 8.4 3 4.5 6.8 4.5c2.1 0 3.6 1.1 5.2 3 1.6-1.9 3.1-3 5.2-3 3.8 0 5.9 3.9 4.4 7.3C19.5 16.4 12 21 12 21z"/></svg>'
  root().appendChild(n)
  setTimeout(() => n.remove(), 1600)
}

function votesHtml(names, replay) {
  return `<div class="ix-votes${replay ? ' replay' : ''}" role="group" aria-label="Torcida">
    ${replay ? '<span class="ix-lbl">Torcida (gravada)</span>' : ''}
    <button type="button" class="ix-vote s1" data-side="1" ${replay ? 'disabled' : ''} aria-label="Apoiar ${esc(names[0])}"><i></i><b data-n="1">0</b></button>
    <button type="button" class="ix-vote s2" data-side="2" ${replay ? 'disabled' : ''} aria-label="Apoiar ${esc(names[1])}"><i></i><b data-n="2">0</b></button>
    ${replay ? '' : linkBtn('ix-donate', W.LIVEPIX_URL, 'Super chat')}${linkBtn('ix-apoie', W.APOIASE_URL, 'Apoie o projeto')}
  </div><div class="ix-chats" aria-live="polite"></div><div class="ix-toast" role="status"></div>`
}

function setTotals(t) {
  for (const side of ['1', '2']) {
    const b = document.querySelector(`.ix-vote b[data-n="${side}"]`)
    if (b) b.textContent = Number(t[side] || 0).toLocaleString('pt-BR')
  }
}

function toast(msg) {
  const el = document.querySelector('.ix-toast')
  if (!el) return
  el.textContent = msg
  el.classList.add('on')
  clearTimeout(toast._t)
  toast._t = setTimeout(() => el.classList.remove('on'), 2200)
}

const chatQueue = []
let chatBusy = false
export function showChat(c) {
  chatQueue.push(c)
  if (!chatBusy) nextChat()
}
function nextChat() {
  const c = chatQueue.shift()
  const box = document.querySelector('.ix-chats')
  if (!c || !box) { chatBusy = false; return }
  chatBusy = true
  const tier = c.valor_centavos >= 5000 ? 't3' : c.valor_centavos >= 2000 ? 't2' : 't1'
  const el = document.createElement('div')
  el.className = `ix-chat ${tier}`
  el.innerHTML = `<div class="ix-chat-h"><b>${esc(c.nome)}</b><span>${esc(brl(c.valor_centavos))}</span>${c.teste ? '<em>teste</em>' : ''}</div><p>${esc(c.mensagem)}</p>`
  box.appendChild(el)
  setTimeout(() => { el.classList.add('out'); setTimeout(() => { el.remove(); nextChat() }, 400) }, 7000)
}

// ---------- Portão de e-mail ----------
function gate() {
  try { if (localStorage.getItem(GATE_KEY)) return } catch { /* sem storage: pede de novo */ }
  const social = W.PLACAR_SOCIAL || {}
  const requireSocial = W.REQUIRE_SOCIAL_CLICK === true
  const links = [['instagram', 'Instagram'], ['x', 'X'], ['youtube', 'YouTube']].filter(([k]) => social[k])
  const wrap = document.createElement('div')
  wrap.className = 'ix-gate'
  wrap.innerHTML = `<div class="ix-modal" role="dialog" aria-modal="true" aria-labelledby="ixg-t">
    <h2 id="ixg-t">Acompanhe o Placar da Verdade</h2>
    <p class="muted">Receba o resumo das checagens depois de cada debate.</p>
    <form novalidate>
      <label>E-mail<input type="email" name="email" autocomplete="email" required placeholder="voce@exemplo.com"></label>
      <small class="ix-err" data-err="email"></small>
      <label class="ix-check"><input type="checkbox" name="consent" required>
        <span>Concordo em receber e-mails do Placar da Verdade e com o tratamento do meu e-mail para esse fim (LGPD, Lei 13.709/2018). Posso cancelar quando quiser.</span></label>
      <small class="ix-err" data-err="consent"></small>
      <div class="ix-social">${links.map(([k, label]) => `<a class="ix-soc ${k}" href="${esc(social[k])}" target="_blank" rel="noopener noreferrer" data-soc="${k}">Seguir no ${label}</a>`).join('')}</div>
      ${requireSocial ? '<small class="muted">Siga pelo menos uma rede para continuar.</small>' : ''}
      <button type="submit" class="ix-go">Entrar no placar</button>
    </form></div>`
  document.body.appendChild(wrap)
  document.documentElement.classList.add('ix-dim')
  let clicked = 0
  const socialClicked = {}
  wrap.querySelectorAll('[data-soc]').forEach((a) => a.addEventListener('click', () => { clicked++; socialClicked[a.dataset.soc] = true }))
  const form = wrap.querySelector('form')
  setTimeout(() => form.email.focus(), 50)
  form.addEventListener('submit', async (ev) => {
    ev.preventDefault()
    const email = form.email.value.trim()
    const consent = form.consent.checked
    wrap.querySelector('[data-err="email"]').textContent = validEmail(email) ? '' : 'Digite um e-mail válido.'
    wrap.querySelector('[data-err="consent"]').textContent = consent ? '' : 'Marque o consentimento para continuar.'
    if (!gateReady({ email, consent, clicked, requireSocial })) return
    const btn = form.querySelector('.ix-go')
    btn.disabled = true
    btn.textContent = 'Enviando…'
    try {
      if (sb()) await rpc('subscribe_email', { p_email: email, p_consent: true, p_consent_text: form.querySelector('.ix-check span').textContent, p_social: socialClicked, p_client: clientId() })
      try { localStorage.setItem(GATE_KEY, JSON.stringify({ at: Date.now() })) } catch { /* ok */ }
      wrap.classList.add('out')
      document.documentElement.classList.remove('ix-dim')
      setTimeout(() => wrap.remove(), 300)
    } catch (e) {
      btn.disabled = false
      btn.textContent = 'Entrar no placar'
      wrap.querySelector('[data-err="email"]').textContent = /email/.test(e.message) ? 'Digite um e-mail válido.' : 'Não deu para salvar agora. Tente de novo.'
    }
  })
}

// ---------- Super chat e apoio (só links de terceiros) ----------
// Nenhum dado de pagamento passa pelo nosso código: o super chat é pago na página da LivePix,
// que avisa nossa Edge Function (webhook); o apoio mensal é no Apoia.se.
export function externalUrl(u) {
  return typeof u === 'string' && /^https:\/\/(?:[a-z0-9-]+\.)*(?:livepix\.gg|apoia\.se)\/[A-Za-z0-9_./-]+$/i.test(u) && !/SEU_/.test(u) ? u : ''
}

function linkBtn(cls, url, label) {
  const ok = externalUrl(url)
  return ok
    ? `<a class="${cls}" href="${esc(ok)}" target="_blank" rel="noopener noreferrer">${label}</a>`
    : `<button type="button" class="${cls}" data-act="nolink" aria-disabled="true">${label}</button>`
}

// ---------- Ao vivo ----------
async function live(names) {
  root().innerHTML = votesHtml(names, false)
  const pending = { 1: 0, 2: 0 }
  const totals = { 1: 0, 2: 0 }
  const allow = tapLimiter(6, 1000)
  if (sb()) {
    for (const row of await select('vote_totals?select=side,n').catch(() => [])) totals[row.side] = row.n
    setTotals(totals)
  }
  root().addEventListener('click', (ev) => {
    const btn = ev.target.closest('.ix-vote')
    if (btn) {
      if (!allow()) { toast('Calma! Muitos toques por segundo.'); return }
      const side = btn.dataset.side
      pending[side]++
      totals[side]++
      setTotals(totals)
      float(btn, side)
      btn.classList.remove('pop'); void btn.offsetWidth; btn.classList.add('pop')
      return
    }
    if (ev.target.closest('[data-act="nolink"]')) toast('Link ainda não configurado.')
  })
  setInterval(async () => {
    for (const side of ['1', '2']) {
      const n = Math.min(20, pending[side])
      if (!n || !sb()) continue
      pending[side] -= n
      try {
        const out = await rpc('cast_vote', { p_side: side, p_n: n, p_client: clientId(), p_debate: W.PLACAR_DEBATE_KEY || 'ao-vivo' })
        if (out?.ok) Object.assign(totals, out.totais)
        else toast('Calma! Seus votos estão rápidos demais.')
        setTotals(totals)
      } catch { /* rede: tenta no próximo ciclo */ pending[side] += n }
    }
  }, 900)
  // Tempo real: supabase-js (canal postgres_changes); se falhar, consulta a cada 4 s.
  const seen = new Set()
  const onChat = (c) => { if (c?.status === 'aprovado' && !seen.has(c.id)) { seen.add(c.id); showChat(c) } }
  let realtime = false
  try {
    const { createClient } = await import('https://esm.sh/@supabase/supabase-js@2.45.4')
    const client = createClient(sb().url, sb().key)
    client.channel('placar')
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'vote_totals' }, (p) => {
        const r = p.new; if (r) { totals[r.side] = Math.max(totals[r.side], r.n); setTotals(totals) }
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'superchats' }, (p) => onChat(p.new))
      .subscribe((status) => { realtime = status === 'SUBSCRIBED'; document.documentElement.dataset.realtime = status })
  } catch { realtime = false }
  const since = new Date().toISOString()
  setInterval(async () => {
    if (realtime || !sb()) return
    for (const row of await select('vote_totals?select=side,n').catch(() => [])) totals[row.side] = Math.max(totals[row.side], row.n)
    setTotals(totals)
    for (const c of await select(`superchats?select=id,nome,mensagem,valor_centavos,teste,status&moderado_at=gt.${since}&order=moderado_at`).catch(() => [])) onChat(c)
  }, 4000)
}

// ---------- Replay: reproduz o que foi gravado ----------
function replay(names, getData, now) {
  root().innerHTML = votesHtml(names, true)
  let last = null
  setInterval(() => {
    const data = getData()
    const ev = data?.eventos
    if (!ev) return
    const sec = now()
    if (last === null || sec < last || sec - last > 5) { // início ou seek: só ajusta contadores
      last = sec
      setTotals(totalsAt(ev, sec))
      return
    }
    const { votos, chats } = eventsBetween(ev, last, sec)
    last = sec
    setTotals(totalsAt(ev, sec))
    let shown = 0
    for (const v of votos) {
      const btn = document.querySelector(`.ix-vote.s${v.side}`)
      for (let i = 0; i < Math.min(v.n || 1, 3) && shown < 12; i++, shown++) if (btn) float(btn, v.side)
    }
    for (const c of chats) showChat(c)
    const lbl = document.querySelector('.ix-lbl')
    if (lbl && ev.simulado) lbl.textContent = 'Torcida (eventos simulados)'
  }, 250)
}

function names() {
  return [document.querySelector('.cand .nm')?.textContent || 'Candidato A', document.querySelector('.cand.r .nm')?.textContent || 'Candidato B']
}

export function boot() {
  gate()
  const isReplay = /[?&]replay=/.test(location.search)
  const start = () => {
    if (isReplay) {
      if (!W.__replay) { setTimeout(start, 300); return }
      replay(names(), () => W.__replay.data, () => W.__replay.now())
    } else {
      live(names())
    }
  }
  setTimeout(start, 400)
}

if (typeof document !== 'undefined' && document.getElementById?.('app')) boot()
