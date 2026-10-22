Saída real do pipeline (teste dev, 22/10/2026 ~9h BRT): debate Band 2º turno, YouTube RugVB17uRVM, primeiros 30 min,
áudio gravado tocado a 1,5x pelo pipeline completo (Groq Whisper + 2ª passada whisper-large-v3 em trechos com números,
voz ECAPA com detecção de fala sobreposta, Groq gpt-oss-120b + qwen3.8-27b, SearXNG, banco de checagens profissionais).
A cota diária grátis da Groq acabou no meio do teste: 45 de 179 turnos não foram classificados, por isso há poucas afirmações.

Cada afirmação tem `vs` (fim da frase no vídeo), `va` (quando apareceu), `vv` (quando o veredito saiu) e `lat` (va - vs).
`eventos` (votos e super chats) são SIMULADOS para testar o replay (`eventos.simulado = true`).
Replay: `?replay=RugVB17uRVM&src=./teste/` (relógio simulado: `&replay_clock=1&t=<segundo>`). Não é placar publicado.
