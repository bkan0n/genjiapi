import logging
from dataclasses import asdict, dataclass
from typing import List, Optional

import httpx
from litestar import Request, Response
from litestar.middleware import MiddlewareProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

log = logging.getLogger(__name__)

@dataclass
class UmamiPayload:
    """Dataclass for the payload of an Umami request. See https://umami.is/docs/api/sending-stats"""
    hostname: str
    language: str
    referrer: str
    screen: str
    title: str
    url: str
    website: str
    ip: str
    # name: str
    # currently not used -> asdict() outputs "None" if not set, has to be prevented if this field is used
    # data: Optional[dict] = None


@dataclass
class UmamiRequest:
    payload: UmamiPayload
    type: str = "event"  # currently the only type available

async def send_umami_payload(
    api_endpoint: str, request_payload: UmamiRequest, headers: dict, follow_redirects: bool
):
    async with httpx.AsyncClient() as client:
        log.info("10")
        try:
            log.info("11")
            payload = asdict(request_payload)
            log.info("12")
            await client.post(
                api_endpoint, json=payload, headers=headers, follow_redirects=follow_redirects
            )
            log.info("13")
        except Exception as e:
            log.info("14")
            # Log or handle exception if necessary
            print(f"Error sending umami payload: {e}")
    log.info("15")
class UmamiMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: ASGIApp,
        api_endpoint: str,
        website_id: str,
        follow_redirects: bool = True,
        proxy_enabled: bool = False,
        trusted_proxies: Optional[List[str]] = None,
    ) -> None:
        if not api_endpoint:
            return  # TODO: This is for CI/CD
        self.app = app
        if not api_endpoint.endswith("/"):
            api_endpoint += "/"
        self.api_endpoint = api_endpoint + "send"
        self.website_id = website_id
        self.follow_redirects = follow_redirects
        self.trusted_proxies = set(trusted_proxies) if proxy_enabled and trusted_proxies else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        log.info("1")
        request = Request(scope)
        log.info("2")
        response = Response(content=b"")
        log.info("3")
        umami_request = UmamiRequest(
            payload=UmamiPayload(
                hostname=request.url.hostname,
                language=request.headers.get("Accept-Language", ""),
                referrer=request.headers.get("Referer", ""),
                screen="",
                title="",
                url=request.url.path,
                website=self.website_id,
                ip=request.headers.get("X-Real-IP", request.client.host),
            )
        )
        log.info("4")
        umami_headers = {
            "User-Agent": request.headers.get("User-Agent", ""),
            "X-Forwarded-Proto": "https",
        }
        log.info("5")
        if self.trusted_proxies and (
            request.client.host in self.trusted_proxies or "0.0.0.0" in self.trusted_proxies
        ):
            log.info("in 5")
            umami_headers.update(
                {
                    "X-Real-IP": request.headers.get("X-Real-IP", request.client.host),
                    "X-Forwarded-For": request.headers.get("X-Forwarded-For", request.client.host),
                    "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", request.url.hostname),
                }
            )
        else:
            log.info("in 5 2")
            umami_headers.update(
                {
                    "X-Real-IP": request.client.host,
                    "X-Forwarded-For": request.client.host,
                    "X-Forwarded-Host": "",
                }
            )
        log.info("6")
        await send_umami_payload(
            self.api_endpoint, umami_request, umami_headers, self.follow_redirects
        )
        log.info("7")
        await self.app(scope, receive, send)
