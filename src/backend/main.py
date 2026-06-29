from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.accounts import router as accounts_router
from api.auth import router as auth_router
from api.flags import router as flags_router
from api.forecast import router as forecast_router
from api.imports import router as imports_router
from api.loans import router as loans_router
from api.spend import router as spend_router
from core.limiter import limiter

app = FastAPI(title="Finance App API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth_router, prefix="/api")
app.include_router(imports_router, prefix="/api")
app.include_router(accounts_router, prefix="/api")
app.include_router(loans_router, prefix="/api")
app.include_router(spend_router, prefix="/api")
app.include_router(flags_router, prefix="/api")
app.include_router(forecast_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
