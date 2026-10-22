// Replay sincronizado com o vídeo: mostra só o que já tinha sido dito no segundo atual.
// Dados: replay.json do pipeline (placar + `vs` por item + `linhas` da transcrição).

const VERDICTS = ['verdadeiro', 'impreciso', 'falso', 'sem_dados']

export function itemSecond(item, data) {
  if (typeof item?.vs === 'number') return item.vs
  const t0 = Number(data?.video?.t0 || 0)
  const inicio = Number(data?.replay?.inicio || 0)
  return t0 ? inicio + (Number(item?.t || 0) - t0) / 1000 : inicio
}

export function snapshotAt(data, sec) {
  const visible = (item) => itemSecond(item, data) <= sec
  const fatos = []
  for (const group of data?.fatos || []) {
    const declaracoes = (group.declaracoes || []).filter(visible)
    if (declaracoes.length) fatos.push({ ...group, declaracoes })
  }
  const propostas = (data?.propostas || []).filter(visible)
  const ataques = (data?.ataques || []).filter(visible)
  const candidatos = {}
  const fim = Number(data?.replay?.fim || 0) || 1
  const inicio = Number(data?.replay?.inicio || 0)
  const share = Math.max(0, Math.min(1, (sec - inicio) / Math.max(1, fim - inicio)))
  for (const [id, cand] of Object.entries(data?.candidatos || {})) {
    const counts = Object.fromEntries(VERDICTS.map((v) => [v, 0]))
    for (const group of fatos) {
      for (const claim of group.declaracoes) {
        if (claim.quem === id && claim.veredito in counts) counts[claim.veredito] += 1
      }
    }
    const tempo = Object.fromEntries(Object.entries(cand.tempo || {}).map(([k, v]) => [k, Math.round(v * share * 10) / 10]))
    candidatos[id] = {
      ...cand,
      ...counts,
      propostas: propostas.filter((p) => p.quem === id).length,
      ataques: ataques.filter((a) => a.quem === id).length,
      tempo,
    }
  }
  const { linhas, replay, ...rest } = data || {}
  return {
    ...rest,
    candidatos,
    fatos,
    propostas,
    ataques,
    video: { ...(data?.video || {}), ao_vivo: false },
    atualizado: Math.floor(sec * 1000),
  }
}

export function lineAt(data, sec, holdS = 1.5) {
  let found = null
  for (const line of data?.linhas || []) {
    if (line.s <= sec && sec < line.e + holdS) found = line
    if (line.s > sec) break
  }
  return found
}

// Assinatura do que está visível: só repinta quando muda.
export function signatureAt(data, sec) {
  const n = (list) => (list || []).filter((item) => itemSecond(item, data) <= sec).length
  const claims = (data?.fatos || []).reduce((acc, g) => acc + n(g.declaracoes), 0)
  const line = lineAt(data, sec)
  return `${claims}|${n(data?.propostas)}|${n(data?.ataques)}|${line ? line.s : ''}`
}

export function clock({ now = () => Date.now(), start = 0, rate = 1 } = {}) {
  let base = start
  let t0 = now()
  return {
    get: () => base + ((now() - t0) / 1000) * rate,
    seek: (sec) => { base = sec; t0 = now() },
  }
}

export function mmss(sec) {
  const s = Math.max(0, Math.floor(sec))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const pad = (x) => String(x).padStart(2, '0')
  return h ? `${h}:${pad(m)}:${pad(s % 60)}` : `${m}:${pad(s % 60)}`
}
