from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from contextlib import contextmanager
from typing import TypeVar, Generic, Type, Optional, Generator, Any
import logging
import threading

from app.models.database import Base
from app.config import config

logger = logging.getLogger(__name__)

# Fix: Define TypeVar at module level (outside any expression)
T = TypeVar('T', bound=Base)

class BaseRepository(Generic[T]):
    """Base repository with common database operations"""
    
    # Class-level shared database resources
    _engine = None
    _session_factory = None
    _lock = threading.Lock()
    
    def __init__(self, model: Type[T]):
        self.model = model
        self._init_db()
    
    @classmethod
    def _init_db(cls):
        """Initialize database connection (singleton pattern)"""
        with cls._lock:
            if not cls._engine:
                # Configure SQLite for better concurrency
                cls._engine = create_engine(
                    config.DATABASE_URL,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 30  # 30 seconds timeout for locks
                    },
                    pool_pre_ping=True,  # Verify connections before use
                    pool_size=1,  # SQLite works best with single connection
                    max_overflow=0
                )
                
                # Use scoped_session for thread-local sessions
                session_factory = sessionmaker(
                    autocommit=False, 
                    autoflush=False, 
                    bind=cls._engine
                )
                cls._session_factory = scoped_session(session_factory)
                
                # Create tables if they don't exist
                Base.metadata.create_all(bind=cls._engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional scope for database operations"""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            # Remove session from registry
            self._session_factory.remove()
    
    def create(self, **kwargs) -> T:
        """Create a new record"""
        with self.get_session() as session:
            instance = self.model(**kwargs)
            session.add(instance)
            session.flush()
            # Ensure all attributes are loaded before session closes
            session.refresh(instance)
            # Create a detached copy with all data loaded
            # Access all attributes while in session
            instance_dict = {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
            session.expunge(instance)
            # Set attributes back to ensure they're available after detachment
            for key, value in instance_dict.items():
                setattr(instance, key, value)
            return instance
    
    def get_by_id(self, id: int) -> Optional[T]:
        """Get record by ID"""
        with self.get_session() as session:
            instance = session.query(self.model).filter(self.model.id == id).first()
            if instance:
                # Load all attributes before detaching
                instance_dict = {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
                session.expunge(instance)
                # Set attributes back
                for key, value in instance_dict.items():
                    setattr(instance, key, value)
            return instance
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """Update a record"""
        with self.get_session() as session:
            instance = session.query(self.model).filter(self.model.id == id).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
                # Load all attributes before detaching
                instance_dict = {c.name: getattr(instance, c.name) for c in instance.__table__.columns}
                session.expunge(instance)
                # Set attributes back
                for key, value in instance_dict.items():
                    setattr(instance, key, value)
            return instance