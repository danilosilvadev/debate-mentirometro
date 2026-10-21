/** Aplica a fita de eventos em cima de um snapshot. Buraco de seq pede resync. */

export function applyEvent(snapshot, event, expectedSeq) {
  if (!event || event.v !== 1 || event.seq !== expectedSeq) {
    return { snapshot, seq: expectedSeq, resync: true }
  }
  const next = structuredClone(snapshot)
  const payload = event.payload || {}
  if (event.type === 'claim.created') {
    const tema = payload.tema || 'geral'
    let group = (next.fatos || []).find((item) => item.tema === tema)
    if (!group) {
      group = { tema, atualizado: event.t, declaracoes: [] }
      next.fatos = [...(next.fatos || []), group]
    }
    group.declaracoes.push({
      t: event.t,
      quem: event.quem,
      afirmacao: payload.afirmacao,
      contexto: payload.contexto || '',
      veredito: payload.veredito || 'em_revisao',
      motivo: payload.motivo || '',
      literal: payload.literal || '',
    })
    group.atualizado = event.t
  } else if (event.type === 'claim.updated') {
    for (const group of next.fatos || []) {
      const claim = (group.declaracoes || []).find(
        (item) => item.t === event.t && item.quem === event.quem && item.afirmacao === payload.afirmacao,
      )
      if (!claim) continue
      claim.veredito = payload.veredito
      claim.motivo = payload.motivo || claim.motivo
      if (payload.fonte) claim.fonte = payload.fonte
      if (payload.corrigido) claim.corrigido = payload.corrigido
      group.atualizado = event.t
    }
  } else if (event.type === 'proposta.created' || event.type === 'proposta.incremented') {
    const list = next.propostas || []
    const found = list.find((item) => item.quem === event.quem && item.titulo === payload.titulo)
    if (found) {
      found.vezes = payload.vezes || found.vezes + 1
      found.t = event.t
    } else {
      list.push({
        quem: event.quem,
        titulo: payload.titulo,
        explicacao: payload.explicacao || '',
        vezes: payload.vezes || 1,
        t: event.t,
      })
    }
    next.propostas = list
  } else if (event.type === 'ataque.created') {
    next.ataques = [{ quem: event.quem, resumo: payload.resumo, t: event.t }, ...(next.ataques || [])]
  } else if (event.type === 'score.updated' && payload.candidatos) {
    for (const [slot, counts] of Object.entries(payload.candidatos)) {
      if (next.candidatos?.[slot]) Object.assign(next.candidatos[slot], counts)
    }
  } else if (event.type === 'debate.status') {
    if (next.video) next.video.ao_vivo = Boolean(payload.ao_vivo)
    if (payload.encerrado) next.encerrado = payload.encerrado
  }
  next.atualizado = event.t
  return { snapshot: next, seq: event.seq + 1, resync: false }
}
