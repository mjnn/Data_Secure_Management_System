from app.core.config import settings
from app.core.rate_limit import limiter


def auth_rate_limit(limit: str):
    def decorator(func):
        if not settings.auth_rate_limit_enabled:
            return func
        return limiter.limit(limit)(func)

    return decorator
