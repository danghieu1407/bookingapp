function bookingApp() {
    return {
        activeTab: 'booking',
        selectedService: '',
        selectedDate: '',
        selectedTime: '',
        availableSlots: [],
        showSuccessModal: false,
        lastBookingId: '',
        lastBookingService: '',
        lastBookingDate: '',
        lastBookingTime: '',
        isEditMode: false,
        editingBookingId: null,
        showCancelModal: false,
        cancelBookingId: null,
        
        bookingForm: {
            name: '',
            email: '',
            phone: '',
            notes: ''
        },
        
        bookings: [
            
        ],
        
        get today() {
            return new Date().toISOString().split('T')[0];
        },
        
        init() {
            this.loadUserInfo();
            this.updateAvailableSlots();
            this.fetchBookings();
            
            this.checkForLoginSuccess();
        },
        
        checkForLoginSuccess() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('login_success') || window.location.pathname.includes('authorized')) {
                this.fetchUserInfo();
                
                if (urlParams.has('login_success')) {
                    urlParams.delete('login_success');
                    const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
                    window.history.replaceState({}, '', newUrl);
                }
            }
        },
        
        loadUserInfo() {
            let userInfo = null;
            try {
                const storedUserInfo = localStorage.getItem('userInfo');
                if (storedUserInfo) {
                    userInfo = JSON.parse(storedUserInfo);
                }
            } catch (error) {
                console.error('Error reading user info from localStorage:', error);
            }
            
            if (!userInfo) {
                const container = document.querySelector('[data-user-info]');
                if (container) {
                    const dataUserInfo = container.getAttribute('data-user-info');
                    if (dataUserInfo && dataUserInfo !== '{}') {
                        try {
                            userInfo = JSON.parse(dataUserInfo);
                            if (userInfo && userInfo.name && userInfo.email) {
                                localStorage.setItem('userInfo', JSON.stringify(userInfo));
                            }
                        } catch (error) {
                            console.error('Error parsing user info from data attribute:', error);
                        }
                    }
                }
            }
            
            if (userInfo && userInfo.name && userInfo.email) {
                this.bookingForm.name = userInfo.name;
                this.bookingForm.email = userInfo.email;
                
                if (userInfo.picture) {
                    this.updateAvatar(userInfo.picture);
                }
            }
        },
        
        async fetchUserInfo() {
            try {
                const lastAvatarRefresh = localStorage.getItem('lastAvatarRefresh');
                const now = Date.now();
                const fiveMinutes = 5 * 60 * 1000;
                
                if (lastAvatarRefresh && (now - parseInt(lastAvatarRefresh)) < fiveMinutes) {
                    console.log('Avatar refresh rate limited, using cached data');
                    return;
                }
                
                const response = await fetch('/api/user-info');
                if (response.ok) {
                    const userInfo = await response.json();
                    if (userInfo.name && userInfo.email) {
                        localStorage.setItem('userInfo', JSON.stringify(userInfo));
                        this.bookingForm.name = userInfo.name;
                        this.bookingForm.email = userInfo.email;
                        
                        if (userInfo.picture) {
                            this.updateAvatar(userInfo.picture);
                        }
                        
                        localStorage.setItem('lastAvatarRefresh', now.toString());
                    }
                }
            } catch (error) {
                console.error('Error fetching user info:', error);
            }
        },
        
        async fetchBookings() {
            try {
                const response = await fetch('/api/bookings');
                if (response.ok) {
                    const bookings = await response.json();
                    this.bookings = bookings.map(b => ({ ...b, highlight: false }));
                } else {
                    console.error('Failed to fetch bookings');
                }
            } catch (error) {
                console.error('Error fetching bookings:', error);
            }
        },
        
        updateAvailableSlots() {
            if (!this.selectedDate) {
                this.availableSlots = [];
                return;
            }

            const slots = [];
            const startHour = 8;
            const endHour = 20;

            for (let hour = startHour; hour < endHour; hour++) {
                const time = `${hour.toString().padStart(2, '0')}:00`;
                slots.push(time);

                if (hour < endHour - 1) {
                    const halfHour = `${hour.toString().padStart(2, '0')}:30`;
                    slots.push(halfHour);
                }
            }

            this.availableSlots = slots;
        },
        
        getServiceName(service) {
            const serviceNames = {
                'room': 'Hotel Room',
                'meeting': 'Meeting Room',
                'spa': 'Spa Treatment'
            };
            return serviceNames[service] || service;
        },
        
        getServicePrice(service) {
            const servicePrices = {
                'room': '$150/night',
                'meeting': '$75/hour',
                'spa': '$120/session'
            };
            return servicePrices[service] || '';
        },
        
        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        },
        
        canSubmit() {
            return this.selectedService && 
                   this.selectedDate && 
                   this.selectedTime && 
                   this.bookingForm.name && 
                   this.bookingForm.email && 
                   this.bookingForm.phone;
        },
        
        submitBooking() {
            if (!this.canSubmit()) return;
            
            const newBooking = {
                id: this.generateBookingId(),
                service: this.selectedService,
                date: this.selectedDate,
                time: this.selectedTime,
                name: this.bookingForm.name,
                email: this.bookingForm.email,
                phone: this.bookingForm.phone,
                notes: this.bookingForm.notes,
                status: 'confirmed'
            };
            
            this.bookings.unshift(newBooking);
            
            this.lastBookingId = newBooking.id;
            this.lastBookingService = newBooking.service;
            this.lastBookingDate = newBooking.date;
            this.lastBookingTime = newBooking.time;
            
            this.showSuccessModal = true;
            
            this.resetForm();
            
            this.updateAvailableSlots();
        },
        
        generateBookingId() {
            const timestamp = Date.now().toString().slice(-6);
            return `BK${timestamp}`;
        },
        
        resetForm() {
            this.selectedService = '';
            this.selectedDate = '';
            this.selectedTime = '';
            
            let userInfo = null;
            try {
                const storedUserInfo = localStorage.getItem('userInfo');
                if (storedUserInfo) {
                    userInfo = JSON.parse(storedUserInfo);
                }
            } catch (error) {
                console.error('Error reading user info from localStorage:', error);
            }
            
            this.bookingForm = {
                name: userInfo ? userInfo.name || '' : '',
                email: userInfo ? userInfo.email || '' : '',
                phone: '',
                notes: ''
            };
            this.exitEditMode();
        },
        
        exitEditMode() {
            this.isEditMode = false;
            this.editingBookingId = null;
        },
        
        editBooking(booking) {
            this.isEditMode = true;
            this.editingBookingId = booking.id;
            
            this.selectedService = booking.service;
            this.selectedDate = booking.date;
            this.selectedTime = booking.time;
            this.bookingForm = {
                name: booking.name,
                email: booking.email,
                phone: booking.phone,
                notes: booking.notes
            };
            
            this.activeTab = 'booking';
            
            this.updateAvailableSlots();
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
        },
        
        cancelBooking(bookingId) {
            if (confirm('Are you sure you want to cancel this booking?')) {
                const bookingIndex = this.bookings.findIndex(b => b.id === bookingId);
                if (bookingIndex !== -1) {
                    this.bookings[bookingIndex].status = 'cancelled';
                }
            }
        },
        
        openCancelModal(bookingId) {
            this.cancelBookingId = bookingId;
            this.showCancelModal = true;
        },
        async confirmCancelBooking() {
            if (this.cancelBookingId) {
                try {
                    const response = await fetch(`/api/bookings/${this.cancelBookingId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    });
                    if (response.ok) {
                        this.bookings = this.bookings.map(b => b.id === this.cancelBookingId ? { ...b, status: 'cancelled' } : b);
                        showNotification('Booking cancelled successfully!', 'success');
                        this.fetchBookings();
                    } else {
                        showNotification('Failed to cancel booking.', 'error');
                    }
                } catch (error) {
                    showNotification('Network error while cancelling booking.', 'error');
                }
                this.cancelBookingId = null;
            }
            this.showCancelModal = false;
        },
        
        async submitBookingHTMX() {
            const formData = {
                service: this.selectedService,
                date: this.selectedDate,
                time: this.selectedTime,
                ...this.bookingForm
            };
            
            try {
                let response;
                
                if (this.isEditMode) {
                    response = await fetch(`/api/bookings/${this.editingBookingId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });
                } else {
                    response = await fetch('/api/bookings', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(formData)
                    });
                }
                
                if (response.ok) {
                    if (this.isEditMode) {
                        const updatedBooking = await response.json();
                        const bookingIndex = this.bookings.findIndex(b => b.id === this.editingBookingId);
                        if (bookingIndex !== -1) {
                            this.bookings[bookingIndex] = updatedBooking;
                            this.bookings[bookingIndex].highlight = true;
                            setTimeout(() => {
                                this.bookings[bookingIndex].highlight = false;
                                this.fetchBookings();
                            }, 3000);
                        }
                        this.exitEditMode();
                        showNotification('Booking updated successfully!', 'success');
                        this.activeTab = 'my-bookings';
                    } else {
                        this.submitBooking();
                    }
                    this.fetchBookings();
                } else {
                    console.error('Booking failed');
                }
            } catch (error) {
                console.error('Network error:', error);
                this.submitBooking();
            }
        },
        
        validateEmail(email) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email);
        },
        
        validatePhone(phone) {
            const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
            return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
        },
        
        addSuccessAnimation(element) {
            element.classList.add('success-animation');
            setTimeout(() => {
                element.classList.remove('success-animation');
            }, 500);
        },

        clearUserInfo() {
            localStorage.removeItem('userInfo');
            this.bookingForm.name = '';
            this.bookingForm.email = '';
            this.updateAvatar(null);
        },
        
        updateAvatar(pictureUrl) {
            var avatarContainer = document.querySelector('[x-data*="userAvatar"]');
            if (avatarContainer && window.Alpine) {
                try {
                    var alpineData = Alpine.$data(avatarContainer);
                    if (alpineData && typeof alpineData.userAvatar !== 'undefined') {
                        alpineData.userAvatar = pictureUrl;
                    }
                } catch (error) {
                    console.error('Error updating avatar:', error);
                }
            }
        }
    };
}

function avatarComponent() {
    return {
        userAvatar: null,
        
        init() {
            this.initAvatar();
        },
        
        initAvatar() {
            let container = document.querySelector('[data-user-info]');
            if (container) {
                let dataUserInfo = container.getAttribute('data-user-info');
                if (dataUserInfo && dataUserInfo !== '{}') {
                    try {
                        let userInfo = JSON.parse(dataUserInfo);
                        if (userInfo.picture) {
                            this.userAvatar = userInfo.picture;
                            return;
                        }
                    } catch (error) {
                        console.error('Error parsing user info:', error);
                    }
                }
            }
            
            try {
                let storedUserInfo = localStorage.getItem('userInfo');
                if (storedUserInfo) {
                    let userInfo = JSON.parse(storedUserInfo);
                    if (userInfo.picture) {
                        this.userAvatar = userInfo.picture;
                    }
                }
            } catch (error) {
                console.error('Error reading user info from localStorage:', error);
            }
        },
        
        getFallbackAvatar() {
            return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjQwIiBoZWlnaHQ9IjQwIiByeD0iMjAiIGZpbGw9IiM2NjdlZWEiLz4KPHBhdGggZD0iTTIwIDIwQzIyLjc2MTQgMjAgMjUgMTcuNzYxNCAyNSAxNUMyNSAxMi4yMzg2IDIyLjc2MTQgMTAgMjAgMTBDMTcuMjM4NiAxMCAxNSAxMi4yMzg2IDE1IDE1QzE1IDE3Ljc2MTQgMTcuMjM4NiAyMCAyMCAyMFoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik0yMCAyMkMxNi42ODYzIDIyIDE0IDI0LjY4NjMgMTQgMjhIMjZDMjYgMjQuNjg2MyAyMy4zMTM3IDIyIDIwIDIyWiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+';
        },
        
        handleAvatarError(event) {
            console.warn('Avatar failed to load, using fallback');
            event.target.src = this.getFallbackAvatar();
            event.target.onerror = null;
        }
    };
}

document.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.xhr.status === 200) {
        console.log('HTMX request successful');
    }
});

document.addEventListener('htmx:responseError', function(event) {
    console.error('HTMX request failed:', event.detail.xhr.status);
});

document.addEventListener('alpine:init', () => {
    Alpine.data('bookingApp', bookingApp);
    Alpine.data('avatarComponent', avatarComponent);
});

function updateBookingsList(bookings) {
    const app = Alpine.$data(document.querySelector('[x-data="bookingApp()"]'));
    if (app) {
        app.bookings = bookings;
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

const notificationStyles = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 8px;
    color: white;
    font-weight: 600;
    z-index: 1001;
    animation: slideIn 0.3s ease-out;
}

.notification.success {
    background: #48bb78;
}

.notification.error {
    background: #e53e3e;
}

@keyframes slideIn {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
`;

const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet); 