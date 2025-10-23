# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Azure OpenAI 配置
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_deployment_name: str
    azure_api_version: str

    # Azure OpenAI Embedding 配置
    azure_openai_embedding_endpoint: str = ""
    azure_openai_embedding_api_key: str = ""
    azure_openai_embedding_deployment: str = "text-embedding-3-small"
    azure_openai_embedding_api_version: str = "2024-02-01"

    # Azure AI Search 配置
    azure_search_endpoint: str
    azure_search_key: str
    azure_search_index_name: str = "documents-index"
    azure_search_api_version: str = "2023-11-01"

    # 向量配置
    embedding_dimension: int = 1536  # text-embedding-3-small 的维度

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
