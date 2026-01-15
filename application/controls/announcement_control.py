from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any
from database.base import get_session
from application.entities2.announcement import AnnouncementModel
from application.entities2.user import UserModel
from application.entities2.institution import InstitutionModel

class AnnouncementControl:
    """Control class for announcement business logic using ORM"""
    
    @staticmethod
    def create_announcement(app, institution_id: int, requested_by_user_id: int, 
                           title: str, content: str) -> Dict[str, Any]:
        """Create a new announcement"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                
                # Verify the user exists and belongs to the institution
                user = user_model.get_by_id(requested_by_user_id)
                if not user:
                    return {'success': False, 'error': 'User not found'}
                
                if user.institution_id != institution_id:
                    return {'success': False, 'error': 'User does not belong to this institution'}
                
                # Create the announcement
                announcement = announcement_model.create_announcement(
                    institution_id=institution_id,
                    requested_by_user_id=requested_by_user_id,
                    title=title,
                    content=content
                )
                
                # Prepare response
                formatted_announcement = {
                    'announcement_id': announcement.announcement_id,
                    'title': announcement.title,
                    'content': announcement.content,
                    'date_posted': announcement.date_posted.isoformat() if announcement.date_posted else None,
                    'requested_by_user_id': announcement.requested_by_user_id,
                    'requested_by_name': user.name
                }
                
                return {
                    'success': True,
                    'announcement': formatted_announcement,
                    'message': 'Announcement created successfully'
                }
                
        except Exception as e:
            app.logger.error(f"Error creating announcement: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_announcements(app, institution_id: int, limit: Optional[int] = None, 
                         offset: Optional[int] = None, 
                         search_term: Optional[str] = None) -> Dict[str, Any]:
        """Get announcements for an institution with optional filtering"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                
                # Get announcements
                if search_term:
                    announcements = announcement_model.search_announcements(
                        institution_id, search_term
                    )
                else:
                    announcements = announcement_model.get_by_institution(institution_id)
                
                # Apply pagination
                total_count = len(announcements)
                if limit is not None:
                    if offset is None:
                        offset = 0
                    announcements = announcements[offset:offset + limit]
                
                # Format announcements with user info
                formatted_announcements = []
                for announcement in announcements:
                    user = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                    
                    formatted_announcements.append({
                        'announcement_id': announcement.announcement_id,
                        'title': announcement.title,
                        'content': announcement.content,
                        'excerpt': announcement.content[:100] + '...' if len(announcement.content) > 100 else announcement.content,
                        'date_posted': announcement.date_posted.isoformat() if announcement.date_posted else None,
                        'date_posted_display': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                        'requested_by_user_id': announcement.requested_by_user_id,
                        'requested_by_name': user.name if user else 'Unknown',
                        'requested_by_role': user.role if user else 'Unknown'
                    })
                
                # Sort by date (most recent first)
                formatted_announcements.sort(key=lambda x: x['date_posted'] or '', reverse=True)
                
                return {
                    'success': True,
                    'announcements': formatted_announcements,
                    'pagination': {
                        'total': total_count,
                        'limit': limit,
                        'offset': offset,
                        'has_more': offset + len(formatted_announcements) < total_count if offset is not None and limit is not None else False
                    }
                }
                
        except Exception as e:
            app.logger.error(f"Error getting announcements: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_recent_announcements(app, institution_id: int, limit: int = 5) -> Dict[str, Any]:
        """Get recent announcements for an institution"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                
                # Get recent announcements
                announcements = announcement_model.get_recent_announcements(institution_id, limit)
                
                # Format announcements
                formatted_announcements = []
                for announcement in announcements:
                    user = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                    
                    formatted_announcements.append({
                        'announcement_id': announcement.announcement_id,
                        'title': announcement.title,
                        'content': announcement.content,
                        'excerpt': announcement.content[:150] + '...' if len(announcement.content) > 150 else announcement.content,
                        'date_posted': announcement.date_posted.isoformat() if announcement.date_posted else None,
                        'date_posted_display': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                        'requested_by_user_id': announcement.requested_by_user_id,
                        'requested_by_name': user.name if user else 'Unknown',
                        'days_ago': (datetime.now().date() - announcement.date_posted.date()).days if announcement.date_posted else None
                    })
                
                return {
                    'success': True,
                    'announcements': formatted_announcements,
                    'count': len(formatted_announcements)
                }
                
        except Exception as e:
            app.logger.error(f"Error getting recent announcements: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_announcement_by_id(app, announcement_id: int, institution_id: Optional[int] = None) -> Dict[str, Any]:
        """Get a specific announcement by ID"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                institution_model = InstitutionModel(db_session)
                
                # Get the announcement
                announcement = announcement_model.get_by_id(announcement_id)
                if not announcement:
                    return {'success': False, 'error': 'Announcement not found'}
                
                # Verify institution access if specified
                if institution_id and announcement.institution_id != institution_id:
                    return {'success': False, 'error': 'Announcement does not belong to this institution'}
                
                # Get user info
                user = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                
                # Get institution info
                institution = institution_model.get_by_id(announcement.institution_id) if announcement.institution_id else None
                
                # Format announcement
                formatted_announcement = {
                    'announcement_id': announcement.announcement_id,
                    'title': announcement.title,
                    'content': announcement.content,
                    'date_posted': announcement.date_posted.isoformat() if announcement.date_posted else None,
                    'date_posted_display': announcement.date_posted.strftime('%B %d, %Y at %I:%M %p') if announcement.date_posted else 'N/A',
                    'requested_by_user_id': announcement.requested_by_user_id,
                    'requested_by_name': user.name if user else 'Unknown',
                    'requested_by_email': user.email if user else 'Unknown',
                    'requested_by_role': user.role if user else 'Unknown',
                    'institution_id': announcement.institution_id,
                    'institution_name': institution.name if institution else 'Unknown'
                }
                
                return {
                    'success': True,
                    'announcement': formatted_announcement
                }
                
        except Exception as e:
            app.logger.error(f"Error getting announcement by ID: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def update_announcement(app, announcement_id: int, title: Optional[str] = None, 
                           content: Optional[str] = None) -> Dict[str, Any]:
        """Update an existing announcement"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                
                # Get the announcement
                announcement = announcement_model.get_by_id(announcement_id)
                if not announcement:
                    return {'success': False, 'error': 'Announcement not found'}
                
                # Prepare update data
                update_data = {}
                if title is not None:
                    update_data['title'] = title
                if content is not None:
                    update_data['content'] = content
                
                # Update announcement
                updated_announcement = announcement_model.update(announcement_id, **update_data)
                
                if updated_announcement:
                    return {
                        'success': True,
                        'announcement': {
                            'announcement_id': updated_announcement.announcement_id,
                            'title': updated_announcement.title,
                            'content': updated_announcement.content
                        },
                        'message': 'Announcement updated successfully'
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to update announcement'
                    }
                
        except Exception as e:
            app.logger.error(f"Error updating announcement: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def delete_announcement(app, announcement_id: int) -> Dict[str, Any]:
        """Delete an announcement"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                
                # Get the announcement first to return info about what was deleted
                announcement = announcement_model.get_by_id(announcement_id)
                if not announcement:
                    return {'success': False, 'error': 'Announcement not found'}
                
                # Delete announcement
                deleted = announcement_model.delete(announcement_id)
                
                if deleted:
                    return {
                        'success': True,
                        'message': 'Announcement deleted successfully',
                        'deleted_announcement': {
                            'announcement_id': announcement.announcement_id,
                            'title': announcement.title
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to delete announcement'
                    }
                
        except Exception as e:
            app.logger.error(f"Error deleting announcement: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_announcement_statistics(app, institution_id: int, 
                                   start_date: Optional[date] = None, 
                                   end_date: Optional[date] = None) -> Dict[str, Any]:
        """Get statistics about announcements"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                
                # Set default date range if not provided
                if not end_date:
                    end_date = date.today()
                if not start_date:
                    start_date = end_date - timedelta(days=30)  # Last 30 days by default
                
                # Get all announcements for the institution
                announcements = announcement_model.get_by_institution(institution_id)
                
                # Filter by date range
                filtered_announcements = []
                for announcement in announcements:
                    if announcement.date_posted:
                        announcement_date = announcement.date_posted.date()
                        if start_date <= announcement_date <= end_date:
                            filtered_announcements.append(announcement)
                
                # Calculate statistics
                total_announcements = len(filtered_announcements)
                
                # Group by user
                announcements_by_user = {}
                for announcement in filtered_announcements:
                    user_id = announcement.requested_by_user_id
                    if user_id not in announcements_by_user:
                        user = user_model.get_by_id(user_id) if user_id else None
                        announcements_by_user[user_id] = {
                            'user_id': user_id,
                            'user_name': user.name if user else 'Unknown',
                            'user_role': user.role if user else 'Unknown',
                            'count': 0
                        }
                    announcements_by_user[user_id]['count'] += 1
                
                # Group by month
                announcements_by_month = {}
                for announcement in filtered_announcements:
                    if announcement.date_posted:
                        month_key = announcement.date_posted.strftime('%Y-%m')
                        if month_key not in announcements_by_month:
                            announcements_by_month[month_key] = {
                                'month': month_key,
                                'month_display': announcement.date_posted.strftime('%B %Y'),
                                'count': 0
                            }
                        announcements_by_month[month_key]['count'] += 1
                
                # Calculate average announcements per week
                weeks_in_range = max(1, (end_date - start_date).days // 7)
                avg_per_week = total_announcements / weeks_in_range if weeks_in_range > 0 else 0
                
                # Get top users
                top_users = sorted(
                    announcements_by_user.values(),
                    key=lambda x: x['count'],
                    reverse=True
                )[:5]  # Top 5 users
                
                # Get monthly trends
                monthly_trends = sorted(
                    announcements_by_month.values(),
                    key=lambda x: x['month']
                )
                
                return {
                    'success': True,
                    'statistics': {
                        'total_announcements': total_announcements,
                        'date_range': {
                            'start_date': start_date.isoformat(),
                            'end_date': end_date.isoformat(),
                            'days': (end_date - start_date).days
                        },
                        'average_per_week': round(avg_per_week, 2),
                        'top_users': top_users,
                        'monthly_trends': monthly_trends,
                        'daily_average': round(total_announcements / max(1, (end_date - start_date).days), 2)
                    }
                }
                
        except Exception as e:
            app.logger.error(f"Error getting announcement statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def search_announcements_full(app, institution_id: int, search_term: str, 
                                 limit: Optional[int] = 20) -> Dict[str, Any]:
        """Search announcements by title and content with enhanced results"""
        try:
            with get_session() as db_session:
                announcement_model = AnnouncementModel(db_session)
                user_model = UserModel(db_session)
                
                # Search announcements
                announcements = announcement_model.search_announcements(institution_id, search_term)
                
                if limit:
                    announcements = announcements[:limit]
                
                # Format results with relevance highlighting
                formatted_results = []
                for announcement in announcements:
                    user = user_model.get_by_id(announcement.requested_by_user_id) if announcement.requested_by_user_id else None
                    
                    # Create excerpt with search term highlighted (simple version)
                    content_excerpt = announcement.content
                    if len(announcement.content) > 200:
                        # Try to find search term in content
                        search_lower = search_term.lower()
                        content_lower = announcement.content.lower()
                        pos = content_lower.find(search_lower)
                        
                        if pos >= 0:
                            start = max(0, pos - 50)
                            end = min(len(announcement.content), pos + len(search_term) + 50)
                            content_excerpt = announcement.content[start:end]
                            if start > 0:
                                content_excerpt = '...' + content_excerpt
                            if end < len(announcement.content):
                                content_excerpt = content_excerpt + '...'
                    
                    formatted_results.append({
                        'announcement_id': announcement.announcement_id,
                        'title': announcement.title,
                        'content_excerpt': content_excerpt,
                        'date_posted': announcement.date_posted.isoformat() if announcement.date_posted else None,
                        'date_posted_display': announcement.date_posted.strftime('%b %d, %Y') if announcement.date_posted else 'N/A',
                        'requested_by_user_id': announcement.requested_by_user_id,
                        'requested_by_name': user.name if user else 'Unknown',
                        'requested_by_role': user.role if user else 'Unknown',
                        'relevance_score': 1.0  # Placeholder for actual relevance scoring
                    })
                
                # Sort by date (most recent first)
                formatted_results.sort(key=lambda x: x['date_posted'] or '', reverse=True)
                
                return {
                    'success': True,
                    'search_term': search_term,
                    'results': formatted_results,
                    'total_matches': len(announcements),
                    'limited_to': limit
                }
                
        except Exception as e:
            app.logger.error(f"Error searching announcements: {e}")
            return {
                'success': False,
                'error': str(e)
            }