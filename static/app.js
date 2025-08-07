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
            {
                id: 'BK001',
                service: 'room',
                date: '2024-01-15',
                time: '14:00',
                name: 'John Doe',
                email: 'john@example.com',
                phone: '+1-555-0123',
                notes: 'Early check-in preferred',
                status: 'confirmed'
            },
            {
                id: 'BK002',
                service: 'meeting',
                date: '2024-01-20',
                time: '10:00',
                name: 'Jane Smith',
                email: 'jane@example.com',
                phone: '+1-555-0456',
                notes: 'Need projector and whiteboard',
                status: 'pending'
            },
            {
                id: 'BK003',
                service: 'spa',
                date: '2024-01-25',
                time: '16:00',
                name: 'Mike Johnson',
                email: 'mike@example.com',
                phone: '+1-555-0789',
                notes: 'Couples massage',
                status: 'confirmed'
            }
        ],
        
        get today() {
            return new Date().toISOString().split('T')[0];
        },
        
        init() {
            this.updateAvailableSlots();
            this.fetchBookings();
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
            this.bookingForm = {
                name: '',
                email: '',
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