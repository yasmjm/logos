"""Client IP behind a reverse proxy, without trusting what the client can forge.

Each proxy appends the address it saw to X-Forwarded-For, so with N trusted proxies
in front of the app the real client is the N-th entry from the right. Entries to the
left of it were sent by the client and are never trusted (uvicorn's
--forwarded-allow-ips='*' would use the leftmost one, which a client can forge).
"""

from starlette.requests import Request


def client_ip(request: Request, trusted_proxy_hops: int) -> str:
    if trusted_proxy_hops > 0:
        forwarded = request.headers.get("x-forwarded-for", "")
        hops = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(hops) >= trusted_proxy_hops:
            return hops[-trusted_proxy_hops]
    return request.client.host if request.client else "unknown"
