from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.db import close_database, create_database, initialize_database


def create_app(database_url: str | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or (
        get_settings() if database_url is None else Settings(database_url=database_url)
    )
    engine, session_factory = create_database(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await initialize_database(engine)
        app.state.settings = settings
        app.state.session_factory = session_factory
        yield
        await close_database(engine)

    app = FastAPI(title="Qlik Data Flow API", version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
