from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration class for the application."""
    openai_api_key: str = Field(..., description="OpenAI API Key")
    chroma_persist_dir: str = Field("./chroma_db", description="ChromaDB persistence directory")
    data_dir: str = Field("./data", description="Data directory containing PDF documents")
    log_level: str = Field("INFO", description="Logging level")
    
    # Caching
    enable_llm_cache: bool = Field(True, description="Enable LLM caching")
    cache_dir: str = Field(".cache", description="Directory for LLM cache")
    
    # RAG parameters
    chunk_size: int = Field(1000, description="Chunk size for document splitting")
    chunk_overlap: int = Field(200, description="Chunk overlap for document splitting")
    top_k: int = Field(25, description="Initial retrieval top K documents")
    rerank_top_k: int = Field(8, description="Post-reranking top K documents")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
