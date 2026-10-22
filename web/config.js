// Endereço do placar.json. Troque na hora de publicar.
// A barra no final é opcional. Um debate passado entra com ?d=2026-10-18.
window.PLACAR_BASE = "https://placar-dados.zenithonacademy.com.br/";
// Opcional: id do YouTube (ao vivo ou reprise). Vazio usa snapshot.video.id.
window.PLACAR_VIDEO = "";
// "demo" abre a simulação rotulada. "live" abre PLACAR_BASE.
// ?live=1 lê o placar público. ?demo=1 força a simulação. ?src= aponta um JSON.
window.PLACAR_MODE = "demo";

// Link "Replay" no menu (teste com a saída real do pipeline). Vazio esconde.
window.PLACAR_REPLAY = "?replay=RugVB17uRVM&src=./teste/";

// Interação (votos, e-mail, super chat). A chave abaixo é a publicável do Supabase
// (feita para o navegador; o banco só aceita as RPCs com limite e validação).
window.PLACAR_SUPABASE = {
  url: "https://igpkunwxmtopdqtbsuso.supabase.co",
  key: "sb_publishable_KdJP5K5oLFPEZfkaYv81pw_OjdZ_5aR",
};
window.PLACAR_DEBATE_KEY = "globo-2026-10-23";
// Redes no portão de e-mail (troque pelos perfis reais).
window.PLACAR_SOCIAL = {
  instagram: "https://instagram.com/SEU_PERFIL",
  x: "https://x.com/SEU_PERFIL",
  youtube: "https://youtube.com/@SEU_CANAL",
};
// true = exige clicar em ao menos uma rede para entrar. Padrão: opcional.
window.REQUIRE_SOCIAL_CLICK = false;
// Dinheiro só em terceiros. Super chat: página LivePix (o webhook da LivePix grava a mensagem moderada).
// Apoio mensal: Apoia.se. Troque pelos links reais; com SEU_ o botão avisa "não configurado".
window.LIVEPIX_URL = "https://livepix.gg/SEU_USUARIO";
window.APOIASE_URL = "https://apoia.se/SEU_PROJETO";
