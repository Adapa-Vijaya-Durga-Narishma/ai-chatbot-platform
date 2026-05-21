"""
Authenticated StaticFiles implementation for uploaded files.
"""
from fastapi import status
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jose import JWTError

from app.services.auth_service import decode_access_token


class AuthenticatedStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope) -> Response:
        headers = dict(scope.get("headers") or [])
        cookie_bytes = headers.get(b"cookie", b"")
        cookie_header = cookie_bytes.decode("latin1") if cookie_bytes else ""

        access_token = None
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith("access_token="):
                access_token = part.split("=", 1)[1]
                break

        if not access_token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": {"error": "not_authenticated", "message": "Not authenticated"}},
            )

        try:
            decode_access_token(access_token)
        except (JWTError, ValueError):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": {"error": "invalid_token", "message": "Invalid or expired token"}},
            )

        return await super().get_response(path, scope)
