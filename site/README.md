# Site do placar (pele provisória)

Camada de dados do placar na web, em JavaScript sem framework. O visual definitivo ainda não foi escolhido: esta página só mostra que a conta, o polling, a linha do tempo, as propostas e os fatos funcionam.

Quando a opção visual chegar, a pele troca. Os ganchos já estão em `js/render.mjs` (`onSnapshot`, `onScore`, `onFeed`). A direção combinada para essa pele, quando for a hora:

- experiência de assistir ao debate, não uma cópia do site original
- vídeo (embed do YouTube) no centro, Mentirômetro sempre visível
- feed ao vivo ao lado no desktop; no celular, barra compacta e um painel que desliza
- linha do tempo, propostas e “Como ler” em abas ou seções recolhidas
- fundo escuro, cor forte só nos vereditos, movimento curto respeitando `prefers-reduced-motion`
- candidatos distinguíveis sem depender só da cor
- continuar leve: HTML, CSS e JS puros, bem abaixo de 100 KB fora do embed

## Rodar

```bash
cd site
python3 -m http.server 43124
```

Abra `http://127.0.0.1:43124/`. Sem parâmetro, a página lê `sample/placar.json` (o replay sintético do pipeline). Para o JSON servido pelo robô:

`http://127.0.0.1:43124/?src=http://127.0.0.1:8787/placar.json`

Testes da conta, da linha do tempo, do polling e dos eventos:

```bash
node --test site/test/logic.test.mjs
```

(a partir da raiz do repositório)
