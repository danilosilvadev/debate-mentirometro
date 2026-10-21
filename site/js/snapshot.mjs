/** Normaliza o placar.json, a linha do tempo e os filtros. */

import { mentiromentro } from './score.mjs'

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

export function originMs(snapshot) {
  const video = snapshot?.video
  return video?.comeco ?? video?.t0 ?? snapshot?.atualizado ?? 0
}

export function timelineOf(snapshot) {
  const linha = snapshot?.linha || {}
  const minutes = Object.keys(linha).map((key) => Number(key)).filter((n) => !Number.isNaN(n))
  if (!minutes.length) return []
  const first = Math.min(...minutes)
  const last = Math.max(...minutes)
  const ini = Math.floor(first / 5)
  const fim = Math.floor(last / 5)
  const origin = originMs(snapshot)
  const columns = []
  for (let block = ini; block <= fim; block += 1) {
    const cell = { block, startMs: origin + block * 300000, endMs: origin + (block + 1) * 300000, by: {} }
    for (const candidate of candidatesOf(snapshot)) {
      let attacks = 0
      let proposals = 0
      for (let offset = 0; offset < 5; offset += 1) {
        const mark = linha[String(block * 5 + offset)] || {}
        attacks += mark[`a${candidate.id}`] || 0
        proposals += mark[`p${candidate.id}`] || 0
      }
      cell.by[candidate.id] = { attacks, proposals }
    }
    columns.push(cell)
  }
  return columns
}

export function effectiveOrder(snapshot, override) {
  if (override) return override
  if (snapshot?.encerrado || snapshot?.revisao) return 'debate'
  return 'recentes'
}

export function filterClaims(claims, filter, { ignore } = {}) {
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
  const copy = claims.slice()
  copy.sort((a, b) => (order === 'recentes' ? b.t - a.t : a.t - b.t))
  return copy
}

export function buildView(snapshot, filter = {}) {
  const candidates = candidatesOf(snapshot)
  const [left, right] = candidates
  const reading = left && right
    ? mentiromentro(left.nome, right.nome, left, right)
    : null
  const claims = claimsOf(snapshot)
  const order = effectiveOrder(snapshot, filter.order)
  const visible = sortClaims(filterClaims(claims, filter), order)
  return {
    snapshot,
    candidates,
    reading,
    claims,
    visible,
    timeline: timelineOf(snapshot),
    propostas: snapshot?.propostas || [],
    ataques: snapshot?.ataques || [],
    order,
    filter,
  }
}
