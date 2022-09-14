from fastapi import FastAPI
from time import sleep
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine

from starlette.requests import Request
from starlette.responses import JSONResponse

from api.router import router as api_router
from api.schemas.error import ErrorResult
from config import get_settings
from database.engine import create_db

import databases
import uvicorn

settings = get_settings()
database = databases.Database(settings.DATABASE_URL)


def get_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        debug=settings.DEBUG,
        version=settings.VERSION
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS or ['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    application.include_router(router=api_router, prefix=settings.API_PREFIX)

    @application.exception_handler(HTTPException)
    def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResult(code=exc.status_code,
                                message=exc.detail).dict(),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        return JSONResponse(
            status_code=400,
            content=ErrorResult(code=400,
                                message='Validation Failed').dict(),
        )

    return application


app = get_application()


@app.on_event("startup")
async def on_startup():
    create_db()


if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=80, reload=True, debug=settings.DEBUG)
