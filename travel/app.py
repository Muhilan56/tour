import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Initialize the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}

# Initialize the database
db = SQLAlchemy(app)

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
EMAIL_FROM = 'daminmain@gmail.com'
EMAIL_PASSWORD = 'kpqtxqskedcykwjz'  # Replace with your app password

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    interest = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(100), nullable=True)
    hotels = db.relationship('Hotel', back_populates='place')

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    image = db.Column(db.String(100), nullable=True)
    place = db.relationship('Place', back_populates='hotels')

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    booking_date = db.Column(db.String(50), nullable=False)

# Helper function to send emails
def send_email(subject, body, recipients):
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        for recipient in recipients:
            message = MIMEMultipart()
            message['From'] = EMAIL_FROM
            message['To'] = recipient
            message['Subject'] = subject
            message.attach(MIMEText(body, 'plain'))
            server.sendmail(EMAIL_FROM, recipient, message.as_string())
            print(f"Email sent to {recipient}")
        server.quit()
    except Exception as e:
        print(f"Error sending email: {e}")

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contact')
def contact():
    return render_template('contact.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check for admin login
        if username == 'admin' and password == '1234':
            session['user_id'] = 'admin'
            send_email(
                "Admin Login Alert",
                "Admin has logged in successfully.",
                [EMAIL_FROM]  # Send email to the admin's email
            )
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session['user_id'] = user.id
            send_email(
                "Login Successful",
                f"Dear {user.username},\n\nYou have successfully logged in to our ToUR-WoRLD platform.",
                [user.email]
            )
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Login Failed. Check your username and/or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        mobile_number = request.form['mobile_number']
        role = 'user'

        new_user = User(username=username, password=password, email=email, mobile_number=mobile_number, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration Successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/admin_dashboard')
def admin_dashboard():
    places = Place.query.all()
    return render_template('admin_dashboard.html', places=places)

@app.route('/user_dashboard')
def user_dashboard():
    places = Place.query.all()
    return render_template('user_dashboard.html', places=places)

@app.route('/add_place', methods=['GET', 'POST'])
def add_place():
    if request.method == 'POST':
        name = request.form['name']
        interest = request.form['interest']
        description = request.form['description']
        location = request.form['location']
        image = request.files['image']
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            image_path = None

        new_place = Place(name=name, interest=interest, description=description, location=location, image=image_path)
        db.session.add(new_place)
        db.session.commit()

        flash('Place Added Successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_place.html')


@app.route('/view_hotels/<int:place_id>', methods=['GET', 'POST'])
def view_hotels(place_id):
    place = Place.query.get_or_404(place_id)
    hotels = Hotel.query.filter_by(place_id=place_id).all()

    if request.method == 'POST':
        hotel_id = request.form.get('hotel_id')  # Get the selected hotel_id from the form
        if hotel_id:
            hotel = Hotel.query.get_or_404(hotel_id)
            return redirect(url_for('book_place', place_id=place_id, hotel_id=hotel.id))

    return render_template('view_hotels.html', place=place, hotels=hotels)





@app.route('/hotel_details/<int:hotel_id>', methods=['GET'])
def view_hotel_details(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)

    # Get the place associated with the hotel
    place = Place.query.get_or_404(hotel.place_id)

    # Get the weather for the place
    is_raining = check_weather(place.name)

    # Example list of hotel images (you can update this with actual images from the database or storage)
    hotel_images = ['image1.jpg', 'image2.jpg', 'image3.jpg', 'image4.jpg', 'image5.jpg']

    return render_template('hotel_details.html', hotel=hotel, hotel_images=hotel_images, is_raining=is_raining)



@app.route('/book_place/<int:place_id>', methods=['GET', 'POST'])
def book_place(place_id):
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))

    place = Place.query.get_or_404(place_id)
    hotels = Hotel.query.filter_by(place_id=place_id).all()

    if request.method == 'POST':
        selected_hotel_id = request.form['hotel_id']
        hotel = Hotel.query.get_or_404(selected_hotel_id)
        user = User.query.get(session['user_id'])
        
        new_booking = Booking(user_id=user.id, place_id=place.id, hotel_id=hotel.id, booking_date=datetime.today())
        db.session.add(new_booking)
        db.session.commit()

        if check_weather(place.name):
            registered_users = User.query.with_entities(User.email).all()
            email_list = [user.email for user in registered_users]
            send_email(
                " Alert Your Booked Location",
                f"The location '{place.name}' you booked is expected to rain tomorrow. Please take precautions.",
                email_list
            )

        flash('Booking Successful! Weather alert email has been sent.')
        return redirect(url_for('user_dashboard'))

    return render_template('book_place.html', place=place, hotels=hotels)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def check_weather(place_name):
    api_key = 'LJ6uia2Hrfhxs-vuKjkpNibD4qRfaucds-nEO8NFdDHOpFZoO8'  # Replace with your actual API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={place_name}&appid={api_key}&units=metric"
    response = requests.get(url)
    data = response.json()
    return 'rain' in data  # True if rain is in the data

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
