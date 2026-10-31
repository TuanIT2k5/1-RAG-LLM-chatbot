from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Xác định đường dẫn gốc của phân hệ backend và thư mục gốc Monorepo
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Cấu hình trung tâm của hệ thống đọc tự động từ file .env."""

    model_config = SettingsConfigDict(
        env_file=(
            str(BACKEND_DIR / ".env"),
            str(ROOT_DIR / ".env"),
            str(BACKEND_DIR / ".env.example"),
            str(ROOT_DIR / ".env.example"),
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 1. Cấu hình chung hệ thống
    APP_NAME: str = Field(default="Intelligent Document Chatbot")
    APP_VERSION: str = Field(default="2.0.0")
    APP_ENV: str = Field(default="development")
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000, ge=1, le=65535)
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    )

    # 2. Cơ sở dữ liệu & Lưu trữ
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/doc_chatbot"
    )
    CHROMA_PERSIST_DIR: str = Field(default="./storage/chroma_db")
    UPLOAD_DIR: str = Field(default="./storage/uploads")
    MAX_FILE_SIZE_MB: int = Field(default=20, ge=1, le=100)

    # 3. Cấu hình Mô hình AI & RAG
    LLM_PROVIDER: str = Field(default="gemini")
    LLM_API_KEY: str = Field(default="your_api_key_here")
    LLM_MODEL: str = Field(default="gemini-2.5-flash")
    LLM_TEMPERATURE: float = Field(default=0.1, ge=0.0, le=2.0)

    EMBEDDING_MODEL: str = Field(default="BAAI/bge-m3")
    EMBEDDING_MODEL_NAME: str = Field(default="BAAI/bge-m3")

    # 4. Tham số luồng RAG Pipeline
    CHUNK_SIZE: int = Field(default=400, ge=50, le=4000)
    CHUNK_OVERLAP: int = Field(default=60, ge=0, le=1000)
    TOP_K: int = Field(default=5, ge=1, le=50)
    RETRIEVAL_TOP_K: int = Field(default=5, ge=1, le=50)

    @field_validator("LLM_PROVIDER")
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        allowed = {"gemini", "openai", "ollama"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"LLM_PROVIDER phải thuộc một trong các giá trị: {allowed}")
        return normalized

    @property
    def cors_origins_list(self) -> List[str]:
        """Chuyển chuỗi CORS_ORIGINS ngăn cách bằng dấu phẩy thành danh sách URL."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        """Dung lượng tệp tối đa tính theo byte."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Trả về đối tượng Settings dạng Singleton được lưu đệm."""
    return Settings()


settings = get_settings()

