from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import uuid
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_dance.contrib.google import make_google_blueprint, google
from flask import session, redirect, url_for

load_dotenv()

app = Flask(__name__)

SQL_TYPE = os.getenv('SQL_TYPE')
SQL_USER = os.getenv('SQL_USER')
SQL_PASSWORD = os.getenv('SQL_PASSWORD')
SQL_HOST = os.getenv('SQL_HOST')
SQL_PORT = os.getenv('SQL_PORT')
SQL_DB = os.getenv('SQL_DB')

db_uri = f"{SQL_TYPE}://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}:{SQL_PORT}/{SQL_DB}"
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
google_bp = make_google_blueprint(
    client_id=GOOGLE_OAUTH_CLIENT_ID,
    client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
    scope=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ],
    redirect_url="/login/google/authorized"
)
app.register_blueprint(google_bp, url_prefix="/login")

class Booking(db.Model):
    id = db.Column(db.String, primary_key=True)
    service = db.Column(db.String, nullable=False)
    date = db.Column(db.String, nullable=False)
    time = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=False)
    notes = db.Column(db.String, default='')
    status = db.Column(db.String, default='confirmed')

    def to_dict(self):
        return {
            'id': self.id,
            'service': self.service,
            'date': self.date,
            'time': self.time,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'notes': self.notes,
            'status': self.status
        }

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    user_info = None
    google_avatar = None
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
            google_avatar = user_info.get("picture")
            session['google_email'] = user_info.get('email')
            session['google_avatar'] = google_avatar
    return render_template('index.html', user_info=user_info, google_avatar=google_avatar)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings except cancelled ones"""
    bookings = Booking.query.filter(Booking.status != 'cancelled').all()
    return jsonify([b.to_dict() for b in bookings])

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    try:
        print("=== BOOKING REQUEST RECEIVED ===")
        data = request.get_json()
        print(f"Received data: {data}")
        
        required_fields = ['service', 'date', 'time', 'name', 'email', 'phone']
        for field in required_fields:
            if not data.get(field):
                print(f"Missing field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if slot is already booked
        existing_booking = Booking.query.filter_by(date=data['date'], time=data['time']).filter(Booking.status != 'cancelled').first()
        if existing_booking:
            print(f"Slot already booked: {data['date']} {data['time']}")
            return jsonify({'error': 'This time slot is already booked'}), 409
        
        new_booking = Booking(
            id=f"BK{str(uuid.uuid4())[:8].upper()}",
            service=data['service'],
            date=data['date'],
            time=data['time'],
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            notes=data.get('notes', ''),
            status='confirmed'
        )
        print(f"Creating booking: {new_booking.id}")
        
        db.session.add(new_booking)
        db.session.commit()
        print(f"Booking saved to database: {new_booking.id}")
        
        return jsonify(new_booking.to_dict()), 201
    except Exception as e:
        print(f"ERROR creating booking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/login/google/authorized')
def google_authorized():
    if not google.authorized:
        return redirect(url_for("index"))
    
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return "Failed to fetch user info.", 400
    
    user_info = resp.json()
    session['google_email'] = user_info.get('email')
    session['google_avatar'] = user_info.get('picture')

    return redirect(url_for("index"))


@app.route('/api/bookings/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update an existing booking"""
    try:
        data = request.get_json()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        for key, value in data.items():
            if hasattr(booking, key):
                setattr(booking, key, value)
        db.session.commit()
        if request.headers.get('HX-Request'):
            return render_template('booking_card.html', booking=booking)
        else:
            booking_dict = booking.to_dict()
            print(f"Returning booking dict: {booking_dict}")
            return jsonify(booking_dict)
    except Exception as e:
        print(f"Error in update_booking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/<booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    """Cancel a booking"""
    try:
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        booking.status = 'cancelled'
        db.session.commit()
        if request.headers.get('HX-Request'):
            return render_template('booking_card.html', booking=booking)
        else:
            booking_dict = booking.to_dict()
            print(f"Returning booking dict: {booking_dict}")
            return jsonify(booking_dict)
    except Exception as e:
        print(f"Error in delete_booking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/slots/<date>', methods=['GET'])
def get_available_slots(date):
    """Get available time slots for a specific date"""
    try:
        slots = []
        start_hour = 8  # 8 AM
        end_hour = 20   # 8 PM
        for hour in range(start_hour, end_hour):
            slots.append(f"{hour:02d}:00")
            if hour < end_hour - 1:
                slots.append(f"{hour:02d}:30")
        booked_slots = [
            booking.time
            for booking in Booking.query.filter_by(date=date).filter(Booking.status != 'cancelled').all()
        ]
        available_slots = [slot for slot in slots if slot not in booked_slots]
        return jsonify(available_slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/services', methods=['GET'])
def get_services():
    """Get available services"""
    services = [
        {
            'id': 'room',
            'name': 'Hotel Room',
            'description': 'Comfortable accommodation',
            'price': '$150/night',
            'icon': 'fas fa-bed'
        },
        {
            'id': 'meeting',
            'name': 'Meeting Room',
            'description': 'Professional meeting space',
            'price': '$75/hour',
            'icon': 'fas fa-users'
        },
        {
            'id': 'spa',
            'name': 'Spa Treatment',
            'description': 'Relaxing wellness services',
            'price': '$120/session',
            'icon': 'fas fa-spa'
        }
    ]
    return jsonify(services)

# HTMX-specific routes for partial updates
@app.route('/htmx/bookings-list', methods=['GET'])
def htmx_bookings_list():
    bookings = Booking.query.all()
    return render_template('bookings_list.html', bookings=bookings)

@app.route('/htmx/booking-form', methods=['GET'])
def htmx_booking_form():
    return render_template('booking_form.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 