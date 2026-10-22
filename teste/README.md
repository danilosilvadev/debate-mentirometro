Saída real do pipeline (teste dev, 22/10/2026 09h38–10h09 BRT, rodada t30A): debate Band 2º turno, YouTube RugVB17uRVM, primeiros 30 min,
áudio gravado tocado em tempo real (1,0x) pelo pipeline completo (Groq Whisper + 2ª passada whisper-large-v3 em trechos com números,
voz ECAPA com detecção de fala sobreposta, Groq gpt-oss-120b + qwen3.8-27b, SearXNG, banco de checagens profissionais).
Limite por minuto da Groq grátis: 21 de 177 turnos falharam. 13 afirmações sem veredito a tempo viraram sem_dados (regra atual). Títulos de acertos do banco = frase checada.

Cada afirmação tem `vs` (fim da frase no vídeo), `va` (quando apareceu), `vv` (quando o veredito saiu) e `lat` (va - vs).
`eventos` (votos e super chats) são SIMULADOS para testar o replay (`eventos.simulado = true`).
Replay: `?replay=RugVB17uRVM&src=./teste/` (relógio simulado: `&replay_clock=1&t=<segundo>`). Não é placar publicado.
