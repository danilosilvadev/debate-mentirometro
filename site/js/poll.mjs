/** Polling do placar.json, no mesmo ritmo do site: 6 s, cache de 3 s. */

export function placarUrl(base, now = Date.now()) {
  const bust = Math.floor(now / 3000)
  const trimmed = base.endsWith('/') ? base : `${base}/`
  const url = new URL('placar.json', trimmed.startsWith('http') ? trimmed : new URL(trimmed, 'http://local/'))
  if (!trimmed.startsWith('http')) {
    return `${trimmed}placar.json?t=${bust}`
  }
  url.searchParams.set('t', String(bust))
  return url.toString()
}

export function startPolling({ url, intervalMs = 6000, onSnapshot, onError, fetchImpl = fetch, now = Date.now }) {
  let stopped = false
  let last = null
  let timer = 0

  async function tick() {
    if (stopped) return
    try {
      const target = url.includes('placar.json') ? withBust(url, now()) : placarUrl(url, now())
      const response = await fetchImpl(target)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      if (data.atualizado !== last) {
        last = data.atualizado
        onSnapshot(data)
      }
    } catch (error) {
      onError?.(error)
    }
  }

  tick()
  timer = setInterval(tick, intervalMs)
  return () => {
    stopped = true
    clearInterval(timer)
  }
}

function withBust(url, now) {
  const bust = Math.floor(now / 3000)
  const join = url.includes('?') ? '&' : '?'
  return `${url}${join}t=${bust}`
}
