from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration class for the application.
    
    Attributes:
        openai_api_key (str): OpenAI API Key
        chroma_persist_dir (str): ChromaDB persistence directory
        data_dir (str): Data directory containing PDF documents
        log_level (str): Logging level
        enable_llm_cache (bool): Enable LLM caching
        cache_dir (str): Directory for LLM cache
        chunk_size (int): Chunk size for document splitting
        chunk_overlap (int): Chunk overlap for document splitting
        top_k (int): Initial retrieval top K documents
        rerank_top_k (int): Post-reranking top K documents
        langchain_tracing_v2 (bool): Enable LangSmith tracing
        langchain_api_key (str | None): LangSmith API Key
        langchain_project (str): LangSmith Project Name
    """
    openai_api_key: str = Field(default="", description="OpenAI API Key")
    chroma_persist_dir: str = Field(default="./chroma_db", description="ChromaDB persistence directory")
    data_dir: str = Field(default="./data", description="Data directory containing PDF documents")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # LangSmith Tracing
    langchain_tracing_v2: bool = Field(default=False, description="Enable LangSmith tracing")
    langchain_api_key: str | None = Field(default=None, description="LangSmith API Key")
    langchain_project: str = Field(default="heart-speaks", description="LangSmith Project Name")
    
    # Caching
    enable_llm_cache: bool = Field(default=True, description="Enable LLM caching")
    cache_dir: str = Field(default=".cache", description="Directory for LLM cache")
    
    # RAG parameters
    chunk_size: int = Field(default=1000, description="Chunk size for document splitting")
    chunk_overlap: int = Field(default=200, description="Chunk overlap for document splitting")
    top_k: int = Field(default=25, description="Initial retrieval top K documents")
    rerank_top_k: int = Field(default=8, description="Post-reranking top K documents")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

if settings.langchain_tracing_v2 and settings.langchain_api_key:
    import os
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
