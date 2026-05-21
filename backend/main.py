from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn

from app.core.authenticated_static import AuthenticatedStaticFiles
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

upload_dir = Path(settings.UPLOAD_DIR).resolve()
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", AuthenticatedStaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


# Routers
from app.api import auth, chat, dataframe_chat, research, sql_chat, tic_tac_toe

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(dataframe_chat.router, prefix="/api/dataframe-chat", tags=["dataframe-chat"])
app.include_router(sql_chat.router, prefix="/api/sql-chat", tags=["sql-chat"])
app.include_router(research.router, prefix="/api/research", tags=["research"])
app.include_router(tic_tac_toe.router, prefix="/api/tic-tac-toe", tags=["tic-tac-toe"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
