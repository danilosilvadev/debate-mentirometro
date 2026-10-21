import { buildView } from './snapshot.mjs'
import { startPolling } from './poll.mjs'
import { mount } from './render.mjs'

const root = document.querySelector('#app')
const params = new URLSearchParams(location.search)
const source = params.get('src') || './sample/placar.json'
const hooks = {
  buildView,
  onSnapshot(view) {
    document.title = `Placar da Verdade — ${view.candidates.map((item) => item.nome).join(' × ') || 'ao vivo'}`
  },
  onScore() {},
  onFeed() {},
}

const ui = mount(root, hooks)
startPolling({
  url: source,
  onSnapshot: (snapshot) => ui.setSnapshot(snapshot),
  onError: (error) => ui.setStatus(error.message || 'Sem conexão com o placar.'),
})
