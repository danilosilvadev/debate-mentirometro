import { countdown, validate } from "./logic.mjs";
const $ = (id) => document.getElementById(id);
const SB = window.PLACAR_SUPABASE || {}; const DEBATE = window.PLACAR_DEBATE_KEY || "globo-2026-10-23";
const START = Date.parse(window.LANDING_START);
const hdr = { apikey: SB.key, Authorization: `Bearer ${SB.key}`, "Content-Type": "application/json" };
const pad = (n) => String(n).padStart(2, "0");
const cid = localStorage.lp_cid || (localStorage.lp_cid = crypto.randomUUID());

function tick() {
  const c = countdown(START, Date.now());
  $("cd-d").textContent = c.d; $("cd-h").textContent = pad(c.h); $("cd-m").textContent = pad(c.m); $("cd-s").textContent = pad(c.s);
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
