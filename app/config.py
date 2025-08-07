from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost/healthcare_db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Password hashing
    bcrypt_rounds: int = 12
    
    # API
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Healthcare Provider Registration API"
    
    class Config:
        env_file = ".env"


settings = Settings() 