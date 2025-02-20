import logging
from dataclasses import asdict, dataclass
from typing import List, Optional

import httpx
from litestar import Request
from litestar.middleware import MiddlewareProtocol
from litestar.types import ASGIApp, Receive, Scope, Send

log = logging.getLogger(__name__)


@dataclass
class UmamiPayload:
    """Dataclass for the payload of an Umami request. See https://umami.is/docs/api/sending-stats."""

    hostname: str
    language: str
    referrer: str
    screen: str
    title: str
    url: str
    website: str
    ip: str


@dataclass
class UmamiRequest:
    payload: UmamiPayload
    type: str = "event"  # currently the only type available


async def send_umami_payload(
    api_endpoint: str, request_payload: UmamiRequest, headers: dict, follow_redirects: bool
) -> None:
    """Send the Umami payload to the specified API endpoint.

    Args:
        api_endpoint (str): The API endpoint to send the payload to.
        request_payload (UmamiRequest): The payload to send.
        headers (dict): The headers to include in the request.
        follow_redirects (bool): Whether to follow redirects.

    """
    async with httpx.AsyncClient() as client:
        try:
            payload = asdict(request_payload)
            await client.post(api_endpoint, json=payload, headers=headers, follow_redirects=follow_redirects)
        except Exception as e:
            # Log or handle exception if necessary
            print(f"Error sending umami payload: {e}")


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
        """Handle incoming ASGI HTTP requests and send Umami payload."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
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
        umami_headers = {
            "User-Agent": request.headers.get("User-Agent", ""),
            "X-Forwarded-Proto": "https",
        }
        if self.trusted_proxies and (request.client.host in self.trusted_proxies or "0.0.0.0" in self.trusted_proxies):
            umami_headers.update(
                {
                    "X-Real-IP": request.headers.get("X-Real-IP", request.client.host),
                    "X-Forwarded-For": request.headers.get("X-Forwarded-For", request.client.host),
                    "X-Forwarded-Host": request.headers.get("X-Forwarded-Host", request.url.hostname),
                }
            )
        else:
            umami_headers.update(
                {
                    "X-Real-IP": request.client.host,
                    "X-Forwarded-For": request.client.host,
                    "X-Forwarded-Host": "",
                }
            )
        await send_umami_payload(self.api_endpoint, umami_request, umami_headers, self.follow_redirects)
        await self.app(scope, receive, send)
