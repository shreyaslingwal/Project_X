"""Centralized application configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Server
    APP_NAME: str = "Project X - Local NotebookLM RAG"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = False

    # Ollama LLM Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    REWRITE_MODEL: str = "qwen3:4b"
    OLLAMA_TEMPERATURE: float = 0.2

    # Embeddings (Local CPU FastEmbed)
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # FlashRank Re-ranker (Local CPU)
    RERANKER_MODEL: str = "ms-marco-MiniLM-L-12-v2"

    # Retrieval Settings
    TOP_K_RETRIEVAL: int = 15
    TOP_K_RERANK: int = 4

    # Ingestion & Chunking Settings
    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100

    # Security & Upload Limits
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_PAGES_PER_PDF: int = 300
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".md", ".markdown"}
    ENABLE_MAGIC_BYTE_CHECK: bool = True

    # Conversational Memory & Query Rewriting
    MEMORY_WINDOW_TURNS: int = 5
    ENABLE_FAST_PATH_BYPASS: bool = False

    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    FAISS_INDEX_DIR: Path = BASE_DIR / "data" / "faiss_index"

    # Optional Cloud API Keys
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        """Ensure all required data directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    settings = Settings()
    settings.ensure_directories()
    return settings


settings = get_settings()
