import time, uuid, logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
logger = logging.getLogger("agri")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())[:8]; start = time.time(); request.state.req_id = req_id
        response = await call_next(request)
        ms = round((time.time()-start)*1000,1)
        logger.info(f"[{req_id}] {request.method} {request.url.path} → {response.status_code} ({ms}ms)")
        response.headers["X-Request-ID"] = req_id; response.headers["X-Response-Time"] = f"{ms}ms"
        return response
