"""
MongoDB Connection Manager
Handles MongoDB connection with retry logic and health checks
"""

import os
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import (
    ConnectionFailure,
    ServerSelectionTimeoutError,
    ConfigurationError,
    OperationFailure
)
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class MongoDBConfig:
    """MongoDB configuration from environment variables"""

    def __init__(self):
        self.connection_string = os.getenv(
            "MONGODB_URI",
            "mongodb://localhost:27017"
        )
        self.database_name = os.getenv(
            "MONGODB_DATABASE",
            "zeno_db"
        )
        self.collection_name = os.getenv(
            "MONGODB_COLLECTION",
            "transcriptions"
        )
        self.connection_timeout_ms = int(os.getenv(
            "MONGODB_CONNECTION_TIMEOUT_MS",
            "5000"
        ))
        self.server_selection_timeout_ms = int(os.getenv(
            "MONGODB_SERVER_SELECTION_TIMEOUT_MS",
            "5000"
        ))
        self.max_pool_size = int(os.getenv(
            "MONGODB_MAX_POOL_SIZE",
            "10"
        ))
        self.min_pool_size = int(os.getenv(
            "MONGODB_MIN_POOL_SIZE",
            "1"
        ))

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "connection_string": self._mask_connection_string(self.connection_string),
            "database_name": self.database_name,
            "collection_name": self.collection_name,
            "connection_timeout_ms": self.connection_timeout_ms,
            "server_selection_timeout_ms": self.server_selection_timeout_ms,
            "max_pool_size": self.max_pool_size,
            "min_pool_size": self.min_pool_size
        }

    @staticmethod
    def _mask_connection_string(conn_str: str) -> str:
        """Mask sensitive parts of connection string for logging"""
        if "@" in conn_str:
            # Mask credentials
            parts = conn_str.split("@")
            return f"mongodb://***@{parts[-1]}"
        return conn_str


# ============================================================================
# MongoDB Connection Manager
# ============================================================================

class MongoDBConnectionManager:
    """
    MongoDB connection manager with connection pooling and retry logic
    """

    def __init__(self, config: Optional[MongoDBConfig] = None):
        """
        Initialize MongoDB connection manager

        Args:
            config: MongoDBConfig instance. If None, loads from environment.
        """
        self.config = config or MongoDBConfig()
        self._client: Optional[MongoClient] = None
        self._is_connected = False

        logger.info(f"MongoDB Configuration: {self.config.to_dict()}")

    @property
    def client(self) -> MongoClient:
        """
        Get MongoDB client, creating connection if needed

        Returns:
            MongoClient instance

        Raises:
            ConnectionFailure: If connection cannot be established
        """
        if self._client is None or not self._is_connected:
            self.connect()

        return self._client

    @property
    def database(self) -> Database:
        """
        Get MongoDB database

        Returns:
            Database instance
        """
        return self.client[self.config.database_name]

    @property
    def collection(self) -> Collection:
        """
        Get MongoDB collection for transcriptions

        Returns:
            Collection instance
        """
        return self.database[self.config.collection_name]

    def connect(self, max_retries: int = 3) -> None:
        """
        Establish connection to MongoDB with retry logic

        Args:
            max_retries: Maximum number of connection attempts

        Raises:
            ConnectionFailure: If all connection attempts fail
        """
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempting MongoDB connection (attempt {attempt}/{max_retries})...")

                # Create MongoClient with connection parameters
                self._client = MongoClient(
                    self.config.connection_string,
                    connectTimeoutMS=self.config.connection_timeout_ms,
                    serverSelectionTimeoutMS=self.config.server_selection_timeout_ms,
                    maxPoolSize=self.config.max_pool_size,
                    minPoolSize=self.config.min_pool_size,
                )

                # Test connection by pinging
                self._client.admin.command('ping')

                self._is_connected = True
                logger.info(f"Successfully connected to MongoDB: {self.config.database_name}")

                return

            except (ConnectionFailure, ServerSelectionTimeoutError, ConfigurationError) as e:
                last_error = e
                logger.error(f"Connection attempt {attempt} failed: {str(e)}")

                if attempt < max_retries:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} connection attempts failed")

        # All attempts failed
        raise ConnectionFailure(
            f"Failed to connect to MongoDB after {max_retries} attempts: {str(last_error)}"
        )

    def disconnect(self) -> None:
        """
        Close MongoDB connection
        """
        if self._client:
            try:
                self._client.close()
                self._is_connected = False
                logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {str(e)}")

    def health_check(self) -> Dict[str, Any]:
        """
        Check MongoDB connection health

        Returns:
            Dictionary with health check results
        """
        try:
            # Ping database
            start_time = time.time()
            result = self.client.admin.command('ping')
            response_time = (time.time() - start_time) * 1000  # Convert to ms

            # Get server info
            server_info = self.client.server_info()

            return {
                "status": "healthy",
                "connected": self._is_connected,
                "database": self.config.database_name,
                "collection": self.config.collection_name,
                "response_time_ms": round(response_time, 2),
                "mongodb_version": server_info.get("version", "unknown"),
                "ping_result": result
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }

    @contextmanager
    def get_session(self):
        """
        Context manager for MongoDB session (for transactions)

        Usage:
            with mongo_manager.get_session() as session:
                collection.insert_one({...}, session=session)
        """
        session = self.client.start_session()
        try:
            yield session
        finally:
            session.end_session()

    def get_collection(self, collection_name: Optional[str] = None) -> Collection:
        """
        Get a specific collection

        Args:
            collection_name: Collection name. If None, returns default collection.

        Returns:
            Collection instance
        """
        if collection_name:
            return self.database[collection_name]
        return self.collection

    def list_collections(self) -> list:
        """
        List all collections in the database

        Returns:
            List of collection names
        """
        try:
            return self.database.list_collection_names()
        except Exception as e:
            logger.error(f"Failed to list collections: {str(e)}")
            return []

    def drop_collection(self, collection_name: str) -> bool:
        """
        Drop a collection (use with caution!)

        Args:
            collection_name: Name of collection to drop

        Returns:
            True if successful, False otherwise
        """
        try:
            self.database.drop_collection(collection_name)
            logger.info(f"Dropped collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop collection {collection_name}: {str(e)}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get database statistics

        Returns:
            Dictionary with database stats
        """
        try:
            stats = self.database.command("dbStats")
            return {
                "database": stats.get("db"),
                "collections": stats.get("collections"),
                "views": stats.get("views"),
                "objects": stats.get("objects"),
                "avg_obj_size": stats.get("avgObjSize"),
                "data_size": stats.get("dataSize"),
                "storage_size": stats.get("storageSize"),
                "indexes": stats.get("indexes"),
                "index_size": stats.get("indexSize")
            }
        except Exception as e:
            logger.error(f"Failed to get database stats: {str(e)}")
            return {}

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


# ============================================================================
# Global Connection Manager Instance
# ============================================================================

# Global instance (singleton pattern)
_global_mongo_manager: Optional[MongoDBConnectionManager] = None


def get_mongo_manager() -> MongoDBConnectionManager:
    """
    Get or create global MongoDB connection manager instance

    Returns:
        MongoDBConnectionManager instance
    """
    global _global_mongo_manager

    if _global_mongo_manager is None:
        _global_mongo_manager = MongoDBConnectionManager()
        _global_mongo_manager.connect()

    return _global_mongo_manager


def close_mongo_connection() -> None:
    """
    Close global MongoDB connection
    """
    global _global_mongo_manager

    if _global_mongo_manager:
        _global_mongo_manager.disconnect()
        _global_mongo_manager = None


# ============================================================================
# Example Usage
# ============================================================================

"""
# Example 1: Basic usage
from backend.database.mongodb import MongoDBConnectionManager

manager = MongoDBConnectionManager()
manager.connect()

# Get collection
collection = manager.collection

# Insert document
collection.insert_one({"name": "test", "value": 123})

# Health check
health = manager.health_check()
print(health)

# Disconnect
manager.disconnect()

# Example 2: Using context manager
with MongoDBConnectionManager() as manager:
    collection = manager.collection
    collection.insert_one({"test": "data"})
    # Automatically disconnects when exiting context

# Example 3: Using global instance (recommended for FastAPI)
from backend.database.mongodb import get_mongo_manager

manager = get_mongo_manager()
collection = manager.collection
result = collection.find_one({"_id": "some_id"})

# Example 4: Health check endpoint
@app.get("/health/mongodb")
async def mongodb_health():
    manager = get_mongo_manager()
    return manager.health_check()

# Example 5: Custom configuration
from backend.database.mongodb import MongoDBConfig, MongoDBConnectionManager

config = MongoDBConfig()
config.connection_string = "mongodb://custom:27017"
config.database_name = "my_db"

manager = MongoDBConnectionManager(config)
manager.connect()
"""
