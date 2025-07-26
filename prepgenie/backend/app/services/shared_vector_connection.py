"""
Shared Vector Database Connection Manager
Manages single connection to Milvus Lite to prevent file locking issues
"""
import logging
import os
import asyncio
from typing import Optional
from pymilvus import connections
from app.core.config import settings

logger = logging.getLogger(__name__)

class SharedVectorConnection:
    """Manages a single shared connection to prevent database file locking"""
    
    _instance = None
    _connected = False
    _connection_alias = "shared_milvus"
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    async def get_connection(cls) -> Optional[str]:
        """Get the shared connection alias, creating connection if needed"""
        instance = cls()
        
        async with cls._lock:
            if not cls._connected:
                await instance._create_connection()
            
            return cls._connection_alias if cls._connected else None
    
    async def _create_connection(self):
        """Create the shared connection"""
        try:
            # Check if vector service is disabled
            if getattr(settings, 'DISABLE_VECTOR_SERVICE', False):
                logger.info("Vector service disabled, skipping connection")
                return
            
            # Check environment
            environment = getattr(settings, 'ENVIRONMENT', 'production').lower()
            use_local = environment in ['local', 'development']
            
            # Disconnect existing connection if it exists
            try:
                connections.disconnect(self._connection_alias)
                logger.info(f"Disconnected existing connection: {self._connection_alias}")
            except Exception:
                pass  # Connection didn't exist, that's fine
            
            if use_local:
                # Use local Milvus Lite
                local_db_path = getattr(settings, 'MILVUS_LOCAL_PATH', './milvus_lite_local.db')
                connections.connect(
                    alias=self._connection_alias,
                    uri=os.path.abspath(local_db_path)
                )
                logger.info(f"✅ Shared connection created to Milvus Lite: {local_db_path}")
            else:
                # Use Zilliz Cloud
                if not settings.MILVUS_URI or not settings.MILVUS_TOKEN:
                    raise ValueError("MILVUS_URI and MILVUS_TOKEN required for production")
                
                connections.connect(
                    alias=self._connection_alias,
                    uri=settings.MILVUS_URI,
                    token=settings.MILVUS_TOKEN
                )
                logger.info("✅ Shared connection created to Zilliz Cloud")
            
            self.__class__._connected = True
            
        except Exception as e:
            logger.error(f"❌ Failed to create shared vector connection: {e}")
            self.__class__._connected = False
            raise
    
    @classmethod
    async def disconnect(cls):
        """Disconnect the shared connection"""
        async with cls._lock:
            if cls._connected:
                try:
                    connections.disconnect(cls._connection_alias)
                    cls._connected = False
                    logger.info("✅ Shared vector connection disconnected")
                except Exception as e:
                    logger.error(f"❌ Error disconnecting shared connection: {e}")

# Global shared connection manager
shared_connection = SharedVectorConnection()
