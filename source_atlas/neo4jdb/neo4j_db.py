from neo4j import GraphDatabase
from source_atlas.config.config import configs


class Neo4jDB:
    def __init__(
        self, 
        url: str = None,
        user: str = None,
        password: str = None,
        max_connection_lifetime: int = None,
        max_connection_pool_size: int = None,
        connection_timeout: int = None
    ):
        """
        Initialize Neo4j database connection.
        
        Args:
            url: Neo4j connection URL (e.g., 'bolt://localhost:7687')
            user: Neo4j username
            password: Neo4j password
            max_connection_lifetime: Max connection lifetime in seconds
            max_connection_pool_size: Max connection pool size
            connection_timeout: Connection timeout in seconds
            
        If parameters are None, they will be loaded from configs.
        """
        self.driver = GraphDatabase.driver(
            url or configs.APP_NEO4J_URL,
            auth=(user or configs.APP_NEO4J_USER, password or configs.APP_NEO4J_PASSWORD),
            max_connection_lifetime=max_connection_lifetime or configs.NEO4J_MAX_CONNECTION_LIFETIME,
            max_connection_pool_size=max_connection_pool_size or configs.NEO4J_MAX_CONNECTION_POOL_SIZE,
            connection_timeout=connection_timeout or configs.NEO4J_CONNECTION_TIMEOUT
        )

    def close(self):
        self.driver.close()


