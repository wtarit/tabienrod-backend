from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.database import engine
    await engine.dispose()


app = FastAPI(title="Tabienrod Backend", lifespan=lifespan)
app.include_router(router)
