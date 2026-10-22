import { captionClaim, clock as replayClock, mmss, signatureAt, snapshotAt, withinCaption } from './replay.mjs'
/** Placar da Verdade: conta, polling e a página. Sem build. */

export const MINIMO = 3

const VERDICT_LABEL = {
  verdadeiro: 'Verdadeiro',
  impreciso: 'Impreciso',
  falso: 'Falso',
  sem_dados: 'Sem dados',
  em_revisao: 'Em revisão',
  checando: 'Checando…',
}

const TONE = [
  ['proposta', 'propondo', 'p'],
  ['ataque', 'atacando', 'a'],
  ['defesa', 'se defendendo', 'd'],
  ['balanco', 'falando do passado', 'b'],
]

export function errorIndex({ verdadeiro = 0, impreciso = 0, falso = 0 } = {}) {
  const total = verdadeiro + impreciso + falso
  if (!total) {
    return { total: 0, verdadeiroPct: 0, imprecisoPct: 0, falsoPct: 0, erro: 0, erroPct: 0 }
  }
  const pct = (count) => Math.round((count / total) * 100)
  const erro = (falso + impreciso / 2) / total
  return {
    total,
    verdadeiroPct: pct(verdadeiro),
    imprecisoPct: pct(impreciso),
    falsoPct: pct(falso),
    erro,
    erroPct: Math.round(erro * 100),
  }
}

export function mentiromentro(leftName, rightName, left, right) {
  const a = errorIndex(left)
  const b = errorIndex(right)
  const ready = a.total >= MINIMO && b.total >= MINIMO
  const angle = ready ? (b.erro - a.erro) * 90 : 0
  const diff = Math.abs(a.erro - b.erro)
  let call = 'right'
  let headline
  let detail
  if (!ready) {
    call = 'waiting'
    headline = 'Esperando mais fatos'
    detail = `o ponteiro só se mexe com pelo menos ${MINIMO} fatos checáveis de cada lado`
  } else if (diff < 0.1) {
    call = 'tie'
    headline = 'Empate técnico'
    detail = 'os dois erram parecido até agora'
  } else if (a.erro > b.erro) {
    call = 'left'
    headline = `${leftName} está errando mais`
    detail = `${a.erroPct}% contra ${b.erroPct}% de índice de erro`
  } else {
    headline = `${rightName} está errando mais`
    detail = `${b.erroPct}% contra ${a.erroPct}% de índice de erro`
  }
  const word = a.total === 1 ? 'fato checável' : 'fatos checáveis'
  const basis = `com base em ${a.total} ${word} de ${leftName} e ${b.total} de ${rightName} (sem dados fica de fora)`
  return { left: a, right: b, ready, angle, call, headline, detail, basis }
}

export function speakingShares(tempo = {}) {
  const seconds = TONE.map(([key]) => Number(tempo[key]) || 0)
  const sum = seconds.reduce((total, value) => total + value, 0)
  const denom = sum === 0 ? 1 : sum
  return TONE.map(([key, label, cls], index) => ({
    key,
    label,
    cls,
    seconds: seconds[index],
    percent: Math.round((seconds[index] / denom) * 100),
  }))
}

export function candidatesOf(snapshot) {
  const raw = snapshot?.candidatos || {}
  return Object.entries(raw).map(([id, body]) => ({ id, ...body }))
}

export function claimsOf(snapshot) {
  const claims = []
  for (const group of snapshot?.fatos || []) {
    for (const item of group.declaracoes || []) {
      claims.push({ ...item, tema: group.tema || '' })
    }
  }
  return claims
}

export function claimKey(claim) {
  return `${claim.t}|${claim.quem}|${claim.afirmacao}`
}

export function originMs(snapshot) {
  const video = snapshot?.video
  return video?.comeco ?? video?.t0 ?? snapshot?.atualizado ?? 0
}

export function timelineOf(snapshot) {
  const linha = snapshot?.linha || {}
  const minutes = Object.keys(linha).map(Number).filter((n) => !Number.isNaN(n))
  const candidates = candidatesOf(snapshot)
  if (!minutes.length || !candidates.length) return { rows: [], labelStep: 1, maxStack: 1 }
  const first = Math.min(...minutes)
  const last = Math.max(...minutes)
  const ini = Math.floor(first / 5)
  const fim = Math.floor(last / 5)
  const origin = originMs(snapshot)
  const blocks = []
  for (let block = ini; block <= fim; block += 1) blocks.push(block)
  let maxStack = 1
  const rows = candidates.map((candidate) => {
    const columns = blocks.map((block) => {
      let attacks = 0
      let proposals = 0
      for (let offset = 0; offset < 5; offset += 1) {
        const mark = linha[String(block * 5 + offset)] || {}
        attacks += mark[`a${candidate.id}`] || 0
        proposals += mark[`p${candidate.id}`] || 0
      }
      maxStack = Math.max(maxStack, attacks + proposals)
      return {
        block,
        attacks,
        proposals,
        startMs: origin + block * 300000,
        endMs: origin + (block + 1) * 300000,
      }
    })
    return { candidateId: candidate.id, name: candidate.nome, columns }
  })
  const labelStep = Math.max(1, Math.ceil(blocks.length / 6))
  return { rows, labelStep, maxStack }
}

export function effectiveOrder(snapshot, override) {
  if (override) return override
  if (snapshot?.encerrado || snapshot?.revisao) return 'debate'
  return 'recentes'
}

export function filterClaims(claims, filter = {}, ignore) {
  return claims.filter((claim) => {
    if (ignore !== 'quem' && filter.quem && claim.quem !== filter.quem) return false
    if (filter.onlyCorrected) return Boolean(claim.corrigido)
    if (ignore !== 'vered' && filter.verdict && claim.veredito !== filter.verdict) return false
    if (filter.windowStartMs != null && filter.windowEndMs != null) {
      if (claim.t < filter.windowStartMs || claim.t >= filter.windowEndMs) return false
    }
    return true
  })
}

export function sortClaims(claims, order) {
  return claims.slice().sort((a, b) => (order === 'recentes' ? b.t - a.t : a.t - b.t))
}

export function hhmm(epochMs) {
  // Replay: o `t` dos itens é o segundo do vídeo × 1000 (bem menor que um epoch)
  if (epochMs < 1e10) return mmss(epochMs / 1000)
  const time = new Date(epochMs - 3 * 60 * 60 * 1000)
  const hour = String(time.getUTCHours()).padStart(2, '0')
  const minute = String(time.getUTCMinutes()).padStart(2, '0')
  return `${hour}:${minute}`
}

export function dataCurta(epochMs) {
  const time = new Date(epochMs - 3 * 60 * 60 * 1000)
  return `${time.getUTCDate()}/${time.getUTCMonth() + 1}`
}

export function formatPt(value) {
  const negative = value < 0
  const digits = String(Math.abs(value))
  let out = ''
  for (let i = 0; i < digits.length; i += 1) {
    if (i > 0 && (digits.length - i) % 3 === 0) out += '.'
    out += digits[i]
  }
  return negative ? `-${out}` : out
}

export function faltaPara(quandoMs, agoraMs) {
  let seconds = Math.floor((quandoMs - agoraMs) / 1000)
  if (seconds <= 0) return 'começando agora'
  const days = Math.floor(seconds / 86400)
  seconds %= 86400
  const hours = Math.floor(seconds / 3600)
  seconds %= 3600
  const minutes = Math.floor(seconds / 60)
  const secs = seconds % 60
  const dois = (n) => String(n).padStart(2, '0')
  const dias = days === 0 ? '' : `${days} ${days === 1 ? 'dia ' : 'dias '}`
  return `${dias}${dois(hours)}h ${dois(minutes)}min ${dois(secs)}s`
}

export function rotuloDuracao(ms) {
  const minutes = Math.floor(ms / 60000)
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const rest = String(minutes % 60).padStart(2, '0')
    return `rolando há ${hours}h${rest}`
  }
  return `rolando há ${minutes} min`
}

export function positionMs(snapshot, now, mode) {
  const video = snapshot?.video || {}
  const origin = originMs(snapshot)
  if (mode === 'demo' || snapshot?.simulado) {
    return Math.max(0, (snapshot?.atualizado || origin) - origin)
  }
  if (video.ao_vivo) return Math.max(0, now - origin)
  return (video.inicio || 0) * 1000 + Math.max(0, now - (video.t0 || now))
}

export function statusCopy(snapshot, now, mode) {
  const demo = mode === 'demo' || snapshot?.simulado
  if (demo) {
    if (snapshot?.encerrado) return { vivo: false, texto: 'Simulação encerrada · placar final' }
    const pausa = snapshot?.pausado ? ' · pausada' : ''
    return { vivo: true, texto: `Simulação${pausa} · fatos ilustrativos` }
  }
  if (snapshot?.encerrado) return { vivo: false, texto: 'Debate encerrado · placar final' }
  const seconds = Math.floor((now - (snapshot?.atualizado || now)) / 1000)
  const vivo = seconds < 120
  const video = snapshot?.video
  let reprise = ''
  if (video && !video.ao_vivo && video.data) {
    const parsed = Date.parse(video.data)
    if (!Number.isNaN(parsed)) reprise = ` · reprise do debate de ${dataCurta(parsed)}`
  }
  const pausa = snapshot?.pausado ? ' · checagem automática pausada' : ''
  if (vivo) return { vivo: true, texto: `Ao vivo · checagem ~30s atrás da TV${reprise}${pausa}` }
  const minutes = Math.round(seconds / 60)
  if (minutes > 60 * 24) {
    return { vivo: false, texto: `Última atualização em ${dataCurta(snapshot?.atualizado || now)}${pausa}` }
  }
  return { vivo: false, texto: `Última atualização há ${minutes} min${pausa}` }
}

export function positionLabel(snapshot, now, mode) {
  const video = snapshot?.video || {}
  const raw = positionMs(snapshot, now, mode)
  const stale = mode !== 'demo' && !snapshot?.simulado && !video.ao_vivo && now - originMs(snapshot) > 6 * 60 * 60 * 1000
  if (stale) return 'Reprise'
  return rotuloDuracao(raw)
}

const ARCHIVE_OK = /^[\w-]{1,40}$/

export function feedUrl({ base = '', archive = '', now = 0, demo = false } = {}) {
  const bust = Math.floor(now / 3000)
  const safeArchive = ARCHIVE_OK.test(archive) ? archive : ''
  if (demo) {
    const name = safeArchive ? `demo/placar-${safeArchive}.json` : 'demo/placar.json'
    return `${name}?t=${bust}`
  }
  let root = String(base).trim()
  if (/placar[^/?#]*\.json($|\?)/.test(root) && !safeArchive) {
    const join = root.includes('?') ? '&' : '?'
    return `${root}${join}t=${bust}`
  }
  root = root.replace(/placar[^/?#]*\.json(\?.*)?$/, '')
  if (!root.endsWith('/')) root += '/'
  const file = safeArchive ? `placar-${safeArchive}.json` : 'placar.json'
  return `${root}${file}?t=${bust}`
}

export function resolveFeed(search, baseDefault, now, startMode = 'live') {
  const raw = search.startsWith('?') ? search.slice(1) : search
  const query = new URLSearchParams(raw)
  const archive = (query.get('d') || '').trim()
  const src = (query.get('src') || '').trim()
  const wantLive = query.get('live') === '1' || Boolean(src)
  const wantDemo = query.get('demo') === '1' || (!wantLive && (startMode === 'demo' || !baseDefault))
  if (wantDemo) return { mode: 'demo', base: '', url: feedUrl({ demo: true, archive, now }), archive }
  const base = src || baseDefault
  return { mode: 'live', base, url: feedUrl({ base, archive, now }), archive }
}

export function changedStamp(previous, snapshot) {
  if (!snapshot || typeof snapshot.atualizado === 'undefined') return true
  return snapshot.atualizado !== previous
}

export function createFeed({ urlFor, intervalMs = 5000, fetchImpl, isHidden = () => false, onData, onError }) {
  let stamp
  let timer = 0
  let stopped = false
  let seen = false

  async function tick() {
    if (stopped || isHidden()) return
    try {
      const response = await fetchImpl(urlFor(Date.now()))
      if (stopped) return
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (stopped) return
      if (!seen || changedStamp(stamp, data)) {
        seen = true
        stamp = data.atualizado
        onData(data)
      }
    } catch (error) {
      if (!stopped) onError?.(error)
    }
  }

  function arm() {
    clearInterval(timer)
    if (!stopped) timer = setInterval(() => { tick() }, intervalMs)
  }

  return {
    tick,
    start() { stopped = false; tick(); arm() },
    stop() { stopped = true; clearInterval(timer) },
    pause() { clearInterval(timer) },
    resume() { if (!stopped) { tick(); arm() } },
  }
}

export function safeHttpUrl(url) {
  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') return parsed.href
  } catch { /* ignora */ }
  return ''
}

export function youtubeId(id) {
  return /^[\w-]{6,20}$/.test(id || '') ? id : ''
}

export function sharePlacar(snapshot, mode, pageUrl) {
  const candidates = candidatesOf(snapshot)
  if (candidates.length < 2) return 'Placar da Verdade'
  const [left, right] = candidates
  const pct = (candidate) => {
    const index = errorIndex(candidate)
    return index.total ? `${index.erroPct}%` : '–'
  }
  const estado = snapshot.encerrado ? ' (placar final)' : mode === 'demo' || snapshot.simulado ? ' (simulação)' : ', ao vivo'
  const aviso = mode === 'demo' || snapshot.simulado ? '\nFatos fictícios, só para demonstrar o placar.' : ''
  return `Mentirômetro do debate${estado}: ${left.nome} ${pct(left)} x ${right.nome} ${pct(right)} de erro\n${left.nome}: ${left.propostas} propostas x ${left.ataques} ataques. ${right.nome}: ${right.propostas} propostas x ${right.ataques} ataques${aviso}\n${pageUrl}`
}


const COLORS = ['#E5484D', 'verde-amarelo']
const GREEN = '#2FBF71'
const YELLOW = '#F5D33B'
const SPLIT = 'verde-amarelo'

/** Fundo: cor sólida, ou metade verde / metade amarelo com corte seco (sem mistura). */
export function paintBg(color, dir = '90deg') {
  if (color === SPLIT) return `linear-gradient(${dir},${GREEN} 50%,${YELLOW} 50%)`
  return esc(color)
}

/** Texto: cor sólida, ou degradê com corte seco recortado no texto. */
export function paintText(color) {
  if (color === SPLIT) {
    return `background:linear-gradient(90deg,${GREEN} 50%,${YELLOW} 50%);-webkit-background-clip:text;background-clip:text;color:transparent;-webkit-text-fill-color:transparent`
  }
  return `color:${esc(color)}`
}
const VERDICT_COLOR = {
  verdadeiro: '#4CC38A',
  impreciso: '#D9B44A',
  falso: '#EB6F6F',
  sem_dados: '#8B8D98',
  em_revisao: '#A594F9',
  checando: '#8A8F98',
}

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]))
}

export function candidateColor(candidate, index) {
  const raw = candidate?.cor || candidate?.color
  if (typeof raw === 'string' && /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(raw)) return raw
  return COLORS[index % COLORS.length]
}

export function falsasCount(candidate = {}) {
  return (candidate.falso || 0) + (candidate.impreciso || 0)
}

/** Largura do cabo de guerra: o índice de erro de cada lado, a mesma conta do ponteiro. */
export function tugOfWar(left, right) {
  const a = errorIndex(left)
  const b = errorIndex(right)
  const sum = a.erro + b.erro
  const leftPct = sum === 0 ? 50 : Math.round((a.erro / sum) * 100)
  return { leftPct, rightPct: 100 - leftPct, leftFalsas: falsasCount(left), rightFalsas: falsasCount(right) }
}

export function pendeLabel(left, right, leftColor, rightColor) {
  const reading = mentiromentro(left.nome, right.nome, left, right)
  if (reading.call === 'waiting') return { text: 'aguardando fatos', name: '', color: '', reading }
  if (reading.call === 'tie') return { text: 'empate', name: '', color: '', reading }
  if (reading.call === 'left') return { text: 'pende para', name: left.nome, color: leftColor, reading }
  return { text: 'pende para', name: right.nome, color: rightColor, reading }
}

export function feedItems(snapshot) {
  const items = []
  for (const claim of claimsOf(snapshot)) {
    items.push({
      kind: 'claim',
      t: claim.t,
      quem: claim.quem,
      text: claim.afirmacao,
      claim,
      key: claimKey(claim),
    })
  }
  for (const proposal of snapshot?.propostas || []) {
    items.push({
      kind: 'proposta',
      t: proposal.t,
      quem: proposal.quem,
      text: proposal.titulo,
      proposal,
      key: `p|${proposal.t}|${proposal.quem}|${proposal.titulo}`,
    })
  }
  for (const attack of snapshot?.ataques || []) {
    items.push({
      kind: 'ataque',
      t: attack.t,
      quem: attack.quem,
      text: attack.resumo,
      attack,
      key: `a|${attack.t}|${attack.quem}|${attack.resumo}`,
    })
  }
  items.sort((a, b) => a.t - b.t)
  return items
}

export function resolveVideoId(snapshot, override = '') {
  return youtubeId(override || snapshot?.video?.id || '')
}

function tag(label, color) {
  if (!color) return `<span class="tag t2">${esc(label)}</span>`
  return `<span class="tag"><i style="background:${paintBg(color)}"></i>${esc(label)}</span>`
}

/** Fontes clicáveis de uma checagem (fonte única ou lista fontes[]), só http(s). */
export function sourcesOf(claim) {
  const raw = [...(Array.isArray(claim?.fontes) ? claim.fontes : []), ...(claim?.fonte ? [claim.fonte] : [])]
  const seen = new Set()
  const out = []
  for (const src of raw) {
    const url = safeHttpUrl(src?.url)
    if (!url || seen.has(url)) continue
    seen.add(url)
    let host = ''
    try { host = new URL(url).hostname.replace(/^www\./, '') } catch { /* ok */ }
    out.push({ url, titulo: src.titulo || host || 'Fonte', host, oficial: /(^|\.)(gov\.br|leg\.br|jus\.br|ibge\.gov\.br|bcb\.gov\.br)$/.test(host) })
  }
  return out.sort((a, b) => Number(b.oficial) - Number(a.oficial))
}

/** Nunca mostra veredito sem fonte: verdadeiro/impreciso/falso sem link vira "Sem dados". */
export function shownVerdict(claim) {
  const v = claim?.veredito
  if ((v === 'verdadeiro' || v === 'impreciso' || v === 'falso') && !sourcesOf(claim).length) return 'sem_dados'
  return v
}

/** Placar do lado: só vereditos com fonte (shownVerdict) contam. */
export function sideScore(claims, quem) {
  const out = { verdades: 0, mentiras: 0, imprecisos: 0 }
  for (const claim of claims || []) {
    if (quem != null && claim?.quem !== quem) continue
    const v = shownVerdict(claim)
    if (v === 'verdadeiro') out.verdades++
    else if (v === 'falso') out.mentiras++
    else if (v === 'impreciso') out.imprecisos++
  }
  return out
}

export const colTabs = new Map() // quem -> 'checagens' | 'propostas'

function itemTag(item) {
  if (item.kind === 'proposta') return tag('Proposta')
  if (item.kind === 'ataque') return tag('Ataque')
  const verdict = shownVerdict(item.claim)
  return tag(VERDICT_LABEL[verdict] || verdict, VERDICT_COLOR[verdict])
}

function passes(item, filter) {
  if (filter?.quem && item.quem !== filter.quem) return false
  if (filter?.verdict) {
    if (item.kind !== 'claim' || item.claim.veredito !== filter.verdict) return false
  }
  if (filter?.windowStartMs != null && filter?.windowEndMs != null) {
    if (item.t < filter.windowStartMs || item.t >= filter.windowEndMs) return false
  }
  return true
}

function sideItems(items, id, fresh, align) {
  return items.filter((item) => item.quem === id).slice(-5).map((item) => itemButton(item, fresh, `it ${align}`)).join('')
}

function itemButton(item, fresh, cls) {
  const freshCls = fresh?.has(item.key) ? ' fresh' : ''
  return `<button type="button" class="${cls}${freshCls}" data-act="item" data-arg="${esc(item.key)}">
    <span class="meta"><span>${hhmm(item.t)}</span>${itemTag(item)}</span>
    <span class="q">${esc(item.text)}</span>
  </button>`
}

function stageSvg(colorA, colorB) {
  return `<svg class="stage" data-vid="" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <radialGradient id="g1" cx=".5" cy=".35" r=".7"><stop offset="0" stop-color="#1a1d26"/><stop offset=".6" stop-color="#0c0d12"/><stop offset="1" stop-color="#050506"/></radialGradient>
      <radialGradient id="sp" cx=".5" cy="0" r="1"><stop offset="0" stop-color="#fff" stop-opacity=".09"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      <linearGradient id="gyv" x1="0" y1="0" x2="0" y2="1"><stop offset=".5" stop-color="#2FBF71"/><stop offset=".5" stop-color="#F5D33B"/></linearGradient><linearGradient id="fl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#14161d"/><stop offset="1" stop-color="#08090b"/></linearGradient>
    </defs>
    <rect width="1600" height="900" fill="url(#g1)"/>
    <rect y="620" width="1600" height="280" fill="url(#fl)"/>
    <path d="M0 620H1600" stroke="#ffffff10"/>
    <path d="M540 0L440 700H760L670 0Z" fill="url(#sp)"/>
    <path d="M930 0L840 700H1160L1060 0Z" fill="url(#sp)"/>
    <g fill="#262a36" stroke="#ffffff1f">
      <circle cx="600" cy="430" r="34"/><path d="M540 520q60-60 120 0v40h-120z"/>
      <path d="M510 540h180l-15 160h-150z" fill="#12141b" stroke="${colorA === SPLIT ? 'url(#gyv)' : esc(colorA)}" stroke-opacity=".5"/>
      <circle cx="1000" cy="430" r="34"/><path d="M940 520q60-60 120 0v40h-120z"/>
      <path d="M910 540h180l-15 160h-150z" fill="#12141b" stroke="${colorB === SPLIT ? 'url(#gyv)' : esc(colorB)}" stroke-opacity=".5"/>
    </g>
    <rect x="770" y="360" width="60" height="120" rx="4" fill="#0f1117" stroke="#ffffff0d"/>
  </svg><span class="play" aria-hidden="true">▶</span>`
}

function videoHtml(state, colorA, colorB) {
  const id = resolveVideoId(state.snapshot, state.videoOverride || '')
  const demo = state.mode === 'demo' || state.snapshot.simulado
  const status = statusCopy(state.snapshot, state.now, state.mode)
  let pill = 'PLACAR'
  if (state.snapshot.encerrado) pill = 'ENCERRADO'
  else if (demo) pill = 'SIMULAÇÃO'
  else if (status.vivo) pill = 'AO VIVO'
  const live = status.vivo && !demo && !state.snapshot.encerrado
  if (state.replay) {
    // O player mora fora do #app (#rhost) e nunca é recriado nem movido: mover um
    // iframe no DOM recarrega o vídeo (era o que quebrava ao arrastar a barra do YouTube).
    return `<div class="video rvideo"><span class="live">REPLAY</span>
    <div class="rbar" role="group" aria-label="Controle do replay"><button type="button" data-act="rseek" data-arg="-30">−30s</button><span class="rtime">${esc(mmss(state.replaySec || 0))}</span><button type="button" data-act="rseek" data-arg="30">+30s</button></div>
    <button type="button" class="eye" data-act="overlays" aria-pressed="${state.quiet ? 'true' : 'false'}">${state.quiet ? 'Mostrar' : 'Ocultar'}</button>
    <button type="button" class="fsb" data-act="fs" aria-pressed="${state.fs ? 'true' : 'false'}" aria-label="${state.fs ? 'Sair da tela cheia' : 'Tela cheia'}">${state.fs ? '✕ Sair' : '⛶ Tela cheia'}</button></div>`
  }
  const media = id
    ? `<iframe class="stage" data-vid="${esc(id)}" title="Transmissão do debate no YouTube" src="https://www.youtube-nocookie.com/embed/${esc(id)}?rel=0&fs=0&playsinline=1" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>`
    : stageSvg(colorA, colorB)
  return `<div class="video">${media}<span class="live${live ? ' on' : ''}">${live ? '<i></i>' : ''}${pill}</span>
    <button type="button" class="eye" data-act="overlays" aria-pressed="${state.quiet ? 'true' : 'false'}">${state.quiet ? 'Mostrar' : 'Ocultar'}</button>
    <button type="button" class="fsb" data-act="fs" aria-pressed="${state.fs ? 'true' : 'false'}" aria-label="${state.fs ? 'Sair da tela cheia' : 'Tela cheia'}">${state.fs ? '✕ Sair' : '⛶ Tela cheia'}</button></div>`
}

function scoreHtml(snapshot) {
  const people = candidatesOf(snapshot)
  if (people.length < 2) {
    return `<header class="top"><div class="logo">Placar da Verdade</div><p class="muted">Aguardando os dois candidatos.</p></header>`
  }
  const [left, right] = people
  const colorA = candidateColor(left, 0)
  const colorB = candidateColor(right, 1)
  const tug = tugOfWar(left, right)
  const pende = pendeLabel(left, right, colorA, colorB)
  const score = (candidate) => {
    const index = errorIndex(candidate)
    return index.total ? String(index.erroPct) : '–'
  }
  const who = pende.name
    ? `${esc(pende.text)} <b style="${paintText(pende.color)}">${esc(pende.name)}</b>`
    : esc(pende.text)
  const label = `Mentirômetro: ${left.nome} ${score(left)}% de erro, ${right.nome} ${score(right)}%. ${pende.reading.headline}. ${pende.reading.detail}`
  return `<header class="top">
    <div class="logo">Placar da Verdade</div>
    <div class="cand"><span class="dot" style="background:${paintBg(colorA)}"></span>
      <div><div class="nm">${esc(left.nome)}</div><div class="sub">${left.propostas || 0} propostas · ${left.ataques || 0} ataques</div></div>
      <div class="sc">${score(left)}</div></div>
    <div class="meter" role="img" aria-label="${esc(label)}">
      <div class="lbl">Mentirômetro <span>${who}</span></div>
      <div class="bar"><div style="width:${tug.leftPct}%;background:${paintBg(colorA)}"></div><div style="flex:1;background:${paintBg(colorB)}"></div></div>
      <div class="lbl2"><span>${tug.leftFalsas} falsas/imprecisas</span><span>${tug.rightFalsas}</span></div>
    </div>
    <div class="cand r"><div class="sc">${score(right)}</div>
      <div style="text-align:right"><div class="nm">${esc(right.nome)}</div><div class="sub">${right.propostas || 0} propostas · ${right.ataques || 0} ataques</div></div>
      <span class="dot" style="background:${paintBg(colorB)}"></span></div>
    <nav class="menu" aria-label="Seções">
      ${typeof window !== 'undefined' && window.PLACAR_REPLAY && !/[?&]replay=/.test(window.location?.search || '') ? `<a class="word" href="${esc(window.PLACAR_REPLAY)}">Replay</a>` : ''}
      <button type="button" class="word" data-act="panel" data-arg="linha">Linha do tempo</button>
      <button type="button" class="word" data-act="panel" data-arg="ler">Como ler</button>
      <button type="button" class="word" data-act="panel" data-arg="funciona">Como funciona</button>
      <button type="button" class="k" data-act="panel" data-arg="cmd" aria-label="Abrir comandos"><kbd>⌘K</kbd></button>
    </nav>
  </header>`
}

function cardHtml(item, person, color, fresh) {
  const freshCls = fresh?.has(item.key) ? ' fresh' : ''
  const claim = item.claim
  let body = ''
  if (item.kind === 'claim') {
    const srcs = sourcesOf(claim)
    const semFonte = shownVerdict(claim) !== claim.veredito
    const motivo = isChecking(claim) ? 'Checando fontes…' : (semFonte ? 'Sem fonte publicada para comprovar; não conta como checagem.' : (claim.motivo || ''))
    const links = srcs.map((src) => `<a class="src" href="${esc(src.url)}" target="_blank" rel="noopener noreferrer">${src.oficial ? '<b class="of">Oficial</b>' : ''}${esc(src.titulo)}${src.host ? ` <span class="host">· ${esc(src.host)}</span>` : ''} ↗</a>`).join('')
    body = `${motivo ? `<span class="cm">${esc(motivo)}</span>` : ''}</button>
      ${srcs.length && !isChecking(claim) ? `<a class="fbtn" href="${esc(srcs[0].url)}" target="_blank" rel="noopener noreferrer">${srcs[0].oficial ? 'Fonte oficial' : 'Fonte'} ↗</a>` : ''}
      ${links ? `<div class="srcs"><span class="sl">Fonte${srcs.length > 1 ? 's' : ''}</span>${links}</div>` : (isChecking(claim) ? '' : '<span class="src muted">Sem fonte encontrada</span>')}`
  } else {
    const extra = item.proposal?.explicacao || ''
    body = `${extra && extra.toLowerCase() !== String(item.text).toLowerCase() ? `<span class="cm">${esc(extra)}</span>` : ''}${item.proposal?.vezes > 1 ? `<span class="cm">Citada ${item.proposal.vezes} vezes</span>` : ''}</button>`
  }
  const stamp = item.replay ? mmss(item.t / 1000) : hhmm(item.t)
  return `<article class="card${freshCls}" data-quem="${esc(item.quem)}" data-kind="${item.kind}" style="--c:${paintBg(color, '180deg')}">
    <button type="button" class="cb" data-act="item" data-arg="${esc(item.key)}">
      <span class="ch"><b style="${paintText(color)}">${esc(person.nome)}</b><span class="muted">${esc(stamp)}</span>${itemTag(item)}</span>
      <span class="q">${esc(item.text)}</span>
      ${body}
  </article>`
}

/** Coluna de um candidato: as checagens (com veredito e fonte) e as propostas dele. */
function columnHtml(items, people, index, fresh, side, all = []) {
  const person = people[index]
  const color = candidateColor(person, index)
  const mine = items.filter((item) => item.quem === person.id).slice().reverse()
  const claims = mine.filter((item) => item.kind === 'claim')
  const props = mine.filter((item) => item.kind === 'proposta')
  const sc = sideScore(all, person.id)
  const tab = colTabs.get(person.id) === 'propostas' ? 'propostas' : 'checagens'
  const list = tab === 'propostas' ? props : claims
  const empty = tab === 'propostas' ? 'Nenhuma proposta concreta ainda.' : 'Nenhuma afirmação checável ainda.'
  const tbtn = (id, label) => `<button type="button" role="tab" class="ctab${tab === id ? ' on' : ''}" aria-selected="${tab === id}" data-act="ctab" data-arg="${esc(person.id)}:${id}">${label}</button>`
  return `<aside class="col-c ${side}" aria-label="${esc(person.nome)}" data-quem="${esc(person.id)}" style="--c:${paintBg(color, '180deg')}">
    <div class="colh"><div class="colname" style="${paintText(color)}">${esc(person.nome)}</div>
      <div class="score"><b class="sv">${sc.verdades}</b> ${sc.verdades === 1 ? 'Verdade' : 'Verdades'} <span class="vs">vs</span> <b class="sm">${sc.mentiras}</b> ${sc.mentiras === 1 ? 'Mentira' : 'Mentiras'}${sc.imprecisos ? ` <small class="si">· ${sc.imprecisos} impreciso${sc.imprecisos > 1 ? 's' : ''}</small>` : ''}</div>
      <div class="ctabs" role="tablist">${tbtn('checagens', 'Checagens')}<span class="sep">|</span>${tbtn('propostas', `Propostas (${props.length})`)}</div></div>
    <div class="colbody">
      <section class="csec">${list.length ? list.map((item) => cardHtml(item, person, color, fresh)).join('') : `<p class="muted empty">${empty}</p>`}</section>
    </div>
  </aside>`
}

function listsHtml(items, people, fresh, all) {
  if (people.length < 2) return ''
  return `${columnHtml(items, people, 0, fresh, 'a', all)}${columnHtml(items, people, 1, fresh, 'b', all)}`
}

const FLIP_MS = 950
const flips = new Map() // key -> { checking: bool, doneAt: ms }

export function isChecking(claim) {
  if (!claim) return false
  if (claim.veredito === 'checando') return true
  return claim.veredito === 'em_revisao' && /^Áudio e fontes ainda/.test(claim.motivo || '')
}

// Estado da animação: 'front' (checando), 'flip' (virando agora, com atraso negativo) ou 'back'.
export function flipState(key, checking, now = Date.now(), memo = flips) {
  const seen = memo.get(key) || { checking: false, doneAt: 0 }
  if (checking) {
    memo.set(key, { checking: true, doneAt: 0 })
    return { face: 'front', delay: 0 }
  }
  if (seen.checking && !seen.doneAt) seen.doneAt = now
  memo.set(key, seen)
  const elapsed = seen.doneAt ? now - seen.doneAt : Infinity
  return elapsed < FLIP_MS ? { face: 'flip', delay: elapsed } : { face: 'back', delay: 0 }
}

function captionHtml(item, people, vivo) {
  if (!item) {
    return `<div class="capw"><div class="cap" style="--c:#62666D"><div class="capq">Aguardando a primeira afirmação checável.</div><div class="cape">A legenda mostra o resumo de cada afirmação e, em seguida, a checagem.</div></div></div>`
  }
  const person = people.find((candidate) => candidate.id === item.quem)
  const index = Math.max(0, people.findIndex((candidate) => candidate.id === item.quem))
  const color = candidateColor(person || {}, index)
  const claim = item.claim || {}
  const srcs0 = sourcesOf(claim)
  const fonte = srcs0.length ? `<a href="${esc(srcs0[0].url)}" target="_blank" rel="noopener noreferrer">Fonte: ${esc(srcs0[0].titulo)} ↗</a>` : ''
  const motivo = claim.motivo ? esc(claim.motivo) : 'Ainda sem motivo publicado.'
  const stamp = vivo ? `${hhmm(item.t)} · agora` : (item.replay ? mmss(item.t / 1000) : hhmm(item.t))
  const checking = isChecking(claim)
  const st = flipState(item.key, checking)
  const who = `<span style="${paintText(color)}">${esc(person?.nome || '')}</span><span class="muted">${esc(stamp)}</span>`
  const banco = claim.banco ? `<span class="muted">· checagem de ${esc(claim.banco)}</span>` : ''
  const cls = st.face === 'back' ? ' is-done' : (st.face === 'flip' ? ' is-done anim' : '')
  const delay = st.face === 'flip' ? ` style="--fd:-${Math.round(st.delay)}ms"` : ''
  return `<div class="capw"><div class="flip3d${cls}"${delay} data-cap="${esc(item.key)}" data-face="${st.face}">
    <div class="fc-inner">
      <div class="cap fc-front" style="--c:${paintBg(color, '180deg')}" aria-hidden="${checking ? 'false' : 'true'}">
        <div class="capm">${who}<span class="tag chk"><i class="spin"></i>Checando…</span></div>
        <div class="capq">${esc(item.text)}</div>
        <div class="cape">Buscando fontes e conferindo com dois modelos.</div>
      </div>
      <div class="cap fc-back" style="--c:${paintBg(color, '180deg')}" aria-hidden="${checking ? 'true' : 'false'}">
        <div class="capm">${who}${checking ? '' : itemTag(item)}${banco}</div>
        <div class="capq">${esc(item.text)}</div>
        <div class="cape">${checking ? '' : `${motivo} ${fonte}`}</div>
      </div>
    </div>
  </div></div>`
}

/** Última afirmação com veredito comprovado por fonte (até `untilT`, se dado). */
export function lastVerified(items, untilT = Infinity) {
  for (let i = items.length - 1; i >= 0; i--) {
    const it = items[i]
    if (it.kind !== 'claim' || it.t > untilT) continue
    const v = shownVerdict(it.claim)
    if (v === 'verdadeiro' || v === 'falso' || v === 'impreciso') return it
  }
  return null
}

/** Minuto:segundo do debate em que foi dito (replay: t relativo em ms; ao vivo: epoch − começo). */
export function debateClock(item, snapshot, replay) {
  const rel = replay ? item.t : item.t - originMs(snapshot)
  if (!Number.isFinite(rel) || rel < 0) return hhmm(item.t)
  const sec = Math.floor(rel / 1000)
  const h = Math.floor(sec / 3600); const m = Math.floor((sec % 3600) / 60); const ss = sec % 60
  const p2 = (n) => String(n).padStart(2, '0')
  return h ? `${h}:${p2(m)}:${p2(ss)}` : `${p2(m)}:${p2(ss)}`
}

function verifiedCaptionHtml(item, people, snapshot, replay) {
  const person = people.find((c) => c.id === item.quem)
  const index = Math.max(0, people.findIndex((c) => c.id === item.quem))
  const color = candidateColor(person || {}, index)
  const srcs = sourcesOf(item.claim)
  const fbtn = srcs.length ? `<a class="fbtn" href="${esc(srcs[0].url)}" target="_blank" rel="noopener noreferrer">${srcs[0].oficial ? 'Fonte oficial' : 'Fonte'} ↗</a>` : ''
  return `<div class="capw"><div class="cap capv" data-cap="${esc(item.key)}" style="--c:${paintBg(color, '180deg')}">
    <div class="capm"><span class="muted">${esc(debateClock(item, snapshot, replay))}</span><span style="${paintText(color)}">${esc(person?.nome || '')}</span>${itemTag(item)}</div>
    <div class="capq">${esc(item.text)}</div>
    <div class="cape">${fbtn}</div>
  </div></div>`
}

function pickCaption(state, items) {
  const claims = items.filter((item) => item.kind === 'claim')
  if (state.replay) {
    const target = captionClaim(state.replay, state.replaySec || 0)
    if (!target) return null
    const item = claims.find((it) => (target.id && it.claim.id === target.id) || it.claim.afirmacao === target.afirmacao) || null
    return item ? { ...item, replay: true } : null
  }
  for (let i = claims.length - 1; i >= 0; i--) {
    if (withinCaption(claims[i].claim)) return claims[i]
  }
  return null
}

function mobileFeed(items, people, filter, fresh, all) {
  if (people.length < 2) return ''
  const chosen = Math.max(0, people.findIndex((p) => p.id === filter?.quem))
  const tabs = people.map((p, i) => (
    `<button type="button" role="tab" class="mtab${i === chosen ? ' on' : ''}" aria-selected="${i === chosen}" data-act="quem" data-arg="${esc(p.id)}" style="--c:${paintBg(candidateColor(p, i), '90deg')}">${esc(p.nome)}</button>`)).join('')
  return `<div class="mfeed">
    <div class="mtabs" role="tablist" aria-label="Escolher candidato">${tabs}</div>
    ${columnHtml(items, people, chosen, fresh, 'm', all)}</div>`
}

function sheet(title, body) {
  return `<div class="back" data-act="close"><div class="sheet" role="dialog" aria-modal="true" aria-label="${esc(title)}">
    <div class="sheet-h"><h2>${esc(title)}</h2><button type="button" class="x" data-act="close" aria-label="Fechar">✕</button></div>
    ${body}
  </div></div>`
}

function panelHtml(state, items) {
  const panel = state.panel
  if (!panel) return ''
  const snapshot = state.snapshot
  if (panel === 'cmd') {
    const buttons = [
      ['linha', 'Linha do tempo'],
      ['ler', 'Como ler'],
      ['funciona', 'Como funciona'],
      ['propostas', 'Propostas'],
      ['arquivo', 'Debates passados'],
    ].map(([id, label]) => `<button type="button" data-act="panel" data-arg="${id}">${label}</button>`).join('')
    const onDemo = state.mode === 'demo'
    const source = onDemo
      ? `<button type="button" data-act="source" data-arg="live">Placar público</button>`
      : `<button type="button" data-act="source" data-arg="demo">Voltar à simulação</button>`
    return sheet('Comandos', `<div class="cmd">${buttons}${source}</div>`)
  }
  if (panel === 'ler') {
    return sheet('Como ler', `<div class="prose">
      <p>${tag('Verdadeiro', VERDICT_COLOR.verdadeiro)} os dados confirmam</p>
      <p>${tag('Impreciso', VERDICT_COLOR.impreciso)} exagerado ou fora de contexto</p>
      <p>${tag('Falso', VERDICT_COLOR.falso)} os dados contradizem</p>
      <p>${tag('Sem dados', VERDICT_COLOR.sem_dados)} não deu para verificar</p>
      <p>${tag('Em revisão', VERDICT_COLOR.em_revisao)} o áudio não confirmou a frase; fica fora do placar até a conferência</p>
      <p>O número grande é o índice de erro: falso vale 1, impreciso vale meio, verdadeiro vale 0. Sem dados e em revisão ficam de fora. A barra pende para quem tem o índice mais alto, e só depois de 3 fatos checáveis de cada lado.</p>
    </div>`)
  }
  if (panel === 'funciona') {
    const demo = state.mode === 'demo' || snapshot.simulado
    return sheet('Como funciona', `<div class="prose">
      <p>O áudio do debate é transcrito a cada 10 segundos e a voz identifica quem está falando. Uma IA lê cada fala e separa as afirmações que valem checagem (números, dados, atos de governo), as propostas concretas e os ataques ao adversário. Retórica e opinião não viram checagem.</p>
      <p>Cada afirmação é buscada na web (agências de checagem, imprensa e dados oficiais) e julgada com as mesmas regras para os dois candidatos.</p>
      <p>Antes de publicar um "falso" ou "impreciso", o trecho é ouvido de novo por outros modelos para confirmar a frase exata. Se o áudio não confirmar, o fato fica "em revisão" e não conta no placar.</p>
      <p><strong>É uma checagem automática e pode errar.</strong> Confira a fonte antes de compartilhar.</p>
      <p class="muted">${demo ? 'Você está na simulação. Os fatos são fictícios.' : `Fonte dos dados: ${esc(state.sourceLabel || '')}`}</p>
    </div>`)
  }
  if (panel === 'propostas') {
    const blocks = candidatesOf(snapshot).map((candidate, index) => {
      const mine = (snapshot.propostas || []).filter((proposal) => proposal.quem === candidate.id)
        .slice().sort((a, b) => (b.vezes - a.vezes) || (b.t - a.t))
      const cards = mine.length
        ? mine.map((proposal) => `<article class="prop"><h3>${esc(proposal.titulo)}</h3><p>${esc(proposal.explicacao || '')}</p>${proposal.vezes > 1 ? `<p class="muted">Citada ${proposal.vezes} vezes</p>` : ''}</article>`).join('')
        : '<p class="muted">Nenhuma proposta concreta até agora.</p>'
      return `<section><h3 style="${paintText(candidateColor(candidate, index))}">${esc(candidate.nome)}</h3>${cards}</section>`
    }).join('')
    return sheet('Propostas', `<p class="muted">O que cada candidato propôs de concreto, da mais repetida para a mais recente.</p><div class="pair">${blocks}</div>`)
  }
  if (panel === 'linha') {
    const timeline = timelineOf(snapshot)
    const filter = state.filter || {}
    if (!timeline.rows.length) return sheet('Linha do tempo', '<p class="muted">A linha do tempo começa no primeiro ataque ou proposta.</p>')
    const columns = timeline.rows[0].columns
    const rows = timeline.rows.map((row) => {
      const cols = row.columns.map((column) => {
        const active = filter.windowStartMs === column.startMs
        const stack = Math.max(1, timeline.maxStack)
        const attackH = column.attacks ? Math.max(3, (column.attacks / stack) * 48) : 0
        const proposalH = column.proposals ? Math.max(3, (column.proposals / stack) * 48) : 0
        return `<button type="button" class="col${active ? ' on' : ''}" data-act="window" data-arg="${column.startMs}:${column.endMs}" aria-pressed="${active ? 'true' : 'false'}" aria-label="${esc(row.name)} ${hhmm(column.startMs)}">${column.attacks ? `<i class="atk" style="height:${attackH.toFixed(0)}px"></i>` : ''}${column.proposals ? `<i class="pro" style="height:${proposalH.toFixed(0)}px"></i>` : ''}</button>`
      }).join('')
      return `<div class="trow"><span>${esc(row.name)}</span><div class="cols">${cols}</div></div>`
    }).join('')
    const hours = columns.map((column, index) => `<span>${index % timeline.labelStep === 0 ? hhmm(column.startMs) : ''}</span>`).join('')
    const clear = filter.windowStartMs != null ? `<button type="button" class="tag" data-act="window" data-arg="clear">${hhmm(filter.windowStartMs)}–${hhmm(filter.windowEndMs)} ✕</button>` : ''
    return sheet('Linha do tempo', `<p class="muted">A cada 5 minutos. Toque numa coluna para ver os itens daquele trecho.</p><p class="legend"><i class="atk"></i> Ataques <i class="pro"></i> Propostas ${clear}</p><div class="tchart">${rows}<div class="hours">${hours}</div></div>`)
  }
  if (panel === 'arquivo') {
    const current = state.archive || ''
    return sheet('Debates passados', `<form class="archive" data-act="archive">
      <label>Data do debate <input name="d" inputmode="numeric" placeholder="2026-10-18" value="${esc(current)}" autocomplete="off"></label>
      <button type="submit" class="go">Abrir</button>
    </form><p class="muted">O arquivo é <span class="mono">placar-AAAA-MM-DD.json</span> no mesmo host do placar. Na simulação, 18/10 está salvo localmente.</p>
    <button type="button" class="word link" data-act="hoje">Voltar ao debate de agora</button>`)
  }
  if (panel === 'detalhe') {
    const item = items.find((entry) => entry.key === state.detailKey) || feedItems(snapshot).find((entry) => entry.key === state.detailKey)
    if (!item) return ''
    const person = candidatesOf(snapshot).find((candidate) => candidate.id === item.quem)
    const index = Math.max(0, candidatesOf(snapshot).findIndex((candidate) => candidate.id === item.quem))
    const color = candidateColor(person || {}, index)
    let extra = ''
    if (item.kind === 'claim') {
      const srcs = sourcesOf(item.claim)
      extra = `${item.claim.literal ? `<p class="quote">“${esc(item.claim.literal)}”</p>` : ''}
        <p>${esc(item.claim.motivo || 'Ainda sem motivo publicado.')}</p>
        ${srcs.length ? srcs.map((src) => `<p><a href="${esc(src.url)}" target="_blank" rel="noopener noreferrer">${esc(src.titulo)} ↗</a> <span class="muted">${esc(src.host)}</span></p>`).join('') : '<p class="muted">Nenhuma fonte encontrada.</p>'}
        ${item.claim.corrigido ? `<p class="muted">${item.claim.corrigido.por === 'qa_manual' ? 'Corrigido na revisão humana (QA) após o debate' : 'Revisado após o debate'} · a checagem automática dizia ${esc(VERDICT_LABEL[item.claim.corrigido.antes] || '')}</p>` : ''}`
    } else if (item.kind === 'proposta') {
      extra = `<p>${esc(item.proposal.explicacao || '')}</p>${item.proposal.vezes > 1 ? `<p class="muted">Citada ${item.proposal.vezes} vezes</p>` : ''}`
    }
    return sheet(person?.nome || 'Detalhe', `<div class="cap flat" style="--c:${paintBg(color, '180deg')}">
      <div class="capm"><span style="${paintText(color)}">${esc(person?.nome || '')}</span><span class="muted">${hhmm(item.t)}</span>${itemTag(item)}</div>
      <div class="capq">“${esc(item.text)}”</div>
      <div class="cape">${extra}</div>
    </div>`)
  }
  return ''
}

export function renderBoard(state) {
  const snapshot = state.snapshot
  const people = candidatesOf(snapshot)
  const colorA = candidateColor(people[0] || {}, 0)
  const colorB = candidateColor(people[1] || {}, 1)
  const items = feedItems(snapshot).filter((item) => passes(item, { ...state.filter, quem: '' }))
  const demo = state.mode === 'demo' || snapshot.simulado
  const status = statusCopy(snapshot, state.now || Date.now(), state.mode)
  const note = state.banner || snapshot.aviso || (demo ? 'Simulação com fatos fictícios. Não é a checagem do debate.' : '')
  return `${videoHtml(state, colorA, colorB)}
    <div class="edge"></div>
    ${scoreHtml(snapshot)}
    ${note ? `<p class="simline" role="status">${esc(note)}</p>` : ''}
    ${listsHtml(items, people, state.fresh, claimsOf(snapshot))}
    ${(() => {
      const all = feedItems(snapshot)
      const cur = pickCaption(state, all)
      if (cur && isChecking(cur.claim)) return captionHtml(cur, people, !state.replay && status.vivo && !snapshot.encerrado)
      const last = lastVerified(all, state.replay ? (state.replaySec || 0) * 1000 : Infinity)
      return last ? verifiedCaptionHtml(last, people, snapshot, !!state.replay) : captionHtml(null, people, false)
    })()}
    ${mobileFeed(items, people, state.filter, state.fresh, claimsOf(snapshot))}
    ${panelHtml(state, items)}`
}

function boot() {
  const app = document.getElementById('app')
  if (!app) return
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const baseDefault = window.PLACAR_BASE || ''
  const startMode = window.PLACAR_MODE === 'demo' ? 'demo' : 'live'
  const state = {
    mode: 'demo',
    snapshot: null,
    filter: {},
    panel: null,
    detailKey: '',
    quiet: false,
    fresh: new Set(),
    seen: new Set(),
    primed: false,
    now: Date.now(),
    pageUrl: location.href.split('#')[0],
    sourceLabel: '',
    banner: '',
    fallbackNote: '',
    archive: '',
    videoOverride: window.PLACAR_VIDEO || '',
  }
  let feed = null

  function paint() {
    if (!state.snapshot) return
    state.now = Date.now()
    state.pageUrl = location.href.split('#')[0]
    const previous = app.querySelector('.stage')
    const nextId = resolveVideoId(state.snapshot, state.videoOverride || '')
    const sameStage = previous && (previous.getAttribute('data-vid') || '') === nextId
    app.className = `app${state.quiet ? ' quiet' : ''}${state.replay ? ' replay' : ''}`
    const scrolls = [...app.querySelectorAll('.col-c')].map((node) => [node.className, node.querySelector('.colbody')?.scrollTop || 0])
    app.innerHTML = renderBoard(state)
    for (const [cls, top] of scrolls) {
      const body = [...app.querySelectorAll('.col-c')].find((node) => node.className === cls)?.querySelector('.colbody')
      if (body && top) body.scrollTop = top
    }
    if (sameStage && !state.replay) {
      const slot = app.querySelector('.stage')
      if (slot) slot.replaceWith(previous)
    }
    if (!reduce) {
      app.querySelectorAll('.fresh').forEach((node) => node.classList.add('run'))
    }
  }

  function show(snapshot, mode) {
    const keys = new Set(feedItems(snapshot).map((item) => item.key))
    const fresh = new Set()
    if (state.primed) {
      for (const key of keys) if (!state.seen.has(key)) fresh.add(key)
    } else {
      const newest = [...feedItems(snapshot)].sort((a, b) => b.t - a.t)[0]
      if (newest) fresh.add(newest.key)
      state.primed = true
    }
    state.seen = keys
    state.fresh = fresh
    state.snapshot = snapshot
    state.mode = mode
    paint()
  }

  function load(next, { fallback = false } = {}) {
    feed?.stop()
    state.archive = next.archive || ''
    state.sourceLabel = next.url.replace(/[?&]t=\d+$/, '')
    feed = createFeed({
      urlFor: (now) => (next.mode === 'demo'
        ? feedUrl({ demo: true, archive: next.archive, now })
        : feedUrl({ base: next.base, archive: next.archive, now })),
      fetchImpl: (url) => {
        const controller = new AbortController()
        const timer = setTimeout(() => controller.abort(), 8000)
        return fetch(url, { signal: controller.signal, cache: 'no-store' }).finally(() => clearTimeout(timer))
      },
      isHidden: () => document.hidden,
      onData: (data) => {
        if (next.mode === 'demo') {
          state.banner = state.fallbackNote || ''
        } else {
          state.fallbackNote = ''
          state.banner = ''
        }
        show(data, next.mode)
      },
      onError: () => {
        if (!state.snapshot || state.mode !== next.mode) {
          if (fallback && next.mode === 'live') {
            state.fallbackNote = 'Sem conexão com o placar. Mostrando a simulação com fatos fictícios.'
            const archive = next.archive ? `&d=${encodeURIComponent(next.archive)}` : ''
            load(resolveFeed(`?demo=1${archive}`, '', Date.now()), { fallback: false })
            return
          }
          state.banner = 'Sem conexão com o placar. Tentando de novo…'
          if (state.snapshot) paint()
          return
        }
        state.banner = 'Sem conexão com o placar. Tentando de novo…'
        paint()
      },
    })
    feed.start()
  }

  function toggleFullscreen() {
    const root = document.documentElement
    const fsEl = document.fullscreenElement || document.webkitFullscreenElement
    if (fsEl) { (document.exitFullscreen || document.webkitExitFullscreen).call(document); return }
    if (root.classList.contains('pseudo-fs')) { root.classList.remove('pseudo-fs'); state.fs = false; paint(); return }
    const req = root.requestFullscreen || root.webkitRequestFullscreen
    if (req) {
      try { const r = req.call(root); if (r && r.catch) r.catch(() => { root.classList.add('pseudo-fs'); state.fs = true; paint() }) } catch { root.classList.add('pseudo-fs'); state.fs = true; paint() }
    } else { root.classList.add('pseudo-fs'); state.fs = true; paint() }
  }
  const onFs = () => { state.fs = !!(document.fullscreenElement || document.webkitFullscreenElement) || document.documentElement.classList.contains('pseudo-fs'); paint() }
  document.addEventListener('fullscreenchange', onFs)
  document.addEventListener('webkitfullscreenchange', onFs)

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) feed?.pause()
    else feed?.resume()
  })

  document.addEventListener('click', (event) => {
    const node = event.target.closest('[data-act]')
    if (!node || !state.snapshot) return
    const act = node.dataset.act
    const arg = node.dataset.arg || ''
    if (act === 'close' && event.target.closest('.sheet') && !event.target.closest('.x')) return
    if (act === 'close') {
      state.panel = null
      paint()
      return
    }
    if (act === 'panel') {
      state.panel = arg
      paint()
      return
    }
    if (act === 'rseek' && window.__replay) {
      window.__replay.seek(Math.max(0, window.__replay.now() + Number(arg)))
      return
    }
    if (act === 'overlays') {
      state.quiet = !state.quiet
      paint()
      return
    }
    if (act === 'item') {
      state.detailKey = arg
      state.panel = 'detalhe'
      paint()
      return
    }
    if (act === 'fs') {
      toggleFullscreen()
      return
    }
    if (act === 'ctab') {
      const cut = arg.lastIndexOf(':')
      colTabs.set(arg.slice(0, cut), arg.slice(cut + 1))
      paint()
      return
    }
    if (act === 'quem') {
      state.filter = { ...state.filter, quem: arg || undefined }
      paint()
      return
    }
    if (act === 'verdict') {
      state.filter = { ...state.filter, verdict: state.filter.verdict === arg ? undefined : arg }
      paint()
      return
    }
    if (act === 'window') {
      if (arg === 'clear') {
        delete state.filter.windowStartMs
        delete state.filter.windowEndMs
      } else {
        const [start, end] = arg.split(':').map(Number)
        if (state.filter.windowStartMs === start) {
          delete state.filter.windowStartMs
          delete state.filter.windowEndMs
        } else {
          state.filter.windowStartMs = start
          state.filter.windowEndMs = end
        }
      }
      paint()
      return
    }
    if (act === 'hoje') {
      const kept = new URLSearchParams(location.search)
      kept.delete('d')
      const search = kept.toString()
      location.search = search ? `?${search}` : ''
    }
    if (act === 'source') {
      const kept = new URLSearchParams(location.search)
      kept.delete('demo')
      kept.delete('live')
      kept.delete('src')
      kept.set(arg === 'live' ? 'live' : 'demo', '1')
      location.search = `?${kept.toString()}`
    }
  })

  document.addEventListener('submit', (event) => {
    const form = event.target
    if (!(form instanceof HTMLFormElement) || form.dataset.act !== 'archive') return
    event.preventDefault()
    const value = new FormData(form).get('d')
    const date = String(value || '').trim()
    if (!/^[\w-]{1,40}$/.test(date)) return
    const kept = new URLSearchParams(location.search)
    kept.set('d', date)
    location.search = `?${kept.toString()}`
  })

  document.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      if (!state.snapshot) return
      state.panel = state.panel === 'cmd' ? null : 'cmd'
      paint()
    } else if (event.key === 'Escape' && state.panel) {
      state.panel = null
      paint()
    }
  })

  const query = new URLSearchParams(location.search)
  if (query.get('replay')) {
    startReplay(query)
  } else {
    load(resolveFeed(location.search, baseDefault, Date.now(), startMode), { fallback: true })
  }

  function startReplay(q) {
    const vid = youtubeId(q.get('replay'))
    let src = (q.get('src') || './teste/').trim()
    if (!src.endsWith('.json')) src = `${src.replace(/\/?$/, '/')}replay.json`
    const simulated = q.get('replay_clock') === '1'
    const rate = Number(q.get('rate') || 1) || 1
    state.videoOverride = vid
    fetch(src, { cache: 'no-store' }).then((r) => {
      if (!r.ok) throw new Error(String(r.status))
      return r.json()
    }).then((data) => {
      state.replay = data
      const startAt = Number(q.get('t') || data.replay?.inicio || 0)
      let player = null
      let ready = false
      const sim = replayClock({ start: startAt, rate })
      let failed = false
      let hold = startAt // posição enquanto o player não começou a tocar
      const current = () => {
        if (simulated || failed) return sim.get()
        if (!ready || !player?.getCurrentTime) return hold
        // Só lê o player. Buffering (3), pausa (2) e fim (0) não são falha.
        const t = Number(player.getCurrentTime()) || 0
        const st = player.getPlayerState?.()
        if ((st === -1 || st === 5) && t === 0) return hold // ainda não carregou o início pedido
        return t
      }
      let sig = ''
      const tick = () => {
        const sec = current()
        state.replaySec = sec
        const next = signatureAt(data, sec)
        const timeNode = app.querySelector('.rtime')
        if (timeNode) timeNode.textContent = mmss(sec)
        document.documentElement.dataset.replaySec = String(Math.floor(sec))
        if (next === sig) return
        sig = next
        if (simulated) state.banner = 'Replay com relógio simulado (sem player).'
        show(snapshotAt(data, sec), 'live')
      }
      state.banner = 'Replay: os fatos aparecem no momento em que foram ditos.'
      show(snapshotAt(data, startAt), 'live')
      window.__replay = {
        seek: (sec) => { sim.seek(sec); hold = sec; if (ready && !failed && player?.seekTo) player.seekTo(sec, true); tick() },
        mode: () => (simulated || failed ? 'clock' : (ready ? 'player' : 'loading')),
        now: current,
        player: () => player,
        frame: () => document.getElementById('ytreplay'),
        data,
      }
      setInterval(tick, 250)
      if (!simulated) {
        const make = () => {
          if (player) return
          let wrap = document.getElementById('rhost')
          if (!wrap) {
            wrap = document.createElement('div')
            wrap.id = 'rhost'
            wrap.innerHTML = '<div id="ytreplay"></div>'
            app.parentNode.insertBefore(wrap, app)
          }
          const host = document.getElementById('ytreplay')
          if (!host) return
          player = new window.YT.Player(host, {
            videoId: vid || data.replay?.video,
            playerVars: { start: Math.floor(startAt), rel: 0, playsinline: 1, fs: 0 },
            events: {
              onReady: () => { ready = true },
              onError: (event) => {
                // Só erro real de vídeo indisponível/proibido no embed; nada de recriar o player.
                if (![2, 5, 100, 101, 150, 153].includes(Number(event?.data))) return
                // vídeo bloqueado/indisponível neste navegador: segue no relógio simulado
                failed = true
                sim.seek(current() || hold)
                state.banner = 'O vídeo não abriu aqui. Replay seguindo no relógio simulado.'
                sig = ''
              },
            },
          })
        }
        if (window.YT?.Player) make()
        else {
          window.onYouTubeIframeAPIReady = make
          const tagEl = document.createElement('script')
          tagEl.src = 'https://www.youtube.com/iframe_api'
          document.head.appendChild(tagEl)
        }
      }
    }).catch(() => {
      state.banner = 'Não deu para abrir os dados do replay.'
      load(resolveFeed('?demo=1', '', Date.now()), { fallback: false })
    })
  }
}

if (typeof document !== 'undefined' && document.getElementById?.('app')) boot()
