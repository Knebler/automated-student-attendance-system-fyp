/**
 * Notifications Modal and Interaction Script
 * Handles all notification-related UI interactions including modals, badge updates, and API calls
 */

document.addEventListener("DOMContentLoaded", () => {
    // =====================
    // Configuration
    // =====================
    // Get URLs from data attributes or use defaults
    const notificationBell = document.getElementById('notificationBell');
    const notificationsModal = document.getElementById('notificationsModal');
    
    // Get URLs from data attributes if available, otherwise construct them
    const getNotificationsUrl = notificationBell?.dataset.getNotificationsUrl || 
                                 '/lecturer/api/notifications';
    // Flask url_for uses 0 as placeholder, we'll replace it with actual ID
    const markReadUrlTemplate = notificationBell?.dataset.markReadUrlTemplate || 
                                 '/lecturer/api/notifications/0/mark-read';
    const markAllReadUrl = notificationBell?.dataset.markAllReadUrl || 
                           '/lecturer/api/notifications/mark-all-read';
    const clearAllUrl = notificationBell?.dataset.clearAllUrl || 
                        '/lecturer/api/notifications/clear-all';
    
    // =====================
    // Notifications Modal Functions
    // =====================
    
    function openNotificationsModal() {
        const modal = document.getElementById('notificationsModal');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
            loadNotifications();
        }
    }
    
    function closeNotificationsModal() {
        const modal = document.getElementById('notificationsModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    }
    
    function loadNotifications() {
        const notificationsList = document.getElementById('notificationsList');
        if (!notificationsList) return;
        
        notificationsList.innerHTML = '<div class="loading-message">Loading notifications...</div>';
        
        fetch(getNotificationsUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.notifications) {
                    if (data.notifications.length === 0) {
                        notificationsList.innerHTML = '<div class="no-notifications-message"><p>📭 No notifications</p><p class="small-text">You\'re all caught up!</p></div>';
                    } else {
                        notificationsList.innerHTML = '';
                        data.notifications.forEach(notif => {
                            const notifItem = document.createElement('div');
                            notifItem.className = 'notification-item' + (notif.acknowledged ? '' : ' unread');
                            notifItem.dataset.notificationId = notif.notification_id;
                            notifItem.innerHTML = `
                                <p class="notification-content">${escapeHtml(notif.content)}</p>
                                <span class="notification-time">${notif.created_at_relative}</span>
                            `;
                            notifItem.addEventListener('click', () => {
                                if (!notif.acknowledged) {
                                    markNotificationAsRead(notif.notification_id);
                                }
                            });
                            notificationsList.appendChild(notifItem);
                        });
                    }
                } else {
                    notificationsList.innerHTML = '<div class="no-notifications-message"><p>❌ Failed to load notifications</p></div>';
                }
            })
            .catch(error => {
                console.error('Error loading notifications:', error);
                notificationsList.innerHTML = '<div class="no-notifications-message"><p>❌ Error loading notifications</p></div>';
            });
    }
    
    function markNotificationAsRead(notificationId) {
        // Replace the '0' placeholder with actual notification ID
        const url = markReadUrlTemplate.replace('0', notificationId);
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const notifItem = document.querySelector(`.notification-item[data-notification-id="${notificationId}"]`);
                if (notifItem) {
                    notifItem.classList.remove('unread');
                }
                updateNotificationBadge();
            }
        })
        .catch(error => {
            console.error('Error marking notification as read:', error);
        });
    }
    
    function markAllNotificationsAsRead() {
        fetch(markAllReadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelectorAll('.notification-item.unread').forEach(item => {
                    item.classList.remove('unread');
                });
                updateNotificationBadge();
            }
        })
        .catch(error => {
            console.error('Error marking all notifications as read:', error);
        });
    }

    function clearAllNotifications() {
        fetch(clearAllUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.querySelectorAll('.notification-item').forEach(item => {
                    item.remove();
                });
                updateNotificationBadge();
            }
        })
        .catch(error => {
            console.error('Error clearing all notifications:', error);
        });
    }
    
    function updateNotificationBadge() {
        const badge = document.querySelector('#notificationBell .notification-badge');
        const bell = document.getElementById('notificationBell');
        if (badge && bell) {
            const unreadCount = document.querySelectorAll('.notification-item.unread').length;
            if (unreadCount > 0) {
                badge.textContent = unreadCount;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    function escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }
    
    // =====================
    // Event Handlers Setup
    // =====================
    
    // Notification bell click handler - opens notifications modal
    if (notificationBell) {
        notificationBell.addEventListener('click', () => {
            openNotificationsModal();
        });
    }
    
    // Close notifications modal button
    const closeNotificationsModalBtn = document.getElementById('closeNotificationsModal');
    if (closeNotificationsModalBtn) {
        closeNotificationsModalBtn.addEventListener('click', closeNotificationsModal);
    }
    
    // Close notifications modal on backdrop click
    if (notificationsModal) {
        notificationsModal.addEventListener('click', (e) => {
            if (e.target === notificationsModal) {
                closeNotificationsModal();
            }
        });
    }
    
    // Mark all as read button
    const markAllReadBtn = document.getElementById('markAllReadBtn');
    if (markAllReadBtn) {
        markAllReadBtn.addEventListener('click', markAllNotificationsAsRead);
    }
    
    // Clear all notifications button
    const clearAllBtn = document.getElementById('clearAllBtn');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', clearAllNotifications);
    }
    
    // Close modal on Escape key (notifications modal)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const notificationsModal = document.getElementById('notificationsModal');
            if (notificationsModal && notificationsModal.style.display !== 'none') {
                closeNotificationsModal();
            }
        }
    });
    
    // Export functions to global scope for use in other scripts if needed
    window.notifications = {
        openModal: openNotificationsModal,
        closeModal: closeNotificationsModal,
        loadNotifications: loadNotifications,
        updateBadge: updateNotificationBadge
    };
});
