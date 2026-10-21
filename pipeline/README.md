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

Interface única. A ordem padrão é `claude_cli`, depois `openrouter`.

- **Claude Code CLI** (principal), na assinatura de quem roda o robô. Modo headless, conferido na documentação de 21/10/2026 (`code.claude.com/docs/en/headless`):
  - uma chamada: `claude -p "…" --output-format json --json-schema '…' --model haiku --permission-mode dontAsk --max-turns 1`
  - sessão persistente, para não pagar a partida do processo a cada fala: `claude -p --input-format stream-json --output-format stream-json --verbose --model haiku`
  - cada linha não vazia no stdin é uma mensagem; linha em branco é ignorada
  - a cada `CLAUDE_SESSION_CHUNKS` falas (padrão 8) a sessão recomeça, para o contexto não crescer o debate inteiro
  - o alias `haiku` escolhe o Haiku atual da assinatura. A classificação ao vivo foi pensada para **Haiku 5.5**; se o CLI listar um id completo, coloque-o em `CLAUDE_MODEL`
- **OpenRouter** (fallback), API compatível com OpenAI, modelos cujo id termina em `:free`.
- **Anthropic API** e **Gemini**, opcionais: entram só se estiverem em `LLM_PROVIDERS` e a chave existir.

Failover automático quando o CLI erra, estoura o orçamento de latência (`CLAUDE_TIMEOUT_S`, padrão 12 s), devolve mensagem de limite de uso, ou o JSON não fecha o schema (há uma tentativa de reparo: cerca markdown, objeto interno, chaves extras). Erro transitório tenta de novo no mesmo provedor. Limite de uso abre o circuit breaker na hora; os outros erros abrem depois de 3 falhas, por 60 s. Cada chamada é logada com provedor, latência e se houve failover.

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

## Forma do evento

```json
{"v":1,"debate_id":"sintetico-2026","seq":1,"t":1700000000000,
 "type":"claim.created","quem":"2","payload":{"veredito":"em_revisao"}}
```

Tipos: `claim.created`, `claim.updated`, `proposta.created`, `proposta.incremented`, `ataque.created`, `score.updated`, `debate.status`.
