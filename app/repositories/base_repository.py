from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeMeta
from contextlib import contextmanager
from typing import TypeVar, Generic, Optional, List, Dict, Any, Generator
import logging

from app.models.database import Base
from app.config import config

logger = logging.getLogger(__name__)

# Create a TypeVar for the model type
ModelType = TypeVar('ModelType', bound=DeclarativeMeta)

# Single engine instance
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {},
    pool_pre_ping=True
)

# Single session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

class BaseRepository(Generic[ModelType]):
    """Simplified base repository with proper typing"""
    
    def __init__(self, model: type[ModelType]):
        self.model = model
    
    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """Get database session"""
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def create(self, **kwargs) -> ModelType:
        """Create a new record"""
        with self.get_db() as db:
            instance = self.model(**kwargs)
            db.add(instance)
            db.flush()
            db.refresh(instance)
            return instance
    
    def get(self, id: int) -> Optional[ModelType]:
        """Get by ID"""
        with self.get_db() as db:
            return db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        """Get all records with pagination"""
        with self.get_db() as db:
            return db.query(self.model).offset(offset).limit(limit).all()
    
    def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """Update a record"""
        with self.get_db() as db:
            instance = db.query(self.model).filter(self.model.id == id).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                db.flush()
                db.refresh(instance)
            return instance
    
    def delete(self, id: int) -> bool:
        """Delete a record"""
        with self.get_db() as db:
            instance = db.query(self.model).filter(self.model.id == id).first()
            if instance:
                db.delete(instance)
                return True
            return False
    
    def exists(self, id: int) -> bool:
        """Check if record exists"""
        with self.get_db() as db:
            return db.query(self.model).filter(self.model.id == id).count() > 0