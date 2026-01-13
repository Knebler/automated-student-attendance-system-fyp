from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import inspect

# Type variable for the model
ModelType = TypeVar("ModelType")

class BaseEntity(Generic[ModelType]):
    """
    Base entity class that provides CRUD operations for SQLAlchemy models.
    Takes a session and model class to perform database operations.
    """
    
    def __init__(self, session: Session, model: Type[ModelType]):
        """
        Initialize the entity with a database session and model class.
        
        Args:
            session: SQLAlchemy session for database operations
            model: SQLAlchemy model class to perform operations on
        """
        self.session = session
        self.model = model
    
    def create(self, **kwargs) -> ModelType:
        """
        Create a new record in the database.
        
        Args:
            **kwargs: Field values for the new record
            
        Returns:
            The created model instance
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def get_by_id(self, id: Any) -> Optional[ModelType]:
        """
        Retrieve a record by its primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            Model instance or None if not found
        """
        return self.session.query(self.model).get(id)
    
    def get_one(self, **filters) -> Optional[ModelType]:
        """
        Retrieve a single record matching the given filters.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            Model instance or None if not found
        """
        return self.session.query(self.model).filter_by(**filters).first()
    
    def get_all(self, **filters) -> List[ModelType]:
        """
        Retrieve all records matching the given filters.
        
        Args:
            **filters: Field-value pairs to filter by (optional)
            
        Returns:
            List of model instances
        """
        query = self.session.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        return query.all()
    
    def get_paginated(self, page: int = 1, per_page: int = 10, **filters) -> Dict[str, Any]:
        """
        Retrieve paginated records.
        
        Args:
            page: Page number (1-indexed)
            per_page: Number of records per page
            **filters: Field-value pairs to filter by
            
        Returns:
            Dictionary with items, total, page, per_page, and pages
        """
        query = self.session.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page
        }
    
    def update(self, id: Any, **kwargs) -> Optional[ModelType]:
        """
        Update a record by its primary key.
        
        Args:
            id: Primary key value
            **kwargs: Field-value pairs to update
            
        Returns:
            Updated model instance or None if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = self.get_by_id(id)
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                self.session.commit()
                self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def update_by_filter(self, filters: Dict[str, Any], **kwargs) -> int:
        """
        Update multiple records matching the given filters.
        
        Args:
            filters: Field-value pairs to filter by
            **kwargs: Field-value pairs to update
            
        Returns:
            Number of records updated
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            count = self.session.query(self.model).filter_by(**filters).update(kwargs)
            self.session.commit()
            return count
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def delete(self, id: Any) -> bool:
        """
        Delete a record by its primary key.
        
        Args:
            id: Primary key value
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = self.get_by_id(id)
            if instance:
                self.session.delete(instance)
                self.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def delete_by_filter(self, **filters) -> int:
        """
        Delete multiple records matching the given filters.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            Number of records deleted
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            count = self.session.query(self.model).filter_by(**filters).delete()
            self.session.commit()
            return count
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
    
    def exists(self, **filters) -> bool:
        """
        Check if a record exists matching the given filters.
        
        Args:
            **filters: Field-value pairs to filter by
            
        Returns:
            True if record exists, False otherwise
        """
        return self.session.query(self.model).filter_by(**filters).first() is not None
    
    def count(self, **filters) -> int:
        """
        Count records matching the given filters.
        
        Args:
            **filters: Field-value pairs to filter by (optional)
            
        Returns:
            Number of matching records
        """
        query = self.session.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        return query.count()
    
    def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in a single transaction.
        
        Args:
            items: List of dictionaries with field values
            
        Returns:
            List of created model instances
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instances = [self.model(**item) for item in items]
            self.session.bulk_save_objects(instances, return_defaults=True)
            self.session.commit()
            return instances
        except SQLAlchemyError as e:
            self.session.rollback()
            raise e
        
    @staticmethod
    def add_headers(headers: List[str], rows_from_db: List[List[Any]]) -> List[Dict[str, Any]]:
        return [dict(zip(headers, row)) for row in rows_from_db]
