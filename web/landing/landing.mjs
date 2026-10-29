import { countdown, validate, pollPct, pollLabel, validPick } from "./logic.mjs";
const $ = (id) => document.getElementById(id);
const SB = window.PLACAR_SUPABASE || {}; const DEBATE = window.PLACAR_DEBATE_KEY || "globo-2026-10-23";
const START = Date.parse(window.LANDING_START);
const hdr = { apikey: SB.key, Authorization: `Bearer ${SB.key}`, "Content-Type": "application/json" };
const pad = (n) => String(n).padStart(2, "0");
const cid = localStorage.lp_cid || (localStorage.lp_cid = crypto.randomUUID());

const RM = matchMedia("(prefers-reduced-motion: reduce)").matches;
function setD(id, v) {
  const el = $(id); if (el.dataset.v === v) return;
  const old = el.dataset.v || ""; el.dataset.v = v;
  el.innerHTML = [...v].map((ch, i) => (!RM && old && old[i] !== ch && old.length === v.length)
    ? `<i class="dg roll"><em>${old[i]}</em><em>${ch}</em></i>` : `<i class="dg"><em>${ch}</em></i>`).join("");
}
function tick() {
  const c = countdown(START, Date.now());
  setD("cd-d", String(c.d)); setD("cd-h", pad(c.h)); setD("cd-m", pad(c.m)); setD("cd-s", pad(c.s));
  if (c.live) {
    $("count").classList.add("hidden"); $("watch").classList.remove("hidden"); $("watch").href = window.LANDING_LIVE_URL;
    $("pill").textContent = "Ao vivo agora"; document.body.classList.add("is-live"); $("go").textContent = "Quero o lembrete dos próximos";
  }
}
let shown = null;
function showCount(n) {
  if (typeof n !== "number") return;
  document.getElementById("subs-row").classList.toggle("hidden", n < 50);
  const el = $("subs"); const from = shown ?? n; shown = n; const t0 = performance.now();
  const step = (t) => { const k = Math.min(1, (t - t0) / 600); el.textContent = Math.round(from + (n - from) * k).toLocaleString("pt-BR"); if (k < 1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}
async function loadCount() {
  try {
    if (window.LANDING_COUNT_URL) { const j = await (await fetch(window.LANDING_COUNT_URL, { cache: "no-cache" })).json(); return showCount(j.subscribers ?? j.n); }
    const r = await fetch(`${SB.url}/rest/v1/subscriber_count?debate=eq.${encodeURIComponent(DEBATE)}&select=n`, { headers: hdr });
    const j = await r.json(); showCount(j[0]?.n ?? 0);
  } catch { /* mantém o último valor */ }
}
$("form").addEventListener("submit", async (ev) => {
  ev.preventDefault(); $("err").textContent = "";
  const v = validate({ email: $("email").value, wa: $("wa").value, cEmail: $("c-email").checked, cWa: $("c-wa").checked });
  if (v.err) { $("err").textContent = v.err; return; }
  const consent = [v.email && $("c-email").nextElementSibling.textContent, v.wa && $("c-wa").nextElementSibling.textContent].filter(Boolean).join(" | ");
  const body = { p_debate: DEBATE, p_email: v.email, p_whatsapp: v.wa, p_email_consent: !!v.email, p_whatsapp_consent: !!v.wa, p_consent_text: consent, p_client: cid };
  $("go").disabled = true;
  try {
    const url = window.LANDING_SUBSCRIBE_URL || `${SB.url}/rest/v1/rpc/subscribe`;
    const r = await fetch(url, { method: "POST", headers: window.LANDING_SUBSCRIBE_URL ? { "Content-Type": "application/json" } : hdr, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error({ devagar: "Muitas tentativas, tente em um minuto.", email: "E-mail inválido.", whatsapp: "WhatsApp inválido." }[j.erro] || "Não deu certo. Tente de novo.");
    showCount(j.total);
    $("form").classList.add("hidden"); $("done").classList.remove("hidden");
    $("done-msg").textContent = j.novo ? "Você vai receber o lembrete antes do debate." : "Você já estava inscrito — atualizamos seus contatos.";
  } catch (e) { $("err").textContent = e.message; } finally { $("go").disabled = false; }
});
tick(); setInterval(tick, 1000); loadCount(); setInterval(loadCount, 15000);

// Troféu Pinóquio: resultados ficam escondidos até o palpite.
const NOMES = { lula: "Lula", flavio: "Flávio", empate: "Os dois empatam" };
function showPoll(t, mine) {
  const p = pollPct(t);
  for (const k of ["lula", "flavio", "empate"]) { $("pb-" + k).style.width = p[k] + "%"; $("pp-" + k).textContent = p[k] + "%"; }
  $("ptot").textContent = pollLabel(p.total); $("pmine").textContent = NOMES[mine] || "—";
  $("pbtns").classList.add("hidden"); $("pres").classList.remove("hidden");
  document.querySelectorAll(".pb").forEach((b) => b.classList.toggle("sel", b.dataset.pick === mine));
  if (t && t.resultado) $("pfinal").dataset.resultado = t.resultado; // gancho pós-debate (não ligado)
}
async function loadPoll() {
  const mine = localStorage.lp_palpite; if (!validPick(mine)) return;
  try {
    const r = await fetch(`${SB.url}/rest/v1/palpite_totais?debate=eq.${encodeURIComponent(DEBATE)}&select=lula,flavio,empate,resultado`, { headers: hdr });
    showPoll((await r.json())[0] || {}, mine);
  } catch { showPoll({}, mine); }
}
document.querySelectorAll(".pb").forEach((b) => b.addEventListener("click", async () => {
  const pick = b.dataset.pick; $("perr").textContent = "";
  document.querySelectorAll(".pb").forEach((x) => (x.disabled = true));
  try {
    const r = await fetch(`${SB.url}/rest/v1/rpc/palpitar`, { method: "POST", headers: hdr, body: JSON.stringify({ p_debate: DEBATE, p_escolha: pick, p_client: cid }) });
    const j = await r.json();
    if (!r.ok || !j.ok) throw new Error({ devagar: "Calma! Muitos palpites daqui, tente em um minuto.", encerrado: "Palpites encerrados." }[j.erro] || "Não deu certo. Tente de novo.");
    localStorage.lp_palpite = pick; showPoll(j, pick);
  } catch (e) { $("perr").textContent = e.message; } finally { document.querySelectorAll(".pb").forEach((x) => (x.disabled = false)); }
}));
$("pchange").addEventListener("click", () => { $("pres").classList.add("hidden"); $("pbtns").classList.remove("hidden"); });
loadPoll(); setInterval(loadPoll, 20000);
