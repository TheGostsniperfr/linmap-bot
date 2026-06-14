from fastapi import FastAPI
from src.api.routers import roadmap

def create_app() -> FastAPI:
    app = FastAPI(
        title="Linmap API",
        description="Core engine for Linear roadmap extraction and report generation",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    @app.get("/health", tags=["Diagnostic"])
    async def health_check():
        """Verifies the API is online and responsive."""
        return {"status": "healthy", "version": "1.0.0"}

    # Include routers
    app.include_router(roadmap.router, prefix="/api/v1")

    return app

app = create_app()
