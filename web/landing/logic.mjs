export const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i;
export function validEmail(e) { e = (e || "").trim(); return e.length <= 254 && EMAIL_RE.test(e); }
// Aceita (11) 91234-5678, 11912345678, +55 11 91234-5678 → +5511912345678 ou null.
export function normBR(p) {
  let d = (p || "").replace(/\D/g, "");
  if (d.startsWith("55") && (d.length === 12 || d.length === 13)) d = d.slice(2);
  if (d.startsWith("0")) d = d.slice(1);
  if (!/^[1-9][0-9]9?[0-9]{8}$/.test(d)) return null;
  if (d.length === 11 && d[2] !== "9") return null;
  return "+55" + d;
}
export function countdown(startMs, nowMs) {
  let s = Math.max(0, Math.floor((startMs - nowMs) / 1000));
  const live = s === 0; const d = Math.floor(s / 86400); s %= 86400;
  return { live, d, h: Math.floor(s / 3600), m: Math.floor((s % 3600) / 60), s: s % 60 };
}
export function validate({ email, wa, cEmail, cWa }) {
  const out = { email: null, wa: null, err: "" };
  if (!email && !wa) return { ...out, err: "Informe um e-mail ou WhatsApp." };
  if (email) { if (!validEmail(email)) return { ...out, err: "E-mail inválido." }; if (!cEmail) return { ...out, err: "Marque a autorização do e-mail." }; out.email = email.trim().toLowerCase(); }
  if (wa) { const n = normBR(wa); if (!n) return { ...out, err: "WhatsApp inválido. Use DDD + número." }; if (!cWa) return { ...out, err: "Marque a autorização do WhatsApp." }; out.wa = n; }
  return out;
}
// Troféu Pinóquio: percentuais inteiros que sempre somam 100 (maior resto).
export const PALPITES = ["lula", "flavio", "empate"];
export function pollPct(t) {
  const v = PALPITES.map((k) => Math.max(0, Number(t?.[k]) || 0)); const total = v.reduce((a, b) => a + b, 0);
  if (!total) return { total: 0, lula: 0, flavio: 0, empate: 0 };
  const raw = v.map((x) => (x * 100) / total); const fl = raw.map(Math.floor);
  let rest = 100 - fl.reduce((a, b) => a + b, 0);
  raw.map((x, i) => [x - fl[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (rest > 0) { fl[i]++; rest--; } });
  return { total, lula: fl[0], flavio: fl[1], empate: fl[2] };
}
export const pollLabel = (n) => `${n.toLocaleString("pt-BR")} ${n === 1 ? "palpite" : "palpites"}`;
export const validPick = (p) => PALPITES.includes(p);
