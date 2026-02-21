"""Global exception handler middleware — standardized error responses."""

import logging
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


# --- Standard error codes ---
class ErrorCode:
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE = "DUPLICATE"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    AI_SERVICE_ERROR = "AI_SERVICE_ERROR"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    RATE_LIMITED = "RATE_LIMITED"


class ErrorResponse(BaseModel):
    detail: str
    error_code: str


# --- Map HTTP status codes to error codes ---
STATUS_TO_ERROR_CODE = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.DUPLICATE,
    413: ErrorCode.FILE_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_FORMAT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
    502: ErrorCode.AI_SERVICE_ERROR,
    503: ErrorCode.AI_SERVICE_ERROR,
}


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle all HTTPException with standardized format."""
        error_code = STATUS_TO_ERROR_CODE.get(exc.status_code, ErrorCode.INTERNAL_ERROR)

        # Log server errors
        if exc.status_code >= 500:
            logger.error(
                "HTTP %d at %s: %s",
                exc.status_code,
                request.url.path,
                exc.detail,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail or "Erreur inconnue",
                "error_code": error_code,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors with French messages."""
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = " → ".join(str(part) for part in first.get("loc", []) if part != "body")
            msg = first.get("msg", "Valeur invalide")
            detail = f"Erreur de validation : {loc} — {msg}" if loc else f"Erreur de validation : {msg}"
        else:
            detail = "Données invalides"

        logger.warning("Validation error at %s: %s", request.url.path, errors)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": detail,
                "error_code": ErrorCode.VALIDATION_ERROR,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions — no stack trace in prod."""
        logger.error(
            "Unhandled exception at %s: %s\n%s",
            request.url.path,
            str(exc),
            traceback.format_exc(),
        )

        detail = (
            f"Erreur interne : {exc}" if settings.environment == "development"
            else "Oups, quelque chose a mal tourné. Réessaie."
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": detail,
                "error_code": ErrorCode.INTERNAL_ERROR,
            },
        )
