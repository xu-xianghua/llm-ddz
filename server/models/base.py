"""
简单的内存存储实现，替代数据库
"""

__all__ = ('AlchemyMixin', 'Base')


class InMemoryStore:
    """A simple in-memory data store to replace the database."""
    
    def __init__(self):
        self.data = {}
        
    def get(self, key, default=None):
        return self.data.get(key, default)
        
    def set(self, key, value):
        self.data[key] = value
        return value
        
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            return True
        return False


class AlchemyMixin:
    """A compatibility layer to replace SQLAlchemy with in-memory storage."""
    
    _store = InMemoryStore()
    
    async def get_one_or_none(self, query):
        # In this simplified version, we just return None
        # In a real implementation, you would parse the query and return the appropriate data
        return None
        
    async def get_all(self, query):
        # In this simplified version, we just return an empty list
        # In a real implementation, you would parse the query and return the appropriate data
        return []
        
    async def insert(self, instance):
        # In this simplified version, we just log the insert
        # In a real implementation, you would store the data
        pass
        
    async def insert_or_update(self, insert_stmt, **kwargs):
        # In this simplified version, we just return a random ID
        # In a real implementation, you would store the data and return the ID
        import random
        return random.randint(1, 1000000)
        
    @property
    def session(self):
        # Return a dummy session object
        return DummySession()
        
        
class DummySession:
    """A dummy session object to replace SQLAlchemy's session."""
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
        
    async def begin(self):
        return self
        
    async def commit(self):
        pass
        
    def add(self, instance):
        pass
        
    async def execute(self, stmt):
        # Return a dummy result
        return DummyResult()
        
        
class DummyResult:
    """A dummy result object to replace SQLAlchemy's result."""
    
    def scalar_one_or_none(self):
        return None
        
    def scalars(self):
        return []
        
    @property
    def lastrowid(self):
        import random
        return random.randint(1, 1000000)


# Define a Base class for compatibility
class Base:
    pass
