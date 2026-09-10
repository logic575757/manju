from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from api import api_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="剧本创作 API",
        description="Script Creation Backend — FastAPI + MySQL",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    Base.metadata.create_all(bind=engine)

    app.include_router(api_router)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "service": "script-creation-api"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    from config import settings
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
