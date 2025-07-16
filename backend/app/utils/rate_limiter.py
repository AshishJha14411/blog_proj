import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status

# In-memory store: key → deque of request timestamps
_request_log: dict[str, deque[float]] = defaultdict(deque)

def rate_limit(
    request: Request,
    *,
    limit: int = 5,
    window: int = 60
) -> None:
    """
    Allow up to `limit` requests per `window` seconds per client IP + path.
    Raises HTTPException 429 if exceeded.
    """
    client_ip = request.client.host
    path      = request.url.path
    key       = f"{client_ip}:{path}"
    now       = time.time()
    dq        = _request_log[key]

    # Purge old entries
    while dq and dq[0] <= now - window:
        dq.popleft()

    if len(dq) >= limit:
        # Too many in current window
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests, please try again later."
        )

    # Record this request
    dq.append(now)
def signup_rate_limiter(request: Request):
    # will raise HTTPException if over the limit
    rate_limit(request, limit=1, window=60)