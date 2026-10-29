"""Busca de fontes: Fact Check Tools, SearXNG e, se houver chave, Brave."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request

from placar.config import Settings
from placar.llm.openrouter import urllib_transport

HttpGet = Callable[[str, float], tuple[int, str]]

WHITELIST = (
    "lupa.uol.com.br",
    "aosfatos.org",
    "projetocomprova.com.br",
    "boatos.org",
    "estadao.com.br",
    "folha.uol.com.br",
    "g1.globo.com",
    "oglobo.globo.com",
    "cnnbrasil.com.br",
    "bbc.com",
    "agenciabrasil.ebc.com.br",
    "poder360.com.br",
    "ibge.gov.br",
    "ipea.gov.br",
    "bcb.gov.br",
    "gov.br",
    "camara.leg.br",
    "senado.leg.br",
    "lupa.uol.com.br",
    "aosfatos.org",
    "estadao.com.br",
    "g1.globo.com",
    "ibge.gov.br",
    "portaldatransparencia.gov.br",
    "tse.jus.br",
    "uol.com.br",
    "valor.globo.com",
    "cartacapital.com.br",
    "nexojornal.com.br",
    "exame.com",
    "infomoney.com.br",
    "jus.br",
    "ipea.gov.br",
    "dieese.org.br",
    "worldbank.org",
    "imf.org",
    "reuters.com",
)


@dataclass(frozen=True)
class Evidence:
    titulo: str
    url: str
    trecho: str
    origem: str

    def as_dict(self) -> dict[str, str]:
        return {
            "titulo": self.titulo,
            "url": self.url,
            "trecho": self.trecho,
            "origem": self.origem,
        }


class Retriever:
    def __init__(
        self,
        settings: Settings,
        http: HttpGet | None = None,
        brave_http: Any = None,
        ddg: Any = None,
    ) -> None:
        self.settings = settings
        self._http = http or _http_get
        self._brave_http = brave_http
        self._ddg = ddg
        self.searx_requests = 0
        self.searx_failures = 0

    def search(self, query: str, *, timeout_s: float = 8.0) -> list[Evidence]:
        found: list[Evidence] = []
        if self.settings.factcheck_key:
            found.extend(self._factcheck(query, timeout_s))
        if self.settings.searxng_url:
            found.extend(self._searx(query, timeout_s))
        if self.settings.brave_key:
            found.extend(self._brave(query, timeout_s))
        trusted = sum(1 for item in found if _whitelisted(item.url))
        if getattr(self.settings, "ddg_enabled", False) and trusted < 2:
            if self._ddg is None:
                self._ddg = DuckDuckGoHtml()
            found.extend(self._ddg.search(query, timeout_s=timeout_s))
        seen: set[str] = set()
        unique = []
        for item in found:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        unique.sort(key=lambda item: 0 if _whitelisted(item.url) else 1)
        return unique[:5]

    def _factcheck(self, query: str, timeout_s: float) -> list[Evidence]:
        qs = urlencode(
            {
                "query": query,
                "languageCode": "pt-BR",
                "key": self.settings.factcheck_key,
            }
        )
        url = f"https://factchecktools.googleapis.com/v1alpha1/claims:search?{qs}"
        status, body = self._http(url, timeout_s)
        if status >= 400:
            return []
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []
        items: list[Evidence] = []
        for claim in payload.get("claims") or []:
            text = claim.get("text") or ""
            for review in claim.get("claimReview") or []:
                items.append(
                    Evidence(
                        titulo=review.get("title") or review.get("publisher", {}).get("name", ""),
                        url=review.get("url") or "",
                        trecho=text,
                        origem="factcheck",
                    )
                )
        return [item for item in items if item.url]

    def _searx(self, query: str, timeout_s: float) -> list[Evidence]:
        qs = urlencode({"q": query, "format": "json", "language": "pt-BR"})
        try:
            status, body = self._http(f"{self.settings.searxng_url}/search?{qs}", timeout_s)
        except Exception:  # SearXNG fora do ar: cai no DuckDuckGo
            self.searx_failures += 1
            return []
        if status >= 400:
            self.searx_failures += 1
            return []
        self.searx_requests += 1
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []
        results = [r for r in (payload.get("results") or []) if r.get("url")]
        # Primeiro os domínios confiáveis; o resto só se não houver nenhum.
        trusted = [r for r in results if _whitelisted(r["url"])]
        return [
            Evidence(
                titulo=item.get("title") or "",
                url=item.get("url") or "",
                trecho=(item.get("content") or "")[:500],
                origem="searxng",
            )
            for item in (trusted or results)[:6]
        ]

    def _brave(self, query: str, timeout_s: float) -> list[Evidence]:
        from urllib.parse import urlencode
        from urllib.request import Request

        from placar.llm.openrouter import urllib_transport

        url = "https://api.search.brave.com/res/v1/web/search?" + urlencode(
            {"q": query, "search_lang": "pt-br"}
        )
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": self.settings.brave_key,
            },
            method="GET",
        )
        transport = self._brave_http or urllib_transport
        status, body = transport(request, timeout_s)
        if status >= 400:
            return []
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []
        web = (payload.get("web") or {}).get("results") or []
        return [
            Evidence(
                titulo=item.get("title") or "",
                url=item.get("url") or "",
                trecho=item.get("description") or "",
                origem="brave",
            )
            for item in web[:5]
            if item.get("url")
        ]


def _whitelisted(url: str) -> bool:
    return any(host in url for host in WHITELIST)


def _http_get(url: str, timeout_s: float) -> tuple[int, str]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    return urllib_transport(request, timeout_s)


# --- DuckDuckGo HTML, sem chave ----------------------------------------------
# Restringe a domínios confiáveis (site:), espera ao menos `min_interval_s`
# entre pedidos e guarda o resultado em cache (memória + disco) para não
# repetir a mesma busca. É o caminho gratuito; os pagos/opcionais vêm antes.

DDG_SITES = ("aosfatos.org", "lupa.uol.com.br", "projetocomprova.com.br", "g1.globo.com",
             "estadao.com.br", "folha.uol.com.br", "agenciabrasil.ebc.com.br", "poder360.com.br",
             "ibge.gov.br", "gov.br")


def ddg_post(query: str, timeout_s: float) -> tuple[int, str]:
    from urllib.error import HTTPError, URLError
    from urllib.request import urlopen

    data = urlencode({"q": query, "kl": "br-pt"}).encode()
    req = Request("https://html.duckduckgo.com/html/", data=data, method="POST",
                  headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) placar-pipeline/0.1",
                           "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except HTTPError as exc:
        return exc.code, ""
    except (URLError, TimeoutError, OSError):
        return 0, ""


def parse_ddg(html_text: str) -> list[Evidence]:
    import html as _html
    import re
    from urllib.parse import parse_qs, urlparse

    out: list[Evidence] = []
    blocks = re.split(r'<div class="result results_links', html_text)[1:]
    for block in blocks:
        link = re.search(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        href = _html.unescape(link.group(1))
        if "duckduckgo.com/l/" in href:
            href = parse_qs(urlparse(href).query).get("uddg", [href])[0]
        if "duckduckgo.com/y.js" in href:
            continue  # anúncio
        snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', block, re.S)
        clean = lambda t: _html.unescape(re.sub(r"<[^>]+>", "", t or "")).strip()
        out.append(Evidence(titulo=clean(link.group(2)), url=href,
                            trecho=clean(snip.group(1) if snip else ""), origem="duckduckgo"))
    return out


class DuckDuckGoHtml:
    def __init__(self, *, post=None, min_interval_s: float = 2.0, cache_path=None,
                 sites: tuple[str, ...] = DDG_SITES, clock=None, sleep=None) -> None:
        import threading
        import time as _time
        from pathlib import Path

        self._post = post or ddg_post
        self.min_interval_s = min_interval_s
        self.sites = sites
        self._clock = clock or _time.monotonic
        self._sleep = sleep or _time.sleep
        self._last = -1e9
        self._lock = threading.Lock()
        self.cache_path = Path(cache_path) if cache_path else Path.home() / ".cache/placar/ddg.json"
        try:
            self._cache = json.loads(self.cache_path.read_text())
        except (OSError, ValueError):
            self._cache = {}
        self.requests = 0

    def search(self, query: str, *, timeout_s: float = 8.0) -> list[Evidence]:
        q = " ".join(query.split())[:160] + " (" + " OR ".join(f"site:{d}" for d in self.sites) + ")"
        with self._lock:
            if q in self._cache:
                return [Evidence(**e) for e in self._cache[q]]
            wait = self.min_interval_s - (self._clock() - self._last)
            if wait > 0:
                self._sleep(wait)
            self._last = self._clock()
            self.requests += 1
            status, body = self._post(q, timeout_s)
            if status != 200:
                # DDG devolve 202/403 quando acha que é robô: espera e tenta uma vez.
                self.failures = getattr(self, "failures", 0) + 1
                self._sleep(self.min_interval_s * 2)
                self._last = self._clock()
                self.requests += 1
                status, body = self._post(q, timeout_s)
                if status != 200:
                    return []
            found = [e for e in parse_ddg(body) if _whitelisted(e.url)][:5]
            self._cache[q] = [e.as_dict() for e in found]
            try:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self.cache_path.write_text(json.dumps(self._cache, ensure_ascii=False))
            except OSError:
                pass
            return found
