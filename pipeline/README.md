# Pipeline do Placar da Verdade

Robô em Python que transforma o áudio de um debate no `placar.json` que o app Flutter já lê. Não há um modelo obrigatório nesta máquina: o replay de exemplo usa provedores fictícios. Claude CLI, OpenRouter, whisper e as buscas entram quando as ferramentas e as chaves existem.

## O que ele faz

1. Corta o áudio em blocos de 10 s com 2 s de sobreposição (`yt-dlp` + `ffmpeg`).
2. Transcreve em português com faster-whisper, se o pacote opcional estiver instalado.
3. Compara o embedding da fala com duas amostras de voz (cosseno). Sem amostra, o replay usa o `quem` do roteiro.
4. Classifica a fala: proposta, ataque, afirmação checável, defesa, balanço ou outro.
5. Busca fontes (Google Fact Check Tools, SearXNG, Brave se houver chave).
6. Julga. **Falso** e **impreciso** só são publicados se um segundo provedor concordar. Até lá o fato fica **em revisão** e fora do Mentirômetro.
7. Escreve `placar.json` no formato do app, mais `events.jsonl` (fita `v: 1` do plano).
8. Pode servir o JSON localmente e, se as chaves existirem, enviar a Supabase Storage ou a um bucket R2.

A conta do Mentirômetro é a do app: falso vale 1, impreciso vale 0,5, sem dados e em revisão ficam de fora, ponteiro só com 3 fatos checáveis de cada lado, ângulo `(erro da direita − erro da esquerda) × 90`.

## Provedores de LLM

Interface única. A ordem padrão é `claude_cli`, depois `groq` (gpt-oss-120b), depois `openrouter`; a confirmação de falso/impreciso usa `groq_verify` (qwen3.8-27b) primeiro.

- **Claude Code CLI** (principal), na assinatura de quem roda o robô. Modo headless, conferido na documentação de 21/10/2026 (`code.claude.com/docs/en/headless`):
  - uma chamada: `claude -p "…" --output-format json --json-schema '…' --model haiku --permission-mode dontAsk --max-turns 1`
  - sessão persistente, para não pagar a partida do processo a cada fala: `claude -p --input-format stream-json --output-format stream-json --verbose --model haiku`
  - cada linha não vazia no stdin é uma mensagem; linha em branco é ignorada
  - a cada `CLAUDE_SESSION_CHUNKS` falas (padrão 8) a sessão recomeça, para o contexto não crescer o debate inteiro
  - o alias `haiku` escolhe o Haiku atual da assinatura. A classificação ao vivo foi pensada para **Haiku 5.5**; se o CLI listar um id completo, coloque-o em `CLAUDE_MODEL`
- **OpenRouter** (fallback), API compatível com OpenAI, modelos cujo id termina em `:free`.
- **Anthropic API** e **Gemini**, opcionais: entram só se estiverem em `LLM_PROVIDERS` e a chave existir.

Failover automático quando o CLI erra, estoura o orçamento de latência (`CLAUDE_TIMEOUT_S`, padrão 12 s), devolve mensagem de limite de uso, ou o JSON não fecha o schema (há uma tentativa de reparo: cerca markdown, objeto interno, chaves extras). Erro transitório tenta de novo no mesmo provedor. Limite de uso abre o circuit breaker na hora; os outros erros abrem depois de 3 falhas, por 60 s. Cada chamada é logada com provedor, latência e se houve failover.

## Transcrição (STT)

`STT_PROVIDER=local` (padrão) usa faster-whisper na máquina (`WHISPER_MODEL`, `small`/`int8` no CPU).
`STT_PROVIDER=groq` usa o Whisper hospedado da Groq e cai no local sozinho se der erro ou passar de `GROQ_TIMEOUT_S` (padrão 8 s).

- Conferido em 21/10/2026 em `console.groq.com/docs/speech-to-text`: endpoint compatível com OpenAI `POST https://api.groq.com/openai/v1/audio/transcriptions`, modelo `whisper-large-v3-turbo`, **US$ 0,04 por hora de áudio**, cobrança mínima de 10 s por pedido, até 25 MB por arquivo no plano gratuito. `whisper-large-v3` custa US$ 0,111/h.
- Blocos de 10 s com 2 s de sobreposição = 1,25 s de áudio cobrado por segundo de debate, cerca de US$ 0,13 por 2,5 h.
- Chave em `GROQ_API_KEY`. O pedido manda um `User-Agent` próprio: o Cloudflare da Groq recusa o do urllib (erro 1010).

## Captura do áudio

`python -m placar live --url … --seconds N` roda `yt-dlp -o -` num pipe para o `ffmpeg`, que entrega PCM 16 kHz. Se o pipe cair, reabre até `--retries` vezes (em VOD retoma do ponto lido). O caminho antigo (`yt-dlp -g` + ffmpeg na URL do googlevideo) levava 403 do YouTube.

Alternativas quando o YouTube bloquear (403, "confirm you're not a bot"):
- `--source <url>`: stream de rádio/TV direto no ffmpeg (Rádio Bandeirantes, BandNews FM e afins têm stream HTTP/Icecast);
- placa de captura HDMI ou o áudio do sistema (`--source` com `-f pulse`/`alsa` via ffmpeg);
- rodar numa máquina com IP residencial em vez de nuvem.

Cada bloco é dono do trecho `[início + 1 s, fim − 1 s]`; um segmento só sai no bloco que contém o seu meio, e `dedupe_overlap` tira palavras repetidas na emenda.

## LLM assíncrono e classificação por turno

O laço de áudio (captura → STT → voz) nunca espera o modelo: cada turno de fala de um candidato (segmentos seguidos da mesma voz, até 60 s) entra numa fila (`placar/worker.py`, pool de 2 threads). Uma chamada `classify_turn` por turno devolve a LISTA de itens (`TURN_SCHEMA`: proposta, ataque ou afirmação checável, cada um com título curto, citação exata, categoria e, para afirmações, palavras de busca). Cada afirmação (até 2 por turno) passa por busca e julgamento. O `placar.json` é reescrito a cada item que chega. Toda chamada tem prazo de relógio de parede (`CLAUDE_TIMEOUT_S`, `OPENROUTER_TIMEOUT_S`).

## Busca de fontes sem chave

Além de Google Fact Check, SearXNG e Brave (opcionais, com chave/URL), há DuckDuckGo HTML (`RETRIEVE_DDG=1`, padrão no `from_env`): busca restrita com `site:` a checadores, imprensa e `gov.br`, filtra por lista de domínios confiáveis, espera 2 s entre pedidos e guarda em cache (`~/.cache/placar/ddg.json`). O DuckDuckGo devolve 202 quando desconfia de robô; aí a afirmação fica `sem_dados`. Com `SEARXNG_URL`, o SearXNG próprio é a busca principal (resultados de domínios confiáveis primeiro) e o DuckDuckGo só entra se vierem menos de 2 fontes confiáveis ou o SearXNG estiver fora.

## Vozes (speaker ID)

`scripts/enroll_voice.py <nome> <url> [início fim]` baixa o trecho, gera embeddings ECAPA (speechbrain, CPU) e acumula em `voices/<nome>.npy` + `voices/<nome>.json` (fontes e checagens). Avisa quando um clipe novo não bate com os anteriores (outra voz). Cadastre também os mediadores; sem eles, uma voz masculina de mediador pode cair no candidato.

## Limites conhecidos (21/10/2026)

- **Assinatura do Claude (Pro, Max, Team).** A Anthropic não publica um número fixo de pedidos por minuto para o Claude Code. O limite é uma janela móvel de uso, diferente por plano, e o CLI responde com uma mensagem do tipo "you've hit your limit". Quando isso aparece, o pipeline trata como limite e passa para o OpenRouter. Confira o plano em claude.ai. Não dá para prometer um debate inteiro só na assinatura.
- **OpenRouter `:free`.** Documentação oficial (`openrouter.ai/docs/api/reference/limits`): 20 pedidos por minuto. Por dia, 50 se a conta comprou menos de 10 créditos no total, 1.000 a partir de 10 créditos comprados alguma vez. Um 429 pode ser essa cota ou o provedor de trás lotado. Cinquenta pedidos por dia não cobrem um debate de duas horas.

## Como rodar

```bash
cd pipeline
python3 -m pip install -e '.[dev]'
cp .env.example .env
python3 -m pytest
```

Replay do roteiro sintético, sem rede e sem o CLI:

```bash
python3 -m placar replay --script fixtures/sample_debate.json --mock --speed 0 --out out
```

`--speed 1` espera o tempo real entre as falas. `--speed 0` corre tudo de uma vez. A saída é `out/placar.json`, `out/events.jsonl` e `out/replay_report.json`.

Servir para o app:

```bash
python3 -m placar serve --dir out --port 8787
```

No app:

```bash
flutter run --dart-define=PLACAR_SOURCE=live \
  --dart-define=PLACAR_BASE=http://127.0.0.1:8787/
```

O servidor manda `Access-Control-Allow-Origin: *`, então o Flutter web também consegue buscar.

## Entrar no Claude CLI

No computador que vai rodar o robô (não neste ambiente de nuvem, a menos que a sessão já esteja autenticada):

```bash
# instale o Claude Code e entre com a assinatura
claude
# /login se ainda não estiver autenticado
claude -p "responda ok" --output-format json --model haiku
```

O processo usa o login da máquina. Não coloque a senha no `.env`. A chave `ANTHROPIC_API_KEY` é outro caminho, o da API paga, e só vale se `anthropic` estiver em `LLM_PROVIDERS`.

## O que ainda precisa de máquina e credencial

Este repositório prova a orquestração com áudio e modelos fictícios. Para um debate de verdade ainda falta:

- `claude` autenticado na assinatura, ou `OPENROUTER_API_KEY`
- `ffmpeg` e `yt-dlp` (`python3 -m placar live --url 'https://…' --seconds 30` só corta os blocos)
- `pip install 'placar-pipeline[whisper]'` e, de preferência, GPU para o `large-v3-turbo`; no CPU o padrão do `.env` é `small` / `int8`
- duas amostras de voz dos candidatos (o código compara embeddings; quem gera o vetor é o modelo de speaker ID na máquina local — SpeechBrain/ECAPA — ainda não empacotado porque pesa e pede torch)
- `FACTCHECK_API_KEY` e um SearXNG (`SEARXNG_URL`); Brave é opcional
- para publicar fora da máquina: `SUPABASE_URL` + service role, ou as chaves R2

## Runbook da noite do debate

Testado de ponta a ponta em 21/10/2026 no debate da Band (`RugVB17uRVM`, 5:40–13:20, tempo real) neste fluxo: captura do YouTube → Groq Whisper → voz ECAPA → Groq/Claude → SearXNG → juiz → segundo modelo → `placar.json` → site.

### 1. Antes (uma vez, ~30 min)

```bash
sudo apt install ffmpeg
cd pipeline
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]' yt-dlp speechbrain soundfile torch torchaudio
# vozes já cadastradas em voices/ (lula, flavio; mediadores: tralli = César Tralli, mediador da Globo em 23/10,
# conferido em 2 vídeos da Globo SP com similaridade 0,89; adriana e oinegue = Band). Para outro debate:
python scripts/enroll_voice.py <perfil> '<url do youtube>' <início_s> <fim_s>   # 2-3 trechos de 20-40 s por pessoa
```

SearXNG local (busca principal, sem chave):

```bash
git clone --depth 1 https://github.com/searxng/searxng ~/searxng/src
python3 -m venv ~/searxng/venv
~/searxng/venv/bin/pip install -r ~/searxng/src/requirements.txt
~/searxng/venv/bin/pip install --no-build-isolation -e ~/searxng/src
mkdir -p ~/searxng/etc && cat > ~/searxng/etc/settings.yml <<'YML'
use_default_settings: true
server: {bind_address: "127.0.0.1", port: 8888, secret_key: "troque-isto", limiter: false}
search: {formats: [html, json], default_lang: pt-BR}
YML
SEARXNG_SETTINGS_PATH=~/searxng/etc/settings.yml ~/searxng/venv/bin/python -m searx.webapp &
curl -s 'http://127.0.0.1:8888/search?q=PIB+2024+IBGE&format=json' | head -c 200   # tem que vir "results"
```

Se o SearXNG cair, o pipeline usa o DuckDuckGo HTML sozinho (mais lento, às vezes bloqueia).

Claude CLI (opcional, principal quando existe): `claude` logado na assinatura (`claude /login`, depois `claude -p "ok" --model haiku`). Se o binário não existir, o roteador registra "Claude CLI não encontrado" uma vez e segue para a Groq, sem erro.

### 2. Variáveis (`pipeline/.env` ou `export`)

| variável | valor | para quê |
|---|---|---|
| `GROQ_API_KEY` | chave da Groq | STT (Whisper) e LLM de fallback/confirmação |
| `STT_PROVIDER` | `groq` | Whisper hospedado (cai no local se falhar) |
| `SEARXNG_URL` | `http://127.0.0.1:8888` | busca principal |
| `LLM_PROVIDERS` | `claude_cli,groq,openrouter` (padrão) | ordem de quem classifica e julga |
| `VERIFY_PROVIDERS` | `groq_verify,openrouter,claude_cli,groq` (padrão) | quem confirma falso/impreciso; nunca o mesmo que julgou |
| `GROQ_LLM_MODEL` | `openai/gpt-oss-120b` | classificação e juiz quando não há Claude |
| `GROQ_VERIFY_MODEL` | `qwen/qwen3.8-27b` | segundo modelo (outra família) |
| `OPENROUTER_API_KEY` | opcional | último fallback (`:free`, 50 pedidos/dia sem créditos) |
| `RETRIEVE_DDG` | `1` | fallback DuckDuckGo |

Limites da Groq no plano gratuito (cabeçalhos `x-ratelimit-*`, 21/10/2026): 1.000 pedidos/dia e 8.000 tokens/min **por modelo**. O provedor espera sozinho quando a Groq diz "try again in Xs" e o prazo da chamada permite. Um debate de 2 h usa ~300–500 chamadas.

### 3. Na hora (21h, 15 min antes)

```bash
cd pipeline && . .venv/bin/activate && set -a && . ./.env && set +a
# terminal 1: o robô
python -m placar run --url 'https://www.youtube.com/watch?v=<ID_DO_AO_VIVO>' \
  --a 'Lula:lula' --b 'Flávio Bolsonaro:flavio' --others tralli \
  --debate-id globo-2turno-2026-10-23 --video-id <ID_DO_AO_VIVO> --out out
# terminal 2: publica out/placar.json (CORS *)
python -m placar serve --dir out --host 0.0.0.0 --port 8787
# terminal 3: URL pública https temporária (o GitHub Pages é https, então precisa de https)
cloudflared tunnel --url http://127.0.0.1:8787
```

Abra `https://danilosilvadev.github.io/debate-mentirometro/?src=https://<o-tunel>.trycloudflare.com/` (a barra final importa).

Fontes de áudio, em ordem de preferência:

1. `--url` do YouTube ao vivo (yt-dlp | ffmpeg).
2. `--source 'https://<stream-de-radio>'` (rádio/TV em HTTP/Icecast) se o YouTube der 403 ou "confirm you're not a bot".
3. `--source` com dispositivo do ffmpeg (placa HDMI, `pulse`, `alsa`) para capturar o som da TV.

Teste sem rede de LLM: `--mock`. Ensaio com VOD no relógio real: `--url <vod> --start 340 --seconds 460 --realtime`. Áudio gravado: `--wav arquivo.wav`.

### 4. Durante

- `out/latency_report.json` só sai no fim; ao vivo, olhe o terminal (uma linha por bloco: `stt_ms`, `lag_vs_wallclock_s`). Atraso acima de 5 s seguido = Groq lenta; o STT cai no local sozinho.
- `curl -s localhost:8787/placar.json | python -m json.tool | head` para ver o placar.
- Falso/impreciso só aparecem depois que o segundo modelo concorda; até lá ficam "em revisão" com texto neutro (o primeiro veredito nunca vai para a tela).
- Ctrl-C para parar. Rodar de novo com outro `--out` começa um placar novo.

## Forma do evento

```json
{"v":1,"debate_id":"sintetico-2026","seq":1,"t":1700000000000,
 "type":"claim.created","quem":"2","payload":{"veredito":"em_revisao"}}
```

Tipos: `claim.created`, `claim.updated`, `proposta.created`, `proposta.incremented`, `ataque.created`, `score.updated`, `debate.status`.

## Interação do público (votos, e-mail, super chat)

- Banco: projeto Supabase `debate-mentirometro` (sa-east-1). Esquema em `supabase/001_interacao.sql`
  (RPCs `cast_vote`, `subscribe_email`, `create_superchat`, `mod_pending`, `mod_decide`, `export_events`).
  O site usa só a chave publicável (config.js); e-mails e cliques ficam no esquema `private`.
- Limites: votos 30 por navegador e 300 por IP a cada 10 s (servidor) + 6 toques/s no navegador;
  super chat 2 por minuto por navegador, 140 caracteres, R$ 2–1.000.
- Pagamento: `PLACAR_PAY_PROVIDER = "mock"` (nada é cobrado, rotulado "teste"). Stripe/Mercado Pago
  precisam de servidor com webhook; `create_superchat` recusa provedor diferente de `mock` até isso existir.
- Moderação (rodar durante o debate, ao lado do pipeline):

      PLACAR_MOD_TOKEN_FILE=/workspace/secrets/placar_mod_token \
      SUPABASE_URL=https://igpkunwxmtopdqtbsuso.supabase.co SUPABASE_KEY=<publicável> \
      python -m placar.superchat

  Regras locais (links, palavrões, tamanho) e depois Groq `openai/gpt-oss-20b`. Só `aprovado` aparece.
- Depois do debate, eventos para o replay: `python -m placar.events_export <out> globo-2026-10-23`
  (mesmas variáveis). `--mock` gera eventos simulados, rotulados, para teste.
- Antes do debate, zerar os totais de teste: `update public.vote_totals set n = 0;`

## Legenda e checagem rápida

- A legenda mostra só resumos de afirmações (quem + uma linha), primeiro "Checando…", depois vira
  (cartão 3D) para o veredito. Afirmação que aparece mais de 15 s depois de dita vai só para a lista.
- Turnos saem no fim de frase com 5+ s (máx. 14 s). Fala sobreposta (dois perfis de voz quase
  empatados) não é atribuída a ninguém.
- Banco de checagens (`placar/data/claim_bank.json`): afirmação repetida com os mesmos números
  e orador recebe na hora o veredito do checador profissional. `PLACAR_BANK=0` desliga.
- Blocos com números passam por uma 2ª transcrição (`whisper-large-v3`); se os números
  divergem, vale a do modelo maior (`numeros_conferidos` no latency_report.json).

## Dinheiro: só terceiros (LivePix e Apoia.se)

Nenhum dado de pagamento passa pelo nosso código.
- **Super chat:** o botão abre `LIVEPIX_URL` (config.js), e o doador paga na página da LivePix. A LivePix chama a Edge Function `supabase/functions/livepix-webhook`, que:
  1. Confere se o `clientId` é o nosso.
  2. Pede um token OAuth2 (client credentials) e busca a mensagem em `GET /v2/messages/{id}`. Só confia na API, nunca no corpo do webhook.
  3. Modera com as regras locais, o `flagged` da LivePix e a Groq. Na dúvida, rejeita.
  4. Grava em `superchats`, e o Realtime mostra só as aprovadas.
- **Apoio mensal:** o botão abre `APOIASE_URL`.
- **Configurar depois:**
  ```
  supabase secrets set LIVEPIX_CLIENT_ID=... LIVEPIX_CLIENT_SECRET=... GROQ_API_KEY=... PLACAR_DEBATE_KEY=globo-2026-10-23
  ```
  Depois, cadastre o webhook `https://igpkunwxmtopdqtbsuso.supabase.co/functions/v1/livepix-webhook` na LivePix.
- **Sem segredos:** a função responde 503.
- **Testes:** `node --test supabase/functions/livepix-webhook/core.test.mjs`, com fixtures de webhook simuladas.
