/** Ganchos de render. A pele provisória só mostra os dados; o visual entra depois. */

const VERDICT_LABEL = {
  verdadeiro: 'Verdadeiro',
  impreciso: 'Impreciso',
  falso: 'Falso',
  sem_dados: 'Sem dados',
  em_revisao: 'Em revisão',
}

export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]))
}

export function mount(root, hooks = {}) {
  const state = {
    tab: 'feed',
    filter: {},
    snapshot: null,
    status: 'Conectando…',
  }

  function paint() {
    if (!state.snapshot) {
      root.innerHTML = `<p class="status">${escapeHtml(state.status)}</p>`
      return
    }
    const view = hooks.buildView(state.snapshot, state.filter)
    hooks.onSnapshot?.(view)
    if (view.reading) hooks.onScore?.(view.reading)
    hooks.onFeed?.(view.visible)
    const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    root.classList.toggle('reduce-motion', Boolean(reduced))
    root.innerHTML = skeleton(view, state)
    bind(root, state, paint)
  }

  return {
    setSnapshot(snapshot) {
      state.snapshot = snapshot
      state.status = 'Atualizado'
      paint()
    },
    setStatus(text) {
      state.status = text
      if (!state.snapshot) paint()
    },
    paint,
  }
}

function skeleton(view, state) {
  const video = view.snapshot.video?.id
  const reading = view.reading
  const names = view.candidates.map((item) => item.nome).join(' · ')
  return `
    <p class="banner">Visual provisório. Os dados e a conta já funcionam; o desenho entra quando a opção visual for escolhida.</p>
    <header><h1>Placar da Verdade</h1><p>${escapeHtml(names)}</p><p class="status">${escapeHtml(state.status)}</p></header>
    <section class="stage" data-hook="stage">
      <div class="video" data-hook="video">
        ${video
          ? `<iframe title="Debate ao vivo" src="https://www.youtube-nocookie.com/embed/${escapeHtml(video)}" allow="autoplay; encrypted-media" allowfullscreen></iframe>`
          : `<p>${escapeHtml(view.snapshot.aviso || 'Sem vídeo neste placar.')}</p>`}
      </div>
      <aside data-hook="gauge">
        <h2>Mentirômetro</h2>
        ${reading ? `<p class="angle" data-angle="${reading.angle}">${escapeHtml(reading.headline)}</p><p>${escapeHtml(reading.detail)}</p><p>${escapeHtml(reading.basis)}</p><p>${reading.left.erroPct}% · ${reading.right.erroPct}%</p>` : '<p>Aguardando os dois candidatos.</p>'}
      </aside>
    </section>
    <nav>
      ${tabButton('feed', 'Ao vivo', state.tab)}
      ${tabButton('linha', 'Linha do tempo', state.tab)}
      ${tabButton('propostas', 'Propostas', state.tab)}
      ${tabButton('leitura', 'Como ler', state.tab)}
    </nav>
    <section data-hook="panel">${panel(view, state)}</section>
  `
}

function tabButton(id, label, current) {
  return `<button type="button" data-tab="${id}" aria-pressed="${current === id}">${label}</button>`
}

function panel(view, state) {
  if (state.tab === 'linha') {
    if (!view.timeline.length) return '<p>A linha do tempo ainda está vazia.</p>'
    return view.timeline.map((column) => {
      const bits = view.candidates.map((candidate) => {
        const cell = column.by[candidate.id]
        return `${escapeHtml(candidate.nome)}: ${cell.attacks} ataques, ${cell.proposals} propostas`
      }).join(' · ')
      return `<button type="button" data-window="${column.startMs}:${column.endMs}">${bits}</button>`
    }).join('')
  }
  if (state.tab === 'propostas') {
    if (!view.propostas.length) return '<p>Nenhuma proposta concreta até agora.</p>'
    return `<ul>${view.propostas.map((item) => `<li><strong>${escapeHtml(item.titulo)}</strong> ${escapeHtml(item.explicacao)} ${item.vezes > 1 ? `<small>Citada ${item.vezes} vezes</small>` : ''}</li>`).join('')}</ul>`
  }
  if (state.tab === 'leitura') {
    return `<article>
      <h2>Como ler</h2>
      <p>Verdadeiro: os dados confirmam. Impreciso: exagerado ou fora de contexto. Falso: os dados contradizem. Sem dados: não deu para verificar. Em revisão: o áudio não confirmou a frase; fica fora do placar até a conferência.</p>
      <p>O Mentirômetro pende para quem teve mais afirmações falsas ou imprecisas (imprecisa conta meio ponto). "Sem dados" fica de fora.</p>
      <h2>Como funciona</h2>
      <p>O áudio do debate é transcrito a cada 10 segundos e a voz identifica quem está falando. Uma IA lê cada fala e separa as afirmações que valem checagem, as propostas concretas e os ataques ao adversário.</p>
      <p><strong>É uma checagem automática e pode errar.</strong> Confira a fonte antes de compartilhar.</p>
    </article>`
  }
  const chips = ['', '1', '2'].map((quem) => {
    const label = quem ? (view.candidates.find((item) => item.id === quem)?.nome || quem) : 'Todos'
    return `<button type="button" data-quem="${quem}" aria-pressed="${(state.filter.quem || '') === quem}">${escapeHtml(label)}</button>`
  }).join('')
  const items = view.visible.map((claim) => `
    <article class="fact" data-verdict="${escapeHtml(claim.veredito)}">
      <p><strong>${escapeHtml(VERDICT_LABEL[claim.veredito] || claim.veredito)}</strong> ${escapeHtml(nameOf(view, claim.quem))}</p>
      <p>${escapeHtml(claim.afirmacao)}</p>
      ${claim.motivo ? `<p>${escapeHtml(claim.motivo)}</p>` : ''}
      ${claim.fonte?.url ? `<p><a href="${escapeHtml(claim.fonte.url)}">${escapeHtml(claim.fonte.titulo || claim.fonte.url)}</a></p>` : ''}
    </article>`).join('')
  return `${chips}${items || '<p>Nenhum fato neste filtro.</p>'}`
}

function nameOf(view, id) {
  return view.candidates.find((item) => item.id === id)?.nome || id
}

function bind(root, state, paint) {
  root.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      state.tab = button.dataset.tab
      paint()
    })
  })
  root.querySelectorAll('[data-quem]').forEach((button) => {
    button.addEventListener('click', () => {
      state.filter = { ...state.filter, quem: button.dataset.quem || undefined }
      paint()
    })
  })
  root.querySelectorAll('[data-window]').forEach((button) => {
    button.addEventListener('click', () => {
      const [start, end] = button.dataset.window.split(':').map(Number)
      const same = state.filter.windowStartMs === start
      state.filter = same
        ? { ...state.filter, windowStartMs: undefined, windowEndMs: undefined }
        : { ...state.filter, windowStartMs: start, windowEndMs: end }
      state.tab = 'feed'
      paint()
    })
  })
}
