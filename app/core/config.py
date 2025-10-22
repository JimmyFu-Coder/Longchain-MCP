# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_deployment_name: str
    azure_api_version: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
