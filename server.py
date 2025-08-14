from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
import json
import uuid
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from flask_dance.contrib.google import make_google_blueprint, google
from flask import session, redirect, url_for
from functools import wraps
import requests
import hashlib
from pathlib import Path
from sqlalchemy import text

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

AVATARS_DIR = Path("static/avatars")
AVATARS_DIR.mkdir(exist_ok=True)

google_bp = make_google_blueprint(
    client_id=GOOGLE_OAUTH_CLIENT_ID,
    client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
    scope=[
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
        "openid"
    ]
)
app.register_blueprint(google_bp, url_prefix="/login")

def cache_google_avatar(google_avatar_url, user_email):
    if not google_avatar_url:
        return None
    
    try:
        url_hash = hashlib.md5(google_avatar_url.encode()).hexdigest()
        filename = f"{url_hash}_{user_email}.jpg"
        filepath = AVATARS_DIR / filename
        
        if filepath.exists():
            print(f"Avatar already cached for {user_email}: {filename}")
            return f"/static/avatars/{filename}"
        
        print(f"Caching avatar for {user_email} from {google_avatar_url}")
        
        response = requests.get(google_avatar_url, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"Successfully cached avatar for {user_email}: {filename}")
            return f"/static/avatars/{filename}"
        else:
            print(f"Failed to download avatar: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"Timeout while downloading avatar for {user_email}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error while downloading avatar for {user_email}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error caching avatar for {user_email}: {str(e)}")
        return None

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
    user_email = db.Column(db.String, nullable=True)

    def to_dict(self):
        base_dict = {
            'id': self.id,
            'service': self.service,
            'date': self.date,
            'time': self.time,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'notes': self.notes,
            'status': self.status,
        }
        
        try:
            if hasattr(self, 'user_email'):
                base_dict['user_email'] = self.user_email
        except Exception:
            pass
            
        return base_dict

def column_exists(table_name, column_name):
    try:
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except Exception as e:
        print(f"Error checking if column {column_name} exists: {e}")
        return False

def ensure_migration():
    try:
        if not column_exists('booking', 'user_email'):
            print("user_email column missing, running migration...")
            migrate_database()
            if not column_exists('booking', 'user_email'):
                print("Warning: Migration failed, some features may not work properly")
        return True
    except Exception as e:
        print(f"Error during migration check: {e}")
        return False

def migrate_database():
    try:
        inspector = db.inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('booking')]
        
        if 'user_email' not in columns:
            print("Adding user_email column to booking table...")
            
            if 'postgresql' in str(db.engine.url).lower():
                db.session.execute(text('ALTER TABLE booking ADD COLUMN user_email VARCHAR'))
            elif 'mysql' in str(db.engine.url).lower():
                db.session.execute(text('ALTER TABLE booking ADD COLUMN user_email VARCHAR(255)'))
            elif 'sqlite' in str(db.engine.url).lower():
                db.session.execute(text('ALTER TABLE booking ADD COLUMN user_email TEXT'))
            else:
                db.session.execute(text('ALTER TABLE booking ADD COLUMN user_email VARCHAR(255)'))
            
            db.session.commit()
            print("Successfully added user_email column")
        else:
            print("user_email column already exists")
            
    except Exception as e:
        print(f"Database migration error: {e}")
        db.session.rollback()
        try:
            print("Trying fallback migration method...")
            db.session.execute(text('ALTER TABLE booking ADD COLUMN user_email VARCHAR(255)'))
            db.session.commit()
            print("Successfully added user_email column using fallback method")
        except Exception as fallback_error:
            print(f"Fallback migration also failed: {fallback_error}")
            db.session.rollback()

with app.app_context():
    db.create_all()
    migrate_database()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not google.authorized:
            if request.path.startswith('/api/') or request.headers.get('HX-Request'):
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    user_info = None
    google_avatar = None
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
            google_avatar_url = user_info.get("picture")
            user_email = user_info.get('email')
            
            cached_avatar = cache_google_avatar(google_avatar_url, user_email)
            
            session['google_email'] = user_email
            session['google_avatar'] = cached_avatar or google_avatar_url
            session['user_info'] = {
                'name': user_info.get('name', ''),
                'email': user_email,
                'picture': cached_avatar or google_avatar_url
            }
    return render_template('index.html', user_info=user_info, google_avatar=google_avatar)

@app.route('/login')
def login():
    if google.authorized:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/login/google/authorized')
def google_authorized():
    if not google.authorized:
        print("Google authorization failed")
        return redirect(url_for("login"))
    
    try:
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            print(f"Failed to fetch user info: {resp.text}")
            return "Failed to fetch user info.", 400
        
        user_info = resp.json()
        user_email = user_info.get('email')
        google_avatar_url = user_info.get('picture')
        
        cached_avatar = cache_google_avatar(google_avatar_url, user_email)
        
        session['google_email'] = user_email
        session['google_avatar'] = cached_avatar or google_avatar_url
        session['user_info'] = {
            'name': user_info.get('name', ''),
            'email': user_email,
            'picture': cached_avatar or google_avatar_url
        }
        
        print(f"Successfully logged in user: {user_email}")
        return redirect(url_for("index", login_success="true"))
    except Exception as e:
        print(f"Error during Google OAuth: {str(e)}")
        return redirect(url_for("login"))

@app.route('/api/user-info')
@login_required
def get_user_info():
    if google.authorized:
        resp = google.get("/oauth2/v2/userinfo")
        if resp.ok:
            user_info = resp.json()
            user_email = user_info.get('email')
            google_avatar_url = user_info.get('picture')
            
            cached_avatar = cache_google_avatar(google_avatar_url, user_email)
            
            return jsonify({
                'name': user_info.get('name', ''),
                'email': user_email,
                'picture': cached_avatar or google_avatar_url
            })
    return jsonify({'error': 'User not authenticated'}), 401

@app.route('/api/bookings', methods=['GET'])
@login_required
def get_bookings():
    if not google.authorized:
        return jsonify({'error': 'User not authenticated'}), 401
    
    ensure_migration()
    
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({'error': 'Failed to get user info'}), 401
    
    user_info = resp.json()
    user_email = user_info.get('email')
    
    try:
        if column_exists('booking', 'user_email'):
            bookings = Booking.query.filter(
                (Booking.user_email == user_email) | 
                ((Booking.user_email.is_(None)) & (Booking.email == user_email)),
                Booking.status != 'cancelled'
            ).all()
        else:
            bookings = Booking.query.filter(
                Booking.email == user_email,
                Booking.status != 'cancelled'
            ).all()
    except Exception as e:
        print(f"Warning: Error in user-specific booking query, falling back to email-only: {e}")
        bookings = Booking.query.filter(
            Booking.email == user_email,
            Booking.status != 'cancelled'
        ).all()
    
    return jsonify([b.to_dict() for b in bookings])

@app.route('/api/bookings', methods=['POST'])
@login_required
def create_booking():
    try:
        print("=== BOOKING REQUEST RECEIVED ===")
        
        ensure_migration()
        
        data = request.get_json()
        print(f"Received data: {data}")
        
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Failed to get user info'}), 401
        
        user_info = resp.json()
        user_email = user_info.get('email')
        
        required_fields = ['service', 'date', 'time', 'name', 'email', 'phone']
        for field in required_fields:
            if not data.get(field):
                print(f"Missing field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        try:
            existing_booking = Booking.query.filter_by(date=data['date'], time=data['time']).filter(Booking.status != 'cancelled').first()
            if existing_booking:
                print(f"Slot already booked: {data['date']} {data['time']}")
                return jsonify({'error': 'This time slot is already booked'}), 409
        except Exception as e:
            print(f"Warning: Could not check existing bookings due to column issue: {e}")
        
        if not column_exists('booking', 'user_email'):
            print("user_email column does not exist, attempting to add it...")
            migrate_database()
        
        if column_exists('booking', 'user_email'):
            new_booking = Booking(
                id=f"BK{str(uuid.uuid4())[:8].upper()}",
                service=data['service'],
                date=data['date'],
                time=data['time'],
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                notes=data.get('notes', ''),
                status='confirmed',
                user_email=user_email
            )
        else:
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
            print("Warning: Created booking without user_email column")
        
        print(f"Creating booking: {new_booking.id}")
        
        db.session.add(new_booking)
        db.session.commit()
        print(f"Booking saved to database: {new_booking.id}")
        
        return jsonify(new_booking.to_dict()), 201
    except Exception as e:
        print(f"ERROR creating booking: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings/<booking_id>', methods=['PUT'])
@login_required
def update_booking(booking_id):
    try:
        ensure_migration()
        
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Failed to get user info'}), 401
        
        user_info = resp.json()
        user_email = user_info.get('email')
        
        data = request.get_json()
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        if column_exists('booking', 'user_email') and hasattr(booking, 'user_email'):
            if booking.user_email and booking.user_email != user_email:
                return jsonify({'error': 'Unauthorized: You can only modify your own bookings'}), 403
            
            if not booking.user_email and booking.email != user_email:
                return jsonify({'error': 'Unauthorized: You can only modify your own bookings'}), 403
        else:
            if booking.email != user_email:
                return jsonify({'error': 'Unauthorized: You can only modify your own bookings'}), 403
        
        for key, value in data.items():
            if hasattr(booking, key) and key != 'user_email':
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
@login_required
def delete_booking(booking_id):
    try:
        ensure_migration()
        
        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return jsonify({'error': 'Failed to get user info'}), 401
        
        user_info = resp.json()
        user_email = user_info.get('email')
        
        booking = db.session.get(Booking, booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        if column_exists('booking', 'user_email') and hasattr(booking, 'user_email'):
            if booking.user_email and booking.user_email != user_email:
                return jsonify({'error': 'Unauthorized: You can only cancel your own bookings'}), 403
            
            if not booking.user_email and booking.email != user_email:
                return jsonify({'error': 'Unauthorized: You can only cancel your own bookings'}), 403
        else:
            if booking.email != user_email:
                return jsonify({'error': 'Unauthorized: You can only cancel your own bookings'}), 403
        
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
@login_required
def get_available_slots(date):
    try:
        slots = []
        start_hour = 8
        end_hour = 20
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
@login_required
def get_services():
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

@app.route('/htmx/bookings-list', methods=['GET'])
@login_required
def htmx_bookings_list():
    ensure_migration()
    
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({'error': 'Failed to get user info'}), 401
    
    user_info = resp.json()
    user_email = user_info.get('email')
    
    try:
        if column_exists('booking', 'user_email'):
            bookings = Booking.query.filter(
                (Booking.user_email == user_email) | 
                ((Booking.user_email.is_(None)) & (Booking.email == user_email)),
                Booking.status != 'cancelled'
            ).all()
        else:
            bookings = Booking.query.filter(
                Booking.email == user_email,
                Booking.status != 'cancelled'
            ).all()
    except Exception as e:
        print(f"Warning: Error in user-specific booking query, falling back to email-only: {e}")
        bookings = Booking.query.filter(
            Booking.email == user_email,
            Booking.status != 'cancelled'
        ).all()
    
    return render_template('bookings_list.html', bookings=bookings)

@app.route('/htmx/booking-form', methods=['GET'])
@login_required
def htmx_booking_form():
    return render_template('booking_form.html')

@app.route('/api/migrate', methods=['POST'])
def manual_migrate():
    try:
        print("Manual migration requested...")
        success = ensure_migration()
        if success:
            return jsonify({'message': 'Migration completed successfully'}), 200
        else:
            return jsonify({'error': 'Migration failed'}), 500
    except Exception as e:
        print(f"Error in manual migration: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/status', methods=['GET'])
def check_status():
    try:
        user_email_exists = column_exists('booking', 'user_email')
        return jsonify({
            'user_email_column_exists': user_email_exists,
            'migration_status': 'complete' if user_email_exists else 'pending'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)