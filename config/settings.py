import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # LLM Configuration
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # MCP Configuration
    mcp_stock_data_url: str = "localhost:5001"
    mcp_technical_url: str = "localhost:5002"
    
    # Redis Configuration
    redis_url: Optional[str] = None
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Frontend Configuration
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"

settings = Settings()