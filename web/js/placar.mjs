/** Placar da Verdade: conta, polling e a página. Sem build. */

export const MINIMO = 3

const VERDICT_LABEL = {
  verdadeiro: 'Verdadeiro',
  impreciso: 'Impreciso',
  falso: 'Falso',
  sem_dados: 'Sem dados',
  em_revisao: 'Em revisão',
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

export function resolveFeed(search, baseDefault, now) {
  const raw = search.startsWith('?') ? search.slice(1) : search
  const query = new URLSearchParams(raw)
  const archive = (query.get('d') || '').trim()
  const src = (query.get('src') || '').trim()
  const forceDemo = query.get('demo') === '1' || (!src && !baseDefault)
  if (forceDemo) return { mode: 'demo', base: '', url: feedUrl({ demo: true, archive, now }), archive }
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

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[char]))
}

function badge(verdict) {
  return `<span class="badge ${esc(verdict)}">${esc(VERDICT_LABEL[verdict] || verdict)}</span>`
}

function chip(label, pressed, act, arg, extra = '') {
  return `<button type="button" class="chip${pressed ? ' on' : ''}" aria-pressed="${pressed ? 'true' : 'false'}" data-act="${act}" data-arg="${esc(arg)}">${extra}${esc(label)}</button>`
}

function gaugeSvg(angle) {
  const cx = 150
  const cy = 138
  const r = 112
  const seg = (start, color) => {
    const sweep = Math.PI / 3
    const point = (rad) => [cx + r * Math.cos(rad), cy + r * Math.sin(rad)]
    const [x1, y1] = point(start)
    const [x2, y2] = point(start + sweep)
    return `<path d="M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${r} ${r} 0 0 1 ${x2.toFixed(1)} ${y2.toFixed(1)}" stroke="${color}" fill="none" stroke-width="22" stroke-linecap="butt"/>`
  }
  const pi = Math.PI
  return `<svg class="gauge" viewBox="0 0 300 168" aria-hidden="true">
    ${seg(pi, '#C62828')}${seg(pi + pi / 3, '#B9BDB8')}${seg(pi + 2 * pi / 3, '#C62828')}
    <g class="needle" style="--ang: ${Number(angle) || 0}deg">
      <line x1="150" y1="138" x2="150" y2="36" stroke="#1B1D1C" stroke-width="4" stroke-linecap="round"/>
      <circle cx="150" cy="138" r="7" fill="#1B1D1C"/>
    </g>
  </svg>`
}

function splitBar(index, reversed) {
  const parts = [
    ['v', index.verdadeiroPct],
    ['i', index.imprecisoPct],
    ['f', index.falsoPct],
  ].filter(([, pct]) => pct > 0)
  const ordered = reversed ? parts.reverse() : parts
  if (!ordered.length) return '<div class="bar"></div>'
  return `<div class="bar" role="img" aria-label="${index.verdadeiroPct}% verdadeiro, ${index.imprecisoPct}% impreciso, ${index.falsoPct}% falso">${ordered.map(([cls, pct]) => `<i class="${cls}" style="width:${pct}%"></i>`).join('')}</div>`
}

function meter(candidate, index, side) {
  const shown = index.total === 0 ? '–' : String(index.erroPct)
  return `<div class="${side}">
    <h3>${esc(candidate.nome)}</h3>
    <div class="erro">${esc(shown)}${index.total ? '<small>% de erro</small>' : ''}</div>
    ${splitBar(index, side === 'right')}
    <p class="muted small">${candidate.verdadeiro} verdadeiro · ${candidate.impreciso} impreciso · ${candidate.falso} falso</p>
    <p class="muted small">${candidate.sem_dados || 0} sem dados</p>
  </div>`
}

function stageHtml(state) {
  const snapshot = state.snapshot
  const ended = snapshot.encerrado
  const videoId = youtubeId(snapshot.video?.id)
  const demo = state.mode === 'demo' || snapshot.simulado
  if (state.embed && videoId) {
    const src = `https://www.youtube-nocookie.com/embed/${videoId}?rel=0`
    return `<section class="card stage" aria-label="Transmissão">
      <iframe class="frame" title="Transmissão do debate no YouTube" src="${src}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
      <button type="button" class="ghost" data-act="close-embed">Fechar o vídeo</button>
    </section>`
  }
  const status = statusCopy(snapshot, state.now, state.mode)
  const pos = positionLabel(snapshot, state.now, state.mode)
  let body
  if (ended) {
    const when = Date.parse(ended.proximo || '')
    const videoDate = snapshot.video?.data ? Date.parse(snapshot.video.data) : NaN
    const day = Number.isNaN(videoDate) ? dataCurta(snapshot.atualizado) : dataCurta(videoDate)
    const count = Number.isNaN(when) ? '' : faltaPara(when, state.now)
    body = `<p class="muted">Debate de ${esc(day)} encerrado · o placar final está logo abaixo</p>
      <p class="muted small">Próximo debate</p>
      <h2>${esc(ended.texto || '')}</h2>
      <p class="dur" data-clock="count">${esc(count)}</p>
      <p class="muted small">Estamos aprimorando os métodos de checagem para o próximo debate.</p>`
  } else {
    const title = demo ? 'Debate simulado' : (snapshot.aviso || 'Transmissão')
    const note = demo
      ? 'Sem sinal de vídeo nesta simulação. Os números ao lado são ilustrativos.'
      : 'A live abre no YouTube quando o placar publica um vídeo.'
    body = `<h2>${esc(title)}</h2>
      <p class="dur" data-clock="pos">${esc(pos)}</p>
      <p class="muted small">${esc(videoId ? 'O vídeo só carrega quando você pede.' : note)}</p>
      ${videoId ? '<button type="button" class="btn" data-act="embed">▶ Ver a live</button>' : ''}`
  }
  return `<section class="card stage" aria-label="Transmissão">${body}</section>`
}

function visorHtml(snapshot) {
  const candidates = candidatesOf(snapshot)
  if (candidates.length < 2) {
    return `<section class="card visor"><h2>Mentirômetro</h2><p class="muted">Aguardando os dois candidatos.</p></section>`
  }
  const [left, right] = candidates
  const reading = mentiromentro(left.nome, right.nome, left, right)
  const label = `Mentirômetro: ${left.nome} ${reading.left.erroPct}% de erro, ${right.nome} ${reading.right.erroPct}%`
  return `<section class="card visor" role="img" aria-label="${esc(label)}">
    <h2>Mentirômetro</h2>
    ${gaugeSvg(reading.angle)}
    <div class="names"><span>${esc(left.nome)}</span><span>${esc(right.nome)}</span></div>
    <p class="headline">${esc(reading.headline)}</p>
    <p class="muted small">${esc(reading.detail)}</p>
    <p class="muted small">${esc(reading.basis)}</p>
    <div class="meters">${meter(left, reading.left, 'left')}${meter(right, reading.right, 'right')}</div>
  </section>`
}

function toneHtml(snapshot) {
  const cards = candidatesOf(snapshot).map((candidate) => {
    const shares = speakingShares(candidate.tempo)
    const attacks = (snapshot.ataques || []).filter((attack) => attack.quem === candidate.id).slice(0, 3)
    const bar = shares.filter((share) => share.seconds > 0).map((share) => `<i class="${share.cls}" style="flex:${Math.max(1, Math.round(share.seconds * 10))}"></i>`).join('')
    return `<div>
      <h3>${esc(candidate.nome)}</h3>
      <div class="counts">
        <div><div class="count p">${candidate.propostas || 0}</div><div class="muted small">propostas</div></div>
        <div><div class="count a">${candidate.ataques || 0}</div><div class="muted small">ataques</div></div>
      </div>
      <div class="tonebar">${bar}</div>
      <div class="legend">${shares.map((share) => `<span><i class="swatch ${share.cls}"></i>${share.percent}% ${esc(share.label)}</span>`).join('')}</div>
      ${attacks.map((attack) => `<p class="muted small">${esc(attack.resumo)}</p>`).join('')}
    </div>`
  }).join('')
  return `<section class="card">
    <h2>Propostas ou ataques?</h2>
    <p class="muted">Quantas vezes cada um apresentou uma proposta concreta e quantas vezes atacou o adversário. A barra mostra como cada um usou o tempo de fala.</p>
    <div class="pair">${cards}</div>
    <button type="button" class="linkish" data-act="proposals">Ver as propostas explicadas</button>
  </section>`
}

function timelineHtml(snapshot, filter) {
  const timeline = timelineOf(snapshot)
  let chart = '<p class="muted">A linha do tempo começa no primeiro ataque ou proposta.</p>'
  if (timeline.rows.length) {
    const columns = timeline.rows[0].columns
    const names = timeline.rows.map((row) => `<div class="who">${esc(row.name)}</div>`).join('')
    const bars = timeline.rows.map((row) => {
      const cols = row.columns.map((column) => {
        const active = filter.windowStartMs === column.startMs
        const inner = 70 - (column.attacks && column.proposals ? 2 : 0)
        const attackH = column.attacks ? Math.max(2, (column.attacks / timeline.maxStack) * inner) : 0
        const proposalH = column.proposals ? Math.max(2, (column.proposals / timeline.maxStack) * inner) : 0
        const label = `${row.name}, ${hhmm(column.startMs)}–${hhmm(column.endMs)}: ${column.attacks} ataques, ${column.proposals} propostas. Toque para ver os fatos desses minutos`
        return `<button type="button" class="col${active ? ' on' : ''}" data-act="window" data-arg="${column.startMs}:${column.endMs}" aria-pressed="${active ? 'true' : 'false'}" aria-label="${esc(label)}">${column.attacks ? `<i class="a" style="height:${attackH.toFixed(1)}px"></i>` : ''}${column.proposals ? `<i class="p" style="height:${proposalH.toFixed(1)}px"></i>` : ''}</button>`
      }).join('')
      return `<div class="cols">${cols}</div>`
    }).join('')
    const hours = columns.map((column, index) => `<span>${index % timeline.labelStep === 0 ? hhmm(column.startMs) : ''}</span>`).join('')
    chart = `<div class="chart"><div>${names}</div><div class="scroll">${bars}<div class="hours">${hours}</div></div></div>`
  }
  return `<section class="card">
    <h2>Linha do tempo</h2>
    <p class="muted">Quando cada um atacou e quando apresentou propostas, a cada 5 minutos de debate. Toque numa coluna para ver os fatos checados daqueles minutos.</p>
    <p class="legend"><span><i class="swatch a"></i>Ataques</span><span><i class="swatch p"></i>Propostas</span></p>
    ${chart}
  </section>`
}

function factCard(snapshot, claim, state) {
  const nome = candidatesOf(snapshot).find((candidate) => candidate.id === claim.quem)?.nome || ''
  const key = claimKey(claim)
  const open = state.open?.has(key)
  const fresh = state.fresh?.has(key) ? ' fresh' : ''
  const fonte = claim.fonte
  const href = fonte ? safeHttpUrl(fonte.url) : ''
  const fonteHtml = !fonte
    ? '<p class="muted small">Nenhuma fonte encontrada.</p>'
    : `<p class="small">Fonte: ${href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">${esc(fonte.titulo)} (${esc(new URL(href).host.replace(/^www\./, ''))})</a>` : esc(fonte.titulo)}</p>`
  const corrigido = claim.corrigido
    ? `<p class="muted small">✎ Revisado após o debate · ao vivo era ${esc(VERDICT_LABEL[claim.corrigido.antes] || claim.corrigido.antes)}</p>`
    : ''
  return `<article class="fact ${esc(claim.veredito)}${fresh}" id="fato-${esc(key)}">
    <div class="meta">${badge(claim.veredito)}<strong>${esc(nome)}</strong><span class="muted small">${hhmm(claim.t)} · ${esc(claim.tema)}</span></div>
    <p>${esc(claim.afirmacao)}</p>
    <details ${open ? 'open' : ''} data-key="${esc(key)}">
      <summary>${open ? 'Ocultar dados e fonte' : 'Ver dados e fonte'}</summary>
      ${claim.literal ? `<p class="quote muted">Frase dita: “${esc(claim.literal)}”</p>` : ''}
      ${claim.contexto ? `<p class="muted small">${esc(claim.contexto)}</p>` : ''}
      ${claim.motivo ? `<p><strong>Os dados: </strong>${esc(claim.motivo)}</p>` : ''}
      ${corrigido}
      ${fonteHtml}
    </details>
    <button type="button" class="ghost" data-act="share-fact" data-arg="${esc(key)}">↗ Compartilhar</button>
  </article>`
}

function factsHtml(state) {
  const snapshot = state.snapshot
  const claims = claimsOf(snapshot)
  const filter = state.filter || {}
  const order = effectiveOrder(snapshot, filter.order)
  const visible = sortClaims(filterClaims(claims, filter), order)
  const byPerson = filterClaims(claims, filter, 'quem')
  const byVerdict = filterClaims(claims, filter, 'vered')
  const count = (verdict) => byVerdict.filter((claim) => claim.veredito === verdict).length
  const corrected = byVerdict.filter((claim) => claim.corrigido).length
  const showCorrected = claims.some((claim) => claim.corrigido)
  const totalLabel = visible.length === claims.length ? `(${claims.length})` : `(${visible.length} de ${claims.length})`
  const people = [chip(`Todos ${byPerson.length}`, !filter.quem, 'quem', '')]
  for (const candidate of candidatesOf(snapshot)) {
    const n = byPerson.filter((claim) => claim.quem === candidate.id).length
    people.push(chip(`${candidate.nome} ${n}`, filter.quem === candidate.id, 'quem', candidate.id))
  }
  const verdicts = ['verdadeiro', 'impreciso', 'falso', 'sem_dados', 'em_revisao']
    .filter((verdict) => verdict !== 'em_revisao' || count(verdict) > 0)
    .map((verdict) => {
      const pressed = filter.verdict === verdict && !filter.onlyCorrected
      const dot = verdict === 'sem_dados'
        ? '<i class="box"></i>'
        : verdict === 'em_revisao'
          ? ''
          : `<i class="dotv ${verdict}"></i>`
      return chip(`${VERDICT_LABEL[verdict]} ${count(verdict)}`, pressed, 'verdict', verdict, dot)
    })
  if (showCorrected) verdicts.push(chip(`✎ Corrigidos ${corrected}`, Boolean(filter.onlyCorrected), 'corrected', ''))
  const windowChip = filter.windowStartMs != null
    ? chip(`${hhmm(filter.windowStartMs)}–${hhmm(filter.windowEndMs)} ✕`, true, 'window', 'clear')
    : ''
  const orderLabel = order === 'recentes' ? '↓ Mais recentes primeiro' : '↓ Na ordem do debate'
  const cards = visible.length
    ? `<div class="facts">${visible.map((claim) => factCard(snapshot, claim, state)).join('')}</div>`
    : `<div class="card"><p class="muted">${claims.length ? 'Nenhum fato com esses filtros.' : 'Os fatos aparecem aqui quando um candidato citar um dado que dá para checar.'}</p></div>`
  return `<section id="fatos">
    <h2>Fatos checados <span class="muted small">${totalLabel}</span></h2>
    <div class="chips">${people.join('')}</div>
    <div class="chips">${verdicts.join('')}</div>
    <div class="chips">${windowChip}${chip(orderLabel, false, 'order', order)}</div>
    ${cards}
  </section>`
}

function highlightsHtml(snapshot) {
  const claims = sortClaims(claimsOf(snapshot).filter((claim) => claim.veredito === 'falso' || claim.veredito === 'impreciso'), 'recentes').slice(0, 6)
  if (!claims.length) return ''
  const cards = claims.map((claim) => {
    const nome = candidatesOf(snapshot).find((candidate) => candidate.id === claim.quem)?.nome || ''
    return `<button type="button" class="${esc(claim.veredito)}" data-act="jump" data-arg="${esc(claimKey(claim))}">${badge(claim.veredito)}<p><strong>${esc(nome)}</strong> ${esc(claim.afirmacao)}</p></button>`
  }).join('')
  return `<section><h3>Destaques: últimos falsos e imprecisos</h3><div class="hl">${cards}</div></section>`
}

function revisionHtml(snapshot) {
  const revision = snapshot.revisao
  if (!revision?.por || !revision?.resumo) return ''
  const changes = revision.mudancas || []
  const changed = changes.filter((change) => change.depois && change.depois !== change.antes).length
  const removed = changes.filter((change) => !change.depois).length
  const candidates = candidatesOf(snapshot)
  const erro = (bag, id) => {
    const counts = bag?.[id]
    if (!counts) return '–'
    const index = errorIndex(counts)
    return index.total ? `${index.erroPct}%` : '–'
  }
  const compare = candidates.slice(0, 2).map((candidate) => `${esc(candidate.nome)} ${erro(revision.antes, candidate.id)} → ${erro(revision.depois, candidate.id)}`).join(' · ')
  return `<section class="card rev"><p><strong>✎ Dados revisados e corrigidos pelo ${esc(revision.por)} após o debate. </strong>${changed} vereditos corrigidos · ${removed} checagens removidas · erro ao vivo → revisado: ${compare}</p><p>${esc(revision.resumo)}</p></section>`
}

function infoHtml(state) {
  const page = state.pageUrl || ''
  const text = sharePlacar(state.snapshot, state.mode, page)
  const fonte = state.mode === 'demo' || state.snapshot.simulado
    ? 'Você está na simulação local. O texto acima descreve o placar publicado.'
    : `Fonte dos dados: ${esc(state.sourceLabel || '')}`
  return `<div class="info">
    <section class="card how">
      <h3>Como ler</h3>
      <div class="rowline">${badge('verdadeiro')}<span>os dados confirmam</span></div>
      <div class="rowline">${badge('impreciso')}<span>exagerado ou fora de contexto</span></div>
      <div class="rowline">${badge('falso')}<span>os dados contradizem</span></div>
      <div class="rowline">${badge('sem_dados')}<span>não deu para verificar</span></div>
      <div class="rowline">${badge('em_revisao')}<span>o áudio não confirmou a frase; fica fora do placar até a conferência</span></div>
      <p>O Mentirômetro pende para quem teve mais afirmações falsas ou imprecisas (imprecisa conta meio ponto). "Sem dados" fica de fora.</p>
    </section>
    <section class="card how">
      <h3>Como funciona</h3>
      <p>O áudio do debate é transcrito a cada 10 segundos e a voz identifica quem está falando. Uma IA lê cada fala e separa as afirmações que valem checagem (números, dados, atos de governo), as propostas concretas e os ataques ao adversário. Retórica e opinião não viram checagem.</p>
      <p>Cada afirmação é buscada na web (agências de checagem, imprensa e dados oficiais) e julgada com as mesmas regras para os dois candidatos.</p>
      <p>Antes de publicar um "falso" ou "impreciso", o trecho é ouvido de novo por outros modelos para confirmar a frase exata. Se o áudio não confirmar, o fato fica "em revisão" e não conta no placar.</p>
      <p><strong>É uma checagem automática e pode errar. </strong>Confira a fonte antes de compartilhar.</p>
      <p class="muted small">${fonte}</p>
    </section>
    <section class="card">
      <h3>Mostre o placar</h3>
      <div class="actions">
        <a class="btn" href="${esc(xUrl(text))}" target="_blank" rel="noopener noreferrer">Postar no X</a>
        <a class="btn" href="${esc(whatsAppUrl(text))}" target="_blank" rel="noopener noreferrer">Enviar no WhatsApp</a>
      </div>
    </section>
  </div>`
}

function proposalsHtml(snapshot) {
  const columns = candidatesOf(snapshot).map((candidate) => {
    const mine = (snapshot.propostas || [])
      .filter((proposal) => proposal.quem === candidate.id)
      .slice()
      .sort((a, b) => (b.vezes - a.vezes) || (b.t - a.t))
    const cards = mine.length
      ? mine.map((proposal) => `<article class="card prop"><h3>${esc(proposal.titulo)}</h3><p>${esc(proposal.explicacao)}</p>${proposal.vezes > 1 ? `<p class="muted small">Citada ${proposal.vezes} vezes</p>` : ''}</article>`).join('')
      : '<div class="card"><p class="muted">Nenhuma proposta concreta até agora.</p></div>'
    return `<div><h3>${esc(candidate.nome)}</h3>${cards}</div>`
  }).join('')
  return `<section>
    <button type="button" class="back" data-act="placar">← Voltar ao placar</button>
    <h2>Propostas explicadas</h2>
    <p class="muted">O que cada candidato propôs de concreto, da proposta mais repetida para a mais recente.</p>
    <div class="pair">${columns}</div>
  </section>`
}

function xUrl(text) {
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`
}

function whatsAppUrl(text) {
  return `https://wa.me/?text=${encodeURIComponent(text)}`
}

export function renderBoard(state) {
  if (state.view === 'propostas') return proposalsHtml(state.snapshot)
  const audience = state.snapshot.audiencia
  const visits = state.snapshot.visitas
  const crowd = audience == null ? '' : `<p class="muted small">${formatPt(audience)} ${audience === 1 ? 'pessoa assistindo' : 'pessoas assistindo'} agora${visits == null ? '' : ` · ${formatPt(visits)} visitas`}</p>`
  return `<div class="stack">${crowd}
    <div class="top">${stageHtml(state)}${visorHtml(state.snapshot)}</div>
    ${revisionHtml(state.snapshot)}
    ${highlightsHtml(state.snapshot)}
    ${toneHtml(state.snapshot)}
    ${timelineHtml(state.snapshot, state.filter || {})}
    ${factsHtml(state)}
    ${infoHtml(state)}</div>`
}

export function modeSwitch(mode) {
  return `<div class="modes" role="group" aria-label="Fonte do placar">
    <button type="button" data-act="demo" aria-pressed="${mode === 'demo' ? 'true' : 'false'}">Simulação</button>
    <button type="button" data-act="live" aria-pressed="${mode === 'live' ? 'true' : 'false'}">Ao vivo</button>
  </div>`
}

export function statusLine(snapshot, now, mode) {
  const status = statusCopy(snapshot, now, mode)
  return `<span class="dot${status.vivo ? ' on' : ''}"></span><span>${esc(status.texto)}</span>`
}

function boot() {
  const app = document.getElementById('app')
  if (!app) return
  const modes = document.getElementById('modes')
  const status = document.getElementById('status')
  const banner = document.getElementById('banner')
  const bootNote = document.getElementById('boot')
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const baseDefault = window.PLACAR_BASE || ''
  const state = {
    mode: 'demo',
    snapshot: null,
    filter: {},
    view: location.hash === '#propostas' ? 'propostas' : 'placar',
    open: new Set(),
    fresh: new Set(),
    pending: 0,
    embed: false,
    now: Date.now(),
    pageUrl: location.href.split('#')[0],
    sourceLabel: '',
    banner: '',
    fallbackNote: '',
    seen: new Set(),
    primed: false,
    lastAngle: 0,
  }
  let feed = null
  let plan = resolveFeed(location.search, baseDefault, Date.now())

  function paint() {
    if (!state.snapshot) return
    state.now = Date.now()
    state.pageUrl = location.href.split('#')[0]
    modes.innerHTML = modeSwitch(state.mode)
    status.className = `status${statusCopy(state.snapshot, state.now, state.mode).vivo ? ' vivo' : ''}`
    status.innerHTML = statusLine(state.snapshot, state.now, state.mode)
    banner.hidden = !state.banner
    banner.textContent = state.banner || ''
    const reading = candidatesOf(state.snapshot)
    const angle = reading.length > 1 ? mentiromentro(reading[0].nome, reading[1].nome, reading[0], reading[1]).angle : 0
    app.innerHTML = renderBoard(state) + (state.pending > 0 ? `<button type="button" class="novo" data-act="jump-facts">↑ ${state.pending} ${state.pending === 1 ? 'fato novo' : 'fatos novos'}</button>` : '')
    const needle = app.querySelector('.needle')
    if (needle && !reduce) {
      needle.style.setProperty('--ang', `${state.lastAngle}deg`)
      requestAnimationFrame(() => needle.style.setProperty('--ang', `${angle}deg`))
    }
    state.lastAngle = angle
    bootNote.hidden = true
    if (!state.didHash && location.hash === '#fatos') {
      state.didHash = true
      document.getElementById('fatos')?.scrollIntoView()
    }
  }

  function noteFresh(snapshot) {
    const ids = new Set(claimsOf(snapshot).map(claimKey))
    if (!state.primed) {
      state.seen = ids
      state.primed = true
      return
    }
    const fresh = [...ids].filter((id) => !state.seen.has(id))
    state.seen = ids
    if (!fresh.length) return
    state.fresh = new Set(fresh)
    const fatos = document.getElementById('fatos')
    if (fatos && fatos.getBoundingClientRect().top < 0 && effectiveOrder(snapshot, state.filter.order) === 'recentes' && !snapshot.encerrado) {
      state.pending += fresh.length
    }
    setTimeout(() => {
      state.fresh = new Set()
      document.querySelectorAll('.fact.fresh').forEach((node) => node.classList.remove('fresh'))
    }, 2000)
  }

  function show(snapshot, mode) {
    noteFresh(snapshot)
    state.snapshot = snapshot
    state.mode = mode
    paint()
  }

  async function load(next, { fallback = false } = {}) {
    plan = next
    feed?.stop()
    state.sourceLabel = next.url.replace(/[?&]t=\d+$/, '')
    const started = createFeed({
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
          state.banner = state.fallbackNote
            || 'Simulação com fatos fictícios. Não é a checagem do debate. Toque em Ao vivo para o placar publicado.'
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
          banner.hidden = false
          banner.textContent = state.banner
          bootNote.hidden = true
          return
        }
        state.banner = 'Sem conexão com o placar. Tentando de novo…'
        banner.hidden = false
        banner.textContent = state.banner
      },
    })
    feed = started
    feed.start()
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) feed?.pause()
    else feed?.resume()
  })

  document.addEventListener('click', (event) => {
    const node = event.target.closest('[data-act]')
    if (!node || !state.snapshot) return
    const act = node.dataset.act
    const arg = node.dataset.arg || ''
    if (act === 'demo') {
      state.fallbackNote = ''
      state.primed = false
      state.filter = {}
      state.embed = false
      const archive = new URLSearchParams(location.search).get('d') || ''
      load(resolveFeed(archive ? `?demo=1&d=${encodeURIComponent(archive)}` : '?demo=1', '', Date.now()))
      return
    }
    if (act === 'live') {
      state.primed = false
      state.filter = {}
      state.embed = false
      state.banner = ''
      state.fallbackNote = ''
      const kept = new URLSearchParams(location.search)
      kept.delete('demo')
      const search = kept.toString()
      load(resolveFeed(search ? `?${search}` : '', baseDefault, Date.now()), { fallback: false })
      return
    }
    if (act === 'proposals') {
      state.view = 'propostas'
      history.replaceState(null, '', '#propostas')
      paint()
      return
    }
    if (act === 'placar') {
      state.view = 'placar'
      history.replaceState(null, '', location.pathname + location.search)
      paint()
      return
    }
    if (act === 'quem') {
      state.filter = { ...state.filter, quem: arg || undefined }
      if (!arg) delete state.filter.quem
      paint()
      return
    }
    if (act === 'verdict') {
      const same = state.filter.verdict === arg && !state.filter.onlyCorrected
      state.filter = { ...state.filter, verdict: same ? undefined : arg, onlyCorrected: false }
      paint()
      return
    }
    if (act === 'corrected') {
      state.filter = { ...state.filter, onlyCorrected: !state.filter.onlyCorrected, verdict: undefined }
      paint()
      return
    }
    if (act === 'order') {
      state.filter = { ...state.filter, order: arg === 'recentes' ? 'debate' : 'recentes' }
      paint()
      return
    }
    if (act === 'window') {
      if (arg === 'clear') {
        delete state.filter.windowStartMs
        delete state.filter.windowEndMs
      } else {
        const [start, end] = arg.split(':').map(Number)
        const same = state.filter.windowStartMs === start
        if (same) {
          delete state.filter.windowStartMs
          delete state.filter.windowEndMs
        } else {
          state.filter.windowStartMs = start
          state.filter.windowEndMs = end
          state.view = 'placar'
        }
      }
      paint()
      if (arg !== 'clear') document.getElementById('fatos')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
      return
    }
    if (act === 'jump' || act === 'jump-facts') {
      state.pending = 0
      state.view = 'placar'
      if (act === 'jump') state.open.add(arg)
      paint()
      const target = act === 'jump' ? document.getElementById(`fato-${CSS.escape(arg)}`) : document.getElementById('fatos')
      target?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
      return
    }
    if (act === 'embed') {
      state.embed = true
      paint()
      return
    }
    if (act === 'close-embed') {
      state.embed = false
      paint()
      return
    }
    if (act === 'share-fact') {
      const claim = claimsOf(state.snapshot).find((item) => claimKey(item) === arg)
      if (!claim) return
      const nome = candidatesOf(state.snapshot).find((candidate) => candidate.id === claim.quem)?.nome || ''
      const text = `${nome} disse: "${claim.afirmacao}" → ${VERDICT_LABEL[claim.veredito] || claim.veredito}. ${claim.motivo || ''}\n${state.pageUrl}`
      node.parentElement?.querySelector('.sharebox')?.remove()
      const share = document.createElement('div')
      share.className = 'card sharebox'
      share.innerHTML = `<h3>Compartilhar este fato</h3><p>${esc(claim.afirmacao)}</p><div class="actions"><a class="btn" href="${esc(whatsAppUrl(text))}">WhatsApp</a><a class="btn" href="${esc(xUrl(text))}">Postar no X</a><button type="button" class="ghost" data-act="copy">Copiar texto</button></div>`
      share.querySelector('[data-act="copy"]').addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(text)
          state.banner = 'Texto copiado'
        } catch {
          state.banner = 'Não foi possível copiar'
        }
        banner.hidden = false
        banner.textContent = state.banner
      })
      node.after(share)
    }
  })

  document.addEventListener('toggle', (event) => {
    const details = event.target
    if (!(details instanceof HTMLDetailsElement)) return
    const key = details.dataset.key
    if (!key) return
    if (details.open) state.open.add(key)
    else state.open.delete(key)
    const summary = details.querySelector('summary')
    if (summary) summary.textContent = details.open ? 'Ocultar dados e fonte' : 'Ver dados e fonte'
  }, true)

  window.addEventListener('scroll', () => {
    const fatos = document.getElementById('fatos')
    if (state.pending > 0 && fatos && fatos.getBoundingClientRect().top >= 0) {
      state.pending = 0
      document.querySelector('.novo')?.remove()
    }
  }, { passive: true })

  setInterval(() => {
    if (!state.snapshot || document.hidden) return
    state.now = Date.now()
    const line = status.querySelector('span:last-child')
    const copy = statusCopy(state.snapshot, state.now, state.mode)
    if (line) line.textContent = copy.texto
    status.className = `status${copy.vivo ? ' vivo' : ''}`
    const pos = document.querySelector('[data-clock="pos"]')
    if (pos) pos.textContent = positionLabel(state.snapshot, state.now, state.mode)
    const count = document.querySelector('[data-clock="count"]')
    if (count && state.snapshot.encerrado?.proximo) {
      const when = Date.parse(state.snapshot.encerrado.proximo)
      if (!Number.isNaN(when)) count.textContent = faltaPara(when, state.now)
    }
  }, 1000)

  load(plan, { fallback: plan.mode === 'live' })
}

if (typeof document !== 'undefined' && document.getElementById?.('app')) boot()
