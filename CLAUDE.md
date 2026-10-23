# CLAUDE.md
Mentirômetro / Placar da Verdade: live fact-checking of Brazilian presidential debates.
**Read docs/HANDOFF.md first.** It covers goals, numbers, architecture, setup, eval, live run, TODO and rules.
Hard rules: every verdadeiro/impreciso/falso must have a real source URL (else sem_dados); 0 wrong Falso;
never commit secrets; never push .github/workflows; no subscriber PII; never vote on the prod poll.
Tests: `cd pipeline && python -m pytest -q`. Revert `pipeline/fixtures/sample_report.json` before `git pull --rebase`.
