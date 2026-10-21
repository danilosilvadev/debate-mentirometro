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
    "estadao.com.br",
    "g1.globo.com",
    "ibge.gov.br",
    "portaldatransparencia.gov.br",
    "tse.jus.br",
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
    ) -> None:
        self.settings = settings
        self._http = http or _http_get
        self._brave_http = brave_http

    def search(self, query: str, *, timeout_s: float = 8.0) -> list[Evidence]:
        found: list[Evidence] = []
        if self.settings.factcheck_key:
            found.extend(self._factcheck(query, timeout_s))
        if self.settings.searxng_url:
            found.extend(self._searx(query, timeout_s))
        if self.settings.brave_key:
            found.extend(self._brave(query, timeout_s))
        found.sort(key=lambda item: (0 if _whitelisted(item.url) else 1, item.origem))
        return found[:5]

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
        status, body = self._http(f"{self.settings.searxng_url}/search?{qs}", timeout_s)
        if status >= 400:
            return []
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return []
        return [
            Evidence(
                titulo=item.get("title") or "",
                url=item.get("url") or "",
                trecho=item.get("content") or "",
                origem="searxng",
            )
            for item in (payload.get("results") or [])[:5]
            if item.get("url")
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
