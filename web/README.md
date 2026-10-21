# Placar da Verdade — site

Site estático do debate, em português, sem framework e sem build. É a mesma conta do aplicativo: Mentirômetro, propostas versus ataques, linha do tempo de 5 minutos, fatos checados, propostas explicadas, Como ler e Como funciona.

O palco é escuro, em tela cheia. A barra de vidro no topo traz os dois candidatos, o placar e o cabo de guerra do Mentirômetro. As checagens de cada lado flutuam sobre o vídeo, sem caixa, e a fala mais recente fica na legenda de baixo. No celular a barra gruda no topo e o feed vira um chat, A à esquerda e B à direita. O nome e a cor de cada candidato vêm do JSON.

O YouTube entra sozinho quando `video.id` (ou `PLACAR_VIDEO` no `config.js`) é um id válido. Sem id, o palco fica no desenho escuro. “Ocultar” tira as checagens e a legenda de cima dos controles do player. ⌘K (ou o botão no canto) abre a linha do tempo, Como ler, Como funciona, as propostas e os debates passados.

## Rodar aqui

```bash
cd web
python3 -m http.server 43125 --bind 0.0.0.0
```

Abra `http://127.0.0.1:43125/?demo=1` para a simulação, com o aviso de fatos fictícios.

Para o `placar.json` do pipeline nesta máquina:

`http://127.0.0.1:43125/?src=http://127.0.0.1:8787/placar.json`

Um debate passado:

`http://127.0.0.1:43125/?d=2026-10-18`

Na simulação, o arquivo local é `demo/placar-2026-10-18.json` (`?demo=1&d=2026-10-18`). No ar, `?d=` pede `placar-2026-10-18.json` no mesmo host do `config.js`.

O endereço padrão está em `config.js` (`PLACAR_BASE`). `PLACAR_VIDEO` troca o id do YouTube sem esperar o JSON. A página busca o placar a cada 5 segundos, para quando a aba fica escondida e só redesenha se `atualizado` mudou. O iframe, quando existe, não é recriado nesse redesenho. Se o feed não responde, entra a simulação, com o aviso no canto.

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

**Cloudflare Pages.** Conecte o repositório, comando de build vazio, diretório de saída `web`. O arquivo `_headers` já evita cache longo do `config.js`.

**Hostinger (ou qualquer Apache).** Envie o *conteúdo* de `web/` para `public_html` (o `index.html` na raiz do domínio). O `.htaccess` liga compressão e o cache curto do `config.js`. No hPanel isso também pode ser um site estático por Git, com a pasta publicada em `web`.

**Qualquer host estático** (Netlify, S3, GitHub Pages, nginx): publique a pasta `web/` como raiz. Não há `npm install` nem etapa de build.

Antes de divulgar:

1. Edite `config.js` e aponte `PLACAR_BASE` para o host do `placar.json` (com ou sem barra no final).
2. Se o domínio não for `placar.zenithonacademy.com.br`, troque `og:url` e `og:image` no `index.html` por URLs absolutas. WhatsApp e o X ignoram caminho relativo.
3. Confira que o host do JSON manda `Access-Control-Allow-Origin` (o servidor do pipeline já manda `*`).

O pipeline local:

```bash
cd pipeline
python3 -m placar serve --dir out --port 8787
```
