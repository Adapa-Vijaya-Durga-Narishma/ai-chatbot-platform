from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ App
    APP_NAME: str = "amzur-ai-chat"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_EXPIRE_MINUTES: int = 480

    # ------------------------------------------------------------------ Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/amzur_chat"
    SQL_ALLOWED_TABLES: str = "users,chat_threads,chat_messages,attachments"
    SQL_QUERY_MAX_ROWS: int = 100

    # ------------------------------------------------------------------ LiteLLM proxy
    LITELLM_PROXY_URL: str = "https://litellm.amzur.com"
    LITELLM_API_KEY: str = ""  # Will fail on actual LLM calls if empty
    LLM_MODEL: str = "gemini/gemini-2.5-flash"
    LITELLM_EMBEDDING_MODEL: str = "text-embedding-3-large"
    IMAGE_GEN_MODEL: str = "gemini/imagen-4.0-fast-generate-001"
    ARXIV_MAX_RESULTS: int = 8
    RESEARCH_AGENT_MAX_ITERATIONS: int = 4
    RESEARCH_AGENT_TIMEOUT_SECONDS: int = 20

    # ------------------------------------------------------------------ MCP
    MCP_SERVER_ENABLED: bool = True
    MCP_SERVER_HOST: str = "127.0.0.1"
    MCP_SERVER_PORT: int = 8811

    # ------------------------------------------------------------------ Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"

    # ------------------------------------------------------------------ ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # ------------------------------------------------------------------ Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_JSON_FILE: Optional[str] = None

    # ------------------------------------------------------------------ File uploads
    MAX_UPLOAD_MB: int = 20
    DATAFRAME_MAX_UPLOAD_MB: int = 10
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_MIME_TYPES: str = (
        "image/jpeg,image/png,image/gif,image/webp,image/bmp,image/svg+xml,"
        "video/mp4,video/webm,video/ogg,text/plain,text/csv,text/tab-separated-values,"
        "application/csv,application/vnd.ms-excel,text/x-python,text/x-java-source,"
        "text/javascript,application/javascript,text/x-c,text/x-c++src,application/pdf,"
        "text/x-typescript,text/markdown,application/x-tex"
    )

    # ------------------------------------------------------------------ CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    def get_cors_origins(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024

    @property
    def dataframe_max_upload_bytes(self) -> int:
        return self.DATAFRAME_MAX_UPLOAD_MB * 1024 * 1024

    @property
    def allowed_mime_types(self) -> list[str]:
        return [mime.strip() for mime in self.ALLOWED_MIME_TYPES.split(",") if mime.strip()]

    @property
    def sql_allowed_tables(self) -> list[str]:
        return [table.strip() for table in self.SQL_ALLOWED_TABLES.split(",") if table.strip()]


settings = Settings()
