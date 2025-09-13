from pydantic_settings import BaseSettings
from pydantic import Field

class Config(BaseSettings):
    # Neo4j
    APP_NEO4J_URL: str = Field(default="bolt://localhost:7687", env="APP_NEO4J_URL")
    APP_NEO4J_USER: str = Field(default="neo4j", env="APP_NEO4J_USER")
    APP_NEO4J_PASSWORD: str = Field(default="your_password", env="APP_NEO4J_PASSWORD")
    APP_NEO4J_DATABASE: str = Field(default="neo4j", env="APP_NEO4J_DATABASE")
    NEO4J_MAX_CONNECTION_LIFETIME: int = Field(default=30, env="NEO4J_MAX_CONNECTION_LIFETIME")
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = Field(default=50, env="NEO4J_MAX_CONNECTION_POOL_SIZE")
    NEO4J_CONNECTION_TIMEOUT: float = Field(default=30.0, env="NEO4J_CONNECTION_TIMEOUT")

    class Config:
        env_file = ".env"

config = Config()