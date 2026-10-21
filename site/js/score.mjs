/** Mentirômetro. Mesma conta do app e do site. */

export const MINIMO = 3

export function errorIndex({ verdadeiro = 0, impreciso = 0, falso = 0 }) {
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
