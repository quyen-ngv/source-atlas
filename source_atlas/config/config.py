import os
from typing import List

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Configs(BaseSettings):

    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "axonion")

    # data dir
    DATA_DIR: str = os.getenv(
        "DATA_DIR",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"),
    )

    # date
    DATETIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S"
    DATE_FORMAT: str = "%Y-%m-%d"

    @property
    def DATABASE_URI(self) -> str:
        """Build database URI only if password is provided."""
        if self.DB_PASSWORD:
            return self.DATABASE_URI_FORMAT.format(
                db_engine=self.DB_ENGINE,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT,
                database=self.DB_DATABASE,
            )
        return ""
    
    # Neo4j (Required)
    APP_NEO4J_URL: str = os.getenv("APP_NEO4J_URL", "bolt://localhost:7687")
    APP_NEO4J_USER: str = os.getenv("APP_NEO4J_USER", "neo4j")
    APP_NEO4J_PASSWORD: str = os.getenv("APP_NEO4J_PASSWORD", "")  # No default password
    APP_NEO4J_DATABASE: str = os.getenv("APP_NEO4J_DATABASE", "neo4j")
    
    def validate_neo4j_config(self) -> None:
        """Validate that required Neo4j configuration is present."""
        if not self.APP_NEO4J_PASSWORD:
            raise ValueError(
                "APP_NEO4J_PASSWORD environment variable is required. "
                "Please set it in your .env file or environment."
            )
        if not self.APP_NEO4J_URL:
            raise ValueError("APP_NEO4J_URL environment variable is required.")
        if not self.APP_NEO4J_USER:
            raise ValueError("APP_NEO4J_USER environment variable is required.")
    NEO4J_MAX_CONNECTION_LIFETIME: int = int(os.getenv("NEO4J_MAX_CONNECTION_LIFETIME", "30"))
    NEO4J_MAX_CONNECTION_POOL_SIZE: int = int(os.getenv("NEO4J_MAX_CONNECTION_POOL_SIZE", "50"))
    NEO4J_CONNECTION_TIMEOUT: float = float(os.getenv("NEO4J_CONNECTION_TIMEOUT", "30.0"))

    class Config:
        case_sensitive = True


configs = Configs()
