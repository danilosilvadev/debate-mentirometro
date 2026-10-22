// Início do debate (Globo, 2º turno). Mude aqui se a emissora alterar o horário.
window.LANDING_START = window.LANDING_START || "2026-10-23T21:20:00-03:00";
window.LANDING_LIVE_URL = window.LANDING_LIVE_URL || "../?live=1";
// Contador: hoje lê a tabela pública do Supabase; depois aponta para o live.json na borda da Cloudflare.
window.LANDING_COUNT_URL = window.LANDING_COUNT_URL || "";
// Inscrição: hoje RPC do Supabase; depois um Worker (POST JSON com os mesmos campos).
window.LANDING_SUBSCRIBE_URL = window.LANDING_SUBSCRIBE_URL || "";
