from .base_entity import BaseEntity
from database.models import *
from datetime import datetime
from sqlalchemy import func, desc

class PlatformIssueModel(BaseEntity[PlatformIssue]):
    """Entity for PlatformIssue model with custom methods"""
    
    def __init__(self, session):
        super().__init__(session, PlatformIssue)

    def get_by_user(self, user_id) -> list[PlatformIssue]:
        """Get all reports by a specific user"""
        return self.session.query(PlatformIssue).filter(
            PlatformIssue.user_id == user_id
        ).order_by(desc(PlatformIssue.created_at)).all()

    def get_by_institution(self, institution_id) -> list[PlatformIssue]:
        """Get all reports from a specific institution"""
        return self.session.query(PlatformIssue).filter(
            PlatformIssue.institution_id == institution_id
        ).order_by(desc(PlatformIssue.created_at)).all()

    def get_active_issues(self) -> list[PlatformIssue]:
        """Get all active (not deleted) issues"""
        return self.session.query(PlatformIssue).filter(
            PlatformIssue.deleted_at.is_(None)
        ).order_by(desc(PlatformIssue.created_at)).all()

    def get_deleted_issues(self) -> list[PlatformIssue]:
        """Get all deleted issues (handed to dev team)"""
        return self.session.query(PlatformIssue).filter(
            PlatformIssue.deleted_at.isnot(None)
        ).order_by(desc(PlatformIssue.deleted_at)).all()

    def get_by_category(self, category: str) -> list[PlatformIssue]:
        """Get all issues by category"""
        return self.session.query(PlatformIssue).filter(
            PlatformIssue.category == category,
            PlatformIssue.deleted_at.is_(None)  # Only active issues
        ).order_by(desc(PlatformIssue.created_at)).all()

    def mark_as_deleted(self, issue_id: int) -> bool:
        """Mark an issue as deleted (hand to dev team)"""
        issue = self.get_by_id(issue_id)
        if issue and issue.deleted_at is None:  # Only if not already deleted
            issue.deleted_at = datetime.now()
            self.session.commit()
            return True
        return False

    def create_issue(self, user_id: int, institution_id: int, 
                    description: str, category: str) -> PlatformIssue:
        """Create a new platform issue report"""
        issue = PlatformIssue(
            user_id=user_id,
            institution_id=institution_id,
            description=description,
            category=category
        )
        self.session.add(issue)
        self.session.commit()
        self.session.refresh(issue)
        return issue

    def get_issue_with_details(self, issue_id: int) -> dict:
        """Get issue with reporter and institution details"""
        issue = self.get_by_id(issue_id)
        if not issue:
            return None
        
        return {
            'issue': issue.as_dict(),
            'reporter_name': issue.reporter.name if issue.reporter else None,
            'reporter_role': issue.reporter.role if issue.reporter else None,
            'institution_name': issue.institution.name if issue.institution else None,
            'is_active': issue.deleted_at is None
        }

    def get_recent_issues(self, limit: int = 10) -> list[dict]:
        """Get recent active issues with details"""
        issues = self.session.query(PlatformIssue).filter(
            PlatformIssue.deleted_at.is_(None)
        ).order_by(desc(PlatformIssue.created_at)).limit(limit).all()
        
        result = []
        for issue in issues:
            result.append({
                'issue_id': issue.issue_id,
                'user_id': issue.user_id,
                'institution_id': issue.institution_id,
                'description': issue.description[:100] + '...' if len(issue.description) > 100 else issue.description,
                'category': issue.category,
                'created_at': issue.created_at,
                'reporter_name': issue.reporter.name if issue.reporter else 'Unknown',
                'institution_name': issue.institution.name if issue.institution else 'Unknown'
            })
        
        return result

    def count_by_category(self) -> dict:
        """Count active issues by category"""
        results = self.session.query(
            PlatformIssue.category,
            func.count(PlatformIssue.issue_id)
        ).filter(
            PlatformIssue.deleted_at.is_(None)
        ).group_by(PlatformIssue.category).all()
        
        return dict(results)

    def count_issues(self, include_deleted: bool = False) -> int:
        """Count total issues, optionally including deleted ones"""
        query = self.session.query(func.count(PlatformIssue.issue_id))
        if not include_deleted:
            query = query.filter(PlatformIssue.deleted_at.is_(None))
        return query.scalar()

    def get_paginated_issues(self, page: int = 1, per_page: int = 10, 
                           include_deleted: bool = False) -> dict:
        """Get paginated list of issues"""
        query = self.session.query(PlatformIssue)
        if not include_deleted:
            query = query.filter(PlatformIssue.deleted_at.is_(None))
        
        total = query.count()
        issues = query.order_by(desc(PlatformIssue.created_at))\
                     .offset((page - 1) * per_page)\
                     .limit(per_page)\
                     .all()
        
        # Format issues with basic details
        items = []
        for issue in issues:
            items.append({
                'issue_id': issue.issue_id,
                'user_id': issue.user_id,
                'institution_id': issue.institution_id,
                'description_preview': issue.description[:150] + '...' if len(issue.description) > 150 else issue.description,
                'category': issue.category,
                'created_at': issue.created_at,
                'deleted_at': issue.deleted_at,
                'is_active': issue.deleted_at is None,
                'reporter_name': issue.reporter.name if issue.reporter else None,
                'institution_name': issue.institution.name if issue.institution else None
            })
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 1
        }

    def search_issues(self, search_term: str = '', category: str = '') -> list[dict]:
        """Search issues by description text and/or category"""
        query = self.session.query(PlatformIssue).filter(
            PlatformIssue.deleted_at.is_(None)  # Only active issues
        )
        
        if search_term:
            query = query.filter(PlatformIssue.description.ilike(f'%{search_term}%'))
        
        if category:
            query = query.filter(PlatformIssue.category == category)
        
        issues = query.order_by(desc(PlatformIssue.created_at)).all()
        
        result = []
        for issue in issues:
            result.append({
                'issue_id': issue.issue_id,
                'description': issue.description,
                'description_preview': issue.description[:100] + '...' if len(issue.description) > 100 else issue.description,
                'category': issue.category,
                'created_at': issue.created_at,
                'reporter_name': issue.reporter.name if issue.reporter else 'Unknown',
                'institution_name': issue.institution.name if issue.institution else 'Unknown'
            })
        
        return result