"""Envio opcional do placar.json para Supabase Storage ou Cloudflare R2."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from placar.config import Settings


def upload_configured(settings: Settings, body: bytes) -> list[str]:
    done: list[str] = []
    if settings.supabase_url and settings.supabase_key:
        upload_supabase(settings, body)
        done.append("supabase")
    if (
        settings.r2_account_id
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
        and settings.r2_bucket
    ):
        upload_r2(settings, body)
        done.append("r2")
    return done


def upload_supabase(settings: Settings, body: bytes, opener=None) -> None:
    url = (
        f"{settings.supabase_url}/storage/v1/object/"
        f"{settings.supabase_bucket}/placar.json"
    )
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.supabase_key}",
            "apikey": settings.supabase_key,
            "Content-Type": "application/json",
            "x-upsert": "true",
        },
    )
    _send(request, opener)


def upload_r2(settings: Settings, body: bytes, opener=None, now: datetime | None = None) -> None:
    moment = now or datetime.now(timezone.utc)
    amz_date = moment.strftime("%Y%m%dT%H%M%SZ")
    datestamp = moment.strftime("%Y%m%d")
    host = f"{settings.r2_account_id}.r2.cloudflarestorage.com"
    canonical_uri = f"/{settings.r2_bucket}/placar.json"
    payload_hash = hashlib.sha256(body).hexdigest()
    canonical_headers = (
        f"host:{host}\n"
        f"x-amz-content-sha256:{payload_hash}\n"
        f"x-amz-date:{amz_date}\n"
    )
    signed_headers = "host;x-amz-content-sha256;x-amz-date"
    canonical_request = "\n".join(
        [
            "PUT",
            canonical_uri,
            "",
            canonical_headers,
            signed_headers,
            payload_hash,
        ]
    )
    scope = f"{datestamp}/auto/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    signing_key = _signing_key(settings.r2_secret_access_key, datestamp)
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    authorization = (
        "AWS4-HMAC-SHA256 "
        f"Credential={settings.r2_access_key_id}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    request = Request(
        f"https://{host}{canonical_uri}",
        data=body,
        method="PUT",
        headers={
            "Host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Authorization": authorization,
            "Content-Type": "application/json",
        },
    )
    _send(request, opener)


def _signing_key(secret: str, datestamp: str) -> bytes:
    def sign(key: bytes, message: str) -> bytes:
        return hmac.new(key, message.encode(), hashlib.sha256).digest()

    dated = sign(("AWS4" + secret).encode(), datestamp)
    regional = sign(dated, "auto")
    service = sign(regional, "s3")
    return sign(service, "aws4_request")


def _send(request: Request, opener) -> None:
    call = opener or urlopen
    try:
        with call(request, timeout=20) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Upload HTTP {exc.code}: {detail[:300]}") from exc
    except URLError as exc:
        raise RuntimeError(f"Upload falhou: {exc.reason}") from exc
