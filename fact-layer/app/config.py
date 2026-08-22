from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "nvidia/llama-3.3-nemotron-super-49b-v1"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    database_url: str = "sqlite:///./data/fact_layer.db"
    chroma_dir: str = "./data/chroma"
    upload_dir: str = "./data/uploads"
    processed_dir: str = "./data/processed"

    max_concurrent_extractions: int = 3
    extraction_timeout_seconds: int = 120
    chunk_max_tokens: int = 3000

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    ui_port: int = 8501
    extractor_type: str = "mock"

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def processed_path(self) -> Path:
        return Path(self.processed_dir)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_dir)


settings = Settings()