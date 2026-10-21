# Placar da Verdade — site

Site estático do debate, em português, sem framework e sem build. É a mesma conta do aplicativo: Mentirômetro, propostas versus ataques, linha do tempo de 5 minutos, fatos checados, propostas explicadas, Como ler e Como funciona.

O visual segue o app (fundo claro, cartões, vereditos nas cores verde, laranja e vermelho). O YouTube só entra quando alguém toca em “Ver a live”.

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

O endereço padrão está em `config.js` (`PLACAR_BASE`). A página busca esse JSON a cada 5 segundos, para quando a aba fica escondida e só redesenha se `atualizado` mudou. Se o feed não responde, entra a simulação com uma faixa amarela.

Peso medido nesta máquina, somando os arquivos que a página pede (o `og.jpg` não entra; o YouTube só entra depois do toque):

| | sem gzip | gzip (o que viaja) |
|---|---:|---:|
| Casca: HTML, CSS, JS, config, ícone | 56 KB | 17 KB |
| Simulação, com `demo/placar.json` | 64 KB | 19 KB |

Os dois ficam abaixo de 100 KB. O cartão de compartilhamento `og.jpg` tem 36 KB e só é buscado pelo WhatsApp ou pelo X.

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
