/**
 * Announcements Modal and Interaction Script
 * Handles all announcement-related UI interactions including modals, toasts, and detail views
 */

document.addEventListener("DOMContentLoaded", () => {
    // =====================
    // Announcements Modal Functions
    // =====================
    
    function openAnnouncementsModal() {
        const modal = document.getElementById('announcementsModal');
        const listView = document.getElementById('anncListView');
        const detailView = document.getElementById('anncDetailView');
        if (modal) {
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
            // Ensure list view is shown and detail view is hidden
            if (listView) listView.style.display = 'block';
            if (detailView) detailView.style.display = 'none';
        }
    }
    
    function closeAnnouncementsModal() {
        const modal = document.getElementById('announcementsModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    }
    
    function showAnnouncementDetail(el) {
        const listView = document.getElementById('anncListView');
        const detailView = document.getElementById('anncDetailView');
        const detailTitle = document.getElementById('anncDetailTitle');
        const detailDate = document.getElementById('anncDetailDate');
        const detailContent = document.getElementById('anncDetailContent');
        
        if (listView && detailView && detailTitle && detailDate && detailContent) {
            // Get data from clicked element
            const title = el.dataset.title || '';
            const date = el.dataset.date || '';
            const content = el.dataset.content || '';
            
            // Fill detail view
            detailTitle.textContent = title;
            detailDate.textContent = date;
            detailContent.textContent = content;
            
            // Show detail view, hide list view
            listView.style.display = 'none';
            detailView.style.display = 'block';
        }
    }
    
    function backToList() {
        const listView = document.getElementById('anncListView');
        const detailView = document.getElementById('anncDetailView');
        if (listView && detailView) {
            listView.style.display = 'block';
            detailView.style.display = 'none';
        }
    }
    
    // =====================
    // Announcement Detail Modal Functions
    // =====================
    
    function openAnnouncementDetailModal(title, date, content) {
        const modal = document.getElementById('announcementDetailModal');
        const titleEl = document.getElementById('announcementDetailTitle');
        const dateEl = document.getElementById('announcementDetailDate');
        const contentEl = document.getElementById('announcementDetailContent');
        
        if (modal && titleEl && dateEl && contentEl) {
            titleEl.textContent = title || '';
            dateEl.textContent = date || '';
            contentEl.textContent = content || '';
            modal.style.display = 'flex';
            modal.setAttribute('aria-hidden', 'false');
        }
    }
    
    function closeAnnouncementDetailModal() {
        const modal = document.getElementById('announcementDetailModal');
        if (modal) {
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        }
    }
    
    // =====================
    // Event Handlers Setup
    // =====================
    
    // Open modal button
    const openModalBtn = document.getElementById('openAnnouncementsModal');
    if (openModalBtn) {
        openModalBtn.addEventListener('click', openAnnouncementsModal);
    }
    
    // Close modal button
    const closeModalBtn = document.getElementById('closeAnnouncementsModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeAnnouncementsModal);
    }
    
    // Close modal on backdrop click
    const modal = document.getElementById('announcementsModal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAnnouncementsModal();
            }
        });
    }
    
    // Announcement list items click handler
    document.querySelectorAll('.annc-item').forEach(item => {
        item.addEventListener('click', function() {
            showAnnouncementDetail(this);
        });
    });
    
    // Back to list button
    const backToListBtn = document.getElementById('anncBackToList');
    if (backToListBtn) {
        backToListBtn.addEventListener('click', backToList);
    }
    
    // Announcement bell click handler - shows toast
    const announcementBell = document.getElementById('announcementBell');
    const notifToast = document.getElementById('notifToast');
    const notifToastMsg = document.getElementById('notifToastMsg');
    const notifToastOpen = document.getElementById('notifToastOpen');
    const notifToastClose = document.getElementById('notifToastClose');
    
    if (announcementBell && notifToast && notifToastMsg) {
        announcementBell.addEventListener('click', () => {
            // Get announcements count from data attribute
            const announcementsCount = parseInt(announcementBell.dataset.announcementsCount || '0') || 0;
            
            // Always show toast with appropriate message
            if (announcementsCount > 0) {
                notifToastMsg.textContent = 'You have new announcements.';
            } else {
                notifToastMsg.textContent = 'No new announcements.';
            }
            
            notifToast.style.display = 'block';
        });
    }
    
    // Toast "View announcements" button - opens modal and closes toast
    if (notifToastOpen) {
        notifToastOpen.addEventListener('click', () => {
            openAnnouncementsModal();
            if (notifToast) {
                notifToast.style.display = 'none';
            }
        });
    }
    
    // Toast close button
    if (notifToastClose) {
        notifToastClose.addEventListener('click', () => {
            if (notifToast) {
                notifToast.style.display = 'none';
            }
        });
    }
    
    // Click handlers for announcement items
    document.querySelectorAll('.announcement-item.clickable').forEach(item => {
        item.addEventListener('click', function() {
            const title = this.dataset.title || '';
            const date = this.dataset.date || '';
            const content = this.dataset.content || '';
            openAnnouncementDetailModal(title, date, content);
        });
    });
    
    // Close announcement detail modal button
    const closeAnnouncementDetailBtn = document.getElementById('closeAnnouncementDetail');
    if (closeAnnouncementDetailBtn) {
        closeAnnouncementDetailBtn.addEventListener('click', closeAnnouncementDetailModal);
    }
    
    // Close announcement detail modal on backdrop click
    const announcementDetailModal = document.getElementById('announcementDetailModal');
    if (announcementDetailModal) {
        announcementDetailModal.addEventListener('click', (e) => {
            if (e.target === announcementDetailModal) {
                closeAnnouncementDetailModal();
            }
        });
    }
    
    // Close modal on Escape key (announcements modal)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            // Close announcements modal if open
            const announcementsModal = document.getElementById('announcementsModal');
            if (announcementsModal && announcementsModal.style.display !== 'none') {
                closeAnnouncementsModal();
            }
            // Close announcement detail modal if open
            const announcementDetailModal = document.getElementById('announcementDetailModal');
            if (announcementDetailModal && announcementDetailModal.style.display !== 'none') {
                closeAnnouncementDetailModal();
            }
        }
    });
    
    // Export functions to global scope for use in other scripts if needed
    window.announcements = {
        openModal: openAnnouncementsModal,
        closeModal: closeAnnouncementsModal,
        openDetailModal: openAnnouncementDetailModal,
        closeDetailModal: closeAnnouncementDetailModal
    };
});
