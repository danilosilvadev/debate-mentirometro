# Placar da Verdade — site

Site estático do debate, em português, sem framework e sem build. É a mesma conta do aplicativo: Mentirômetro, propostas versus ataques, linha do tempo de 5 minutos, fatos checados, propostas explicadas, Como ler e Como funciona.

O palco é escuro, em tela cheia. A barra de vidro no topo traz os dois candidatos, o placar e o cabo de guerra do Mentirômetro. As checagens de cada lado flutuam sobre o vídeo, sem caixa, e a fala mais recente fica na legenda de baixo. No celular a barra gruda no topo e o feed vira um chat, A à esquerda e B à direita. O nome e a cor de cada candidato vêm do JSON.

O YouTube entra sozinho quando `video.id` (ou `PLACAR_VIDEO` no `config.js`) é um id válido. Sem id, o palco fica no desenho escuro. “Ocultar” tira as checagens e a legenda de cima dos controles do player. ⌘K (ou o botão no canto) abre a linha do tempo, Como ler, Como funciona, as propostas e os debates passados.

## Rodar aqui

```bash
cd web
python3 -m http.server 43125 --bind 0.0.0.0
```

Abra `http://127.0.0.1:43125/` para a simulação, com a pílula SIMULAÇÃO e o aviso de fatos fictícios. `config.js` deixa `PLACAR_MODE` em `demo`.

Para o `placar.json` do pipeline nesta máquina:

`http://127.0.0.1:43125/?src=http://127.0.0.1:8787/placar.json`

O placar público (o host responde `Access-Control-Allow-Origin: *`, então o navegador consegue ler):

`http://127.0.0.1:43125/?live=1`

O mesmo atalho está no ⌘K, como “Placar público” / “Voltar à simulação”.

Um debate passado da simulação:

`http://127.0.0.1:43125/?d=2026-10-18`

O arquivo local é `demo/placar-2026-10-18.json`. Com `?live=1&d=2026-10-18`, a página pede `placar-2026-10-18.json` no `PLACAR_BASE`.

`PLACAR_VIDEO` troca o id do YouTube sem esperar o JSON. A página busca o placar a cada 5 segundos, para quando a aba fica escondida e só redesenha se `atualizado` mudou. O iframe, quando existe, não é recriado nesse redesenho. Se o feed público não responde, entra a simulação, com o aviso no canto. Os CSS, a fonte e o `demo/` usam caminho relativo, então o site abre tanto na raiz quanto em `/debate-mentirometro/`.

Peso medido nesta máquina, somando o que a página pede. O iframe do YouTube não entra. A Inter latina está em `fonts/inter-latin.woff2` (47 KB, não comprime).

| | sem gzip | gzip (o que viaja) |
|---|---:|---:|
| Casca: HTML, CSS, JS, config, ícone, Inter | 99 KB | 63 KB |
| Simulação, com `demo/placar.json` | 108 KB | 65 KB |

O cartão de compartilhamento `og.jpg` tem 35 KB e só é buscado pelo WhatsApp ou pelo X.

Testes:

```bash
node --test web/test/logic.test.mjs
```

(a partir da raiz do repositório)

## Publicar

São arquivos estáticos. A raiz do site é esta pasta (`web/`), não o repositório inteiro.

**GitHub Pages.** O workflow `.github/workflows/pages.yml` publica `web/` em cada push na `main`, com `actions/upload-pages-artifact` e `actions/deploy-pages`. O endereço esperado é [https://danilosilvadev.github.io/debate-mentirometro/](https://danilosilvadev.github.io/debate-mentirometro/). O site abre na simulação. ⌘K → “Placar público” (ou `?live=1`) lê `https://placar-dados.zenithonacademy.com.br/placar.json`.

O workflow tenta ligar o Pages pela API (`build_type: workflow`). O `GITHUB_TOKEN` do Actions às vezes não tem permissão para criar o site na primeira vez. Se o deploy falhar com “Get Pages site failed”, no repositório abra **Settings → Pages → Build and deployment → Source: GitHub Actions** e rode o workflow de novo.

**Cloudflare Pages.** Conecte o repositório, comando de build vazio, diretório de saída `web`. O arquivo `_headers` já evita cache longo do `config.js`.

**Hostinger (ou qualquer Apache).** Envie o *conteúdo* de `web/` para `public_html` (o `index.html` na raiz do domínio). O `.htaccess` liga compressão e o cache curto do `config.js`. No hPanel isso também pode ser um site estático por Git, com a pasta publicada em `web`.

**Qualquer host estático** (Netlify, S3, nginx): publique a pasta `web/` como raiz. Não há `npm install` nem etapa de build.

Antes de divulgar em outro domínio:

1. `PLACAR_BASE` já aponta para `https://placar-dados.zenithonacademy.com.br/`. Troque se o JSON mudar de host.
2. `og:url` e `og:image` no `index.html` estão absolutos no endereço do GitHub Pages. WhatsApp e o X ignoram caminho relativo.
3. O host do JSON precisa mandar `Access-Control-Allow-Origin`. O placar público já manda `*`.

O pipeline local:

```bash
cd pipeline
python3 -m placar serve --dir out --port 8787
```
