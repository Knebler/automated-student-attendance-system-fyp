# platformissue_control.py
from application.entities2.user import UserModel
from application.entities2.platformissue import PlatformIssueModel
from application.entities2.institution import InstitutionModel
from database.base import get_session
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Common inappropriate words/phrases to filter (similar to testimonial)
PROFANITY_LIST = [
    'damn', 'hell', 'crap', 'shit', 'fuck', 'bitch', 'ass', 'bastard', 
    'dick', 'piss', 'cock', 'pussy', 'whore', 'slut', 'fag', 'nigger',
    'asshole', 'motherfucker', 'bullshit', 'goddamn', 'retard', 'idiot',
    'stupid', 'dumb', 'moron', 'imbecile', 'anal', 'arse', 'arsehole',
    'wth', 'wtf', 'stfu', 'gtfo', 'kys', 'kms', 'fk', 'fuk', 'fck',
    'sht', 'shyt', 'btch', 'cnt', 'cunt', 'twat', 'bollocks', 'wanker',
    'prick', 'douche', 'jackass', 'dipshit', 'dumbass', 'screw you'
]

# Minimum word count for serious issues
MIN_SERIOUS_WORD_COUNT = 10

class PlatformIssueControl:
    """Control class for platform issue/report business logic"""
    
    @staticmethod
    def analyze_issue_content(description, category=None):
        """
        Analyze issue content for appropriateness.
        
        Args:
            description: Issue description/content
            category: Issue category (optional)
            
        Returns:
            dict: {
                'is_appropriate': bool,
                'reason': str (if inappropriate),
                'contains_profanity': bool,
                'profanity_found': list,
                'word_count': int
            }
        """
        # Check word count
        word_count = len(description.split())
        if word_count < MIN_SERIOUS_WORD_COUNT:
            return {
                'is_appropriate': False,
                'reason': f'Issue description too short ({word_count} words). Please provide at least {MIN_SERIOUS_WORD_COUNT} words.',
                'contains_profanity': False,
                'profanity_found': [],
                'word_count': word_count,
                'is_too_short': True
            }
        
        # Convert to lowercase for checking
        text_lower = description.lower()
        
        # Check for profanity
        found_profanity = []
        for word in PROFANITY_LIST:
            import re
            # For short words/abbreviations
            if len(word) <= 4 and word.isalpha():
                pattern = r'(?:^|\s|[^\w])' + re.escape(word) + r'(?:$|\s|[^\w])'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_profanity.append(word)
            else:
                pattern = r'\b' + re.escape(word) + r'\b'
                if re.search(pattern, text_lower, re.IGNORECASE):
                    found_profanity.append(word)
        
        contains_profanity = len(found_profanity) > 0
        
        # Determine if issue is appropriate
        is_appropriate = True
        reason = None
        
        if contains_profanity:
            is_appropriate = False
            reason = f"Contains inappropriate language: {', '.join(found_profanity)}"
        
        return {
            'is_appropriate': is_appropriate,
            'reason': reason,
            'contains_profanity': contains_profanity,
            'profanity_found': found_profanity,
            'word_count': word_count,
            'is_too_short': word_count < MIN_SERIOUS_WORD_COUNT
        }
    
    @staticmethod
    def create_issue(app, user_id, institution_id, description, category="bug"):
        """
        Create a new platform issue/report.
        
        Args:
            app: Flask application instance
            user_id: ID of the user creating the issue
            institution_id: ID of the institution
            description: Issue description/content
            category: Issue category (default: "bug")
            
        Returns:
            dict: {'success': bool, 'message': str, 'issue_id': int or None}
        """
        try:
            # Validate inputs
            if not description or len(description.strip()) == 0:
                return {'success': False, 'error': 'Issue description is required'}
            
            with get_session() as session:
                # Verify user exists and belongs to the institution
                user_model = UserModel(session)
                user = user_model.get_by_id(user_id)
                if not user or getattr(user, 'institution_id') != institution_id:
                    return {'success': False, 'error': 'User not found or does not belong to this institution'}
                
                # Verify institution exists
                institution_model = InstitutionModel(session)
                institution = institution_model.get_by_id(institution_id)
                if not institution:
                    return {'success': False, 'error': 'Institution not found'}
                
                # Create the issue
                issue_model = PlatformIssueModel(session)
                issue = issue_model.create_issue(
                    user_id=user_id,
                    institution_id=institution_id,
                    description=description.strip(),
                    category=category
                )
                
                return {
                    'success': True,
                    'message': 'Issue reported successfully',
                    'issue_id': issue.issue_id
                }
                
        except Exception as e:
            logger.error(f"Error creating platform issue: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_issue_by_id(app, issue_id):
        """
        Get an issue by its ID.
        
        Args:
            app: Flask application instance
            issue_id: ID of the issue
            
        Returns:
            dict: {'success': bool, 'issue': dict or None, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                issue_data = issue_model.get_issue_with_details(issue_id)
                
                if not issue_data:
                    return {'success': False, 'error': 'Issue not found'}
                
                return {
                    'success': True,
                    'issue': issue_data
                }
                
        except Exception as e:
            logger.error(f"Error getting issue by ID: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_issues_by_user(app, user_id, include_deleted=False):
        """
        Get all issues reported by a specific user.
        
        Args:
            app: Flask application instance
            user_id: ID of the user
            include_deleted: Whether to include deleted issues
            
        Returns:
            dict: {'success': bool, 'issues': list, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                
                # Get user's issues
                if include_deleted:
                    issues = issue_model.get_by_user(user_id)
                else:
                    # Filter only active issues
                    all_issues = issue_model.get_by_user(user_id)
                    issues = [issue for issue in all_issues if issue.deleted_at is None]
                
                # Convert to dicts with additional info
                issue_list = []
                for issue in issues:
                    issue_dict = issue.as_dict()
                    issue_dict['is_active'] = issue.deleted_at is None
                    issue_list.append(issue_dict)
                
                return {
                    'success': True,
                    'issues': issue_list,
                    'count': len(issue_list)
                }
                
        except Exception as e:
            logger.error(f"Error getting issues by user: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_issues_by_institution(app, institution_id, include_deleted=False):
        """
        Get all issues from a specific institution.
        
        Args:
            app: Flask application instance
            institution_id: ID of the institution
            include_deleted: Whether to include deleted issues
            
        Returns:
            dict: {'success': bool, 'issues': list, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                
                # Get institution's issues
                if include_deleted:
                    issues = issue_model.get_by_institution(institution_id)
                else:
                    # Filter only active issues
                    all_issues = issue_model.get_by_institution(institution_id)
                    issues = [issue for issue in all_issues if issue.deleted_at is None]
                
                # Convert to dicts with additional info
                issue_list = []
                for issue in issues:
                    issue_dict = issue.as_dict()
                    issue_dict['is_active'] = issue.deleted_at is None
                    
                    # Add reporter info
                    if issue.reporter:
                        issue_dict['reporter_name'] = issue.reporter.name
                        issue_dict['reporter_role'] = issue.reporter.role
                    
                    issue_list.append(issue_dict)
                
                return {
                    'success': True,
                    'issues': issue_list,
                    'count': len(issue_list)
                }
                
        except Exception as e:
            logger.error(f"Error getting issues by institution: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_all_active_issues(app, category=None, page=1, per_page=10):
        """
        Get all active (not deleted) issues for platform managers.
        
        Args:
            app: Flask application instance
            category: Optional category filter
            page: Page number for pagination
            per_page: Items per page
            
        Returns:
            dict: {'success': bool, 'issues': list, 'pagination': dict, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                
                # Get paginated issues
                result = issue_model.get_paginated_issues(
                    page=page,
                    per_page=per_page,
                    include_deleted=False
                )
                
                # Apply category filter if specified
                if category:
                    filtered_items = [item for item in result['items'] if item['category'] == category]
                    # Recalculate pagination for filtered results
                    total_filtered = len([item for item in result['items'] if item['category'] == category])
                    
                    # Adjust pagination for filtered results
                    start_idx = (page - 1) * per_page
                    end_idx = min(start_idx + per_page, total_filtered)
                    paginated_items = filtered_items[start_idx:end_idx]
                    
                    result['items'] = paginated_items
                    result['total'] = total_filtered
                    result['pages'] = (total_filtered + per_page - 1) // per_page if total_filtered > 0 else 1
                
                return {
                    'success': True,
                    'issues': result['items'],
                    'pagination': {
                        'current_page': result['page'],
                        'total_pages': result['pages'],
                        'total_items': result['total'],
                        'per_page': result['per_page']
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting all active issues: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_recent_issues(app, limit=10):
        """
        Get recent active issues for dashboard display.
        
        Args:
            app: Flask application instance
            limit: Maximum number of issues to return
            
        Returns:
            dict: {'success': bool, 'issues': list, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                recent_issues = issue_model.get_recent_issues(limit=limit)
                
                return {
                    'success': True,
                    'issues': recent_issues,
                    'count': len(recent_issues)
                }
                
        except Exception as e:
            logger.error(f"Error getting recent issues: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_issue_statistics(app):
        """
        Get statistics about platform issues.
        
        Args:
            app: Flask application instance
            
        Returns:
            dict: {'success': bool, 'statistics': dict, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                
                # Get counts by category
                category_counts = issue_model.count_by_category()
                
                # Get total active issues
                total_active = issue_model.count_issues(include_deleted=False)
                
                # Get total issues (including deleted)
                total_all = issue_model.count_issues(include_deleted=True)
                
                return {
                    'success': True,
                    'statistics': {
                        'total_active': total_active,
                        'total_all': total_all,
                        'category_counts': category_counts,
                        'recent_count': min(10, total_active)  # Last 10 or less
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting issue statistics: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def mark_issue_as_deleted(app, issue_id, manager_id=None):
        """
        Mark an issue as deleted (hand over to dev team).
        
        Args:
            app: Flask application instance
            issue_id: ID of the issue to mark as deleted
            manager_id: Optional ID of the platform manager performing the action
            
        Returns:
            dict: {'success': bool, 'message': str, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                
                # Get the issue
                issue = issue_model.get_by_id(issue_id)
                if not issue:
                    return {'success': False, 'error': 'Issue not found'}
                
                # Check if already deleted
                if issue.deleted_at is not None:
                    return {'success': False, 'error': 'Issue is already marked as deleted'}
                
                # Mark as deleted
                success = issue_model.mark_as_deleted(issue_id)
                
                if not success:
                    return {'success': False, 'error': 'Failed to mark issue as deleted'}
                
                # Log the action (optional)
                if manager_id:
                    # Here you could add logic to log manager actions
                    pass
                
                return {
                    'success': True,
                    'message': 'Issue marked as deleted and handed over to development team'
                }
                
        except Exception as e:
            logger.error(f"Error marking issue as deleted: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def search_issues(app, search_term='', category=''):
        """
        Search issues by description text and/or category.
        
        Args:
            app: Flask application instance
            search_term: Text to search in issue descriptions
            category: Optional category filter
            
        Returns:
            dict: {'success': bool, 'issues': list, 'count': int, 'error': str or None}
        """
        try:
            with get_session() as session:
                issue_model = PlatformIssueModel(session)
                issues = issue_model.search_issues(
                    search_term=search_term,
                    category=category
                )
                
                return {
                    'success': True,
                    'issues': issues,
                    'count': len(issues)
                }
                
        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def get_categories():
        """
        Get list of valid issue categories.
        
        Returns:
            list: List of category strings
        """
        return [
            'bug',
            'feature_request',
            'ui_issue',
            'performance',
            'security',
            'data_issue',
            'account_issue',
            'billing',
            'other'
        ]
    
    @staticmethod
    def validate_category(category):
        """
        Validate if a category is valid.
        
        Args:
            category: Category to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        valid_categories = PlatformIssueControl.get_categories()
        return category in valid_categories