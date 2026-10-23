# Handoff for Claude Code (2026-10-22 night)

## Goal
Live fact-check of the **Globo debate, 10/23 at 21:20 BRT**. Targets:
- raw accuracy ≥90%
- 0 wrong Falso
- every verdadeiro/impreciso/falso verdict has a real, verifiable source URL (official sources/fact-checkers preferred); otherwise **sem_dados**. LLM opinion is never published as a verdict.

## Current numbers (Band debate replay; claim bank excludes the Band answers via `PLACAR_BANK_EXCLUDE=band-2026-10-18`)
| run | half | gold matched | decided | correct | acc | wrong Falso | unsourced |
|---|---|---|---|---|---|---|---|
| dev3_noband @2846bbc | tune (0–3300s) | 22/34 | 13 | 9 | 69% | 0 | 0 |
| held1_noband @2846bbc | held (3300s+) | 10/28 | 0 | 0 | n/a | 0 scored, **1 real** | 0 |
| old full run (pre-fixes) | tune / held | 11/32 / 1/20 | 11 / 1 | 11 / 1 | 100% | 0 | 0 |

Held-out caveats:
- "12 mil médicos" (gold impreciso) produced a second claim published as **falso**, so treat this as a wrong Falso. The scorer matched an earlier sem_dados claim instead, which is why it shows 0.
- Held-out matched claims ended sem_dados because of the judge deadline ("não terminou a tempo") and blind-verify disagreement.

Remaining tune errors (gold → ours):
- "73% presos": impreciso → verdadeiro
- "recorde de mulheres assassinadas": impreciso → verdadeiro
- "só PT emendas": falso → impreciso
- "mulheres espancadas": verdadeiro → impreciso

Never tune on the held-out half.

## Architecture
- `pipeline/placar/`: Python pipeline.
  - `turns.py`: process_turn → bank shortcut → LLM extraction (classify_turn) → `_judge`. The judge runs search + official data, then judge, a blind 2nd verifier, a tiebreak, and `_publish` with a support check.
  - `board.py`: `set_verdict` is the source gate.
  - `retrieve.py`: Google Fact Check, then SearXNG, then Brave, then DuckDuckGo (with a circuit breaker).
  - `official.py`: IBGE SIDRA / BCB SGS.
  - `claim_bank.py` + `data/`: fact-checker bank.
  - `llm/`: router plus providers.
  - `worker.py`: queue; STALE_S is 90.
  - `replay.py` / `__main__.py`: `placar replay|serve|live`.
- `web/`: the viewer. `site/` / `flutter_web/` / `lib/`: app and landing.
- `supabase/`: Supabase project `igpkunwxmtopdqtbsuso`, which stores the placar JSON.
- Legacy deploy: gh-pages, by copying the web files.
- `tools/chrome_search.py`: experimental real-Chrome search, NOT wired in. Google showed a captcha and headless Bing returned junk.

## Fresh-clone setup
```
python3 -m venv .venv && .venv/bin/pip install -e "pipeline[dev]" numpy
cd pipeline && ../.venv/bin/python -m pytest -q      # 80 pass
```
SearXNG is the primary search, at http://127.0.0.1:8888 (the default for `SEARXNG_URL`):
- install SearXNG from source in a venv
- enable the json format in settings.yml
- run `python -m searx.webapp` with `SEARXNG_SETTINGS_PATH`
- check: `curl "http://127.0.0.1:8888/search?q=ibge&format=json"`

Env var NAMES only (values live in your own secret store, never in git):
- LLM keys: GROQ_API_KEY, OPENROUTER_API_KEY / AH_OPENROUTER_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY
- Search and Supabase: GOOGLE_FACTCHECK_API_KEY, BRAVE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_BUCKET
- Provider config: LLM_PROVIDERS, VERIFY_PROVIDERS, CLAUDE_BIN, CLAUDE_MODEL, GROK_CLI_BIN, GROK_CLI_FAST_MODEL, GROK_CLI_JUDGE_MODEL, GROK_CLI_EFFORT, GROK_CLI_PARALLEL
- Pipeline config: SEARXNG_URL, RETRIEVE_DDG, PLACAR_BANK_EXCLUDE, PLACAR_STALE_S, PLACAR_OFFICIAL, PLACAR_TRANSCRIPTS_DB, STT_PROVIDER, WHISPER_MODEL

## Eval
- `eval/data/transcripts.sqlite` (≈1 MB): Band transcripts. Never re-transcribe.
- `eval/data/jobs.jsonl`: the per-turn jobs.
- Gold: `pipeline/placar/data/qa/gold-band.json` (52 items). Tune half is t<3300s, held-out is t≥3300s.
- `eval/turn_eval.py NAME REPO_DIR [tune|held|all]`: runs process_turn directly on the turns (DEV_PAR threads) and writes runs/NAME/placar.json.
  - The scripts still hardcode `/workspace/data/eval` paths. Point them at `eval/` (and `eval/data/jobs.jsonl`) on a fresh clone.
- Score: `EVAL_SPEED=1.0 python -c "exec(open('eval/score.py').read().split('if __name__')[0]);print(score('NAME'))"`. It reports tune/held acc, coverage, wrong_falso, no_source and errors.
- One tune run takes ~15 min with grok CLI.

## Running live (debate night)
1. Check that the providers respond: `grok` CLI on PATH, `claude` CLI if installed, and SearXNG up.
2. `placar live --url <stream>` (or `--source` for ffmpeg), plus `placar serve --dir out` for the viewer. Upload goes to Supabase.
3. Watch `no_source` (must stay 0) and every falso.

## Prioritized TODO
1. **Context→impreciso rule** in `SYSTEM_JUDGE_TURN`. Fact-checker methodology:
   - a real base, but rounded up, an unconfirmed "recorde/só/nunca/o maior", missing context, or wrong attribution = impreciso
   - falso only when the numeric/factual core is wrong

   Validate on tune AND confirm held-out does not drop. This would also fix the held-out "médicos" falso.
2. **Coverage.** Held-out matched claims die on the judge deadline and verifier disagreement. Make the verifier a strong, different provider and check CLAIM_DEADLINE_S.
3. **Claude CLI as the first LLM.** The order is Claude CLI → Grok CLI → Groq → OpenRouter. On the box Claude was missing, Groq hits 429 (8k TPM) and OpenRouter times out.
4. Resend reminder emails to subscribers.
5. WhatsApp.
6. LivePix.

## Rules
- No secrets in git or logs.
- Never push `.github/workflows`.
- No subscriber PII.
- Never vote on the production poll.
- Commit only tested code, and push to main after `pull --rebase`.
