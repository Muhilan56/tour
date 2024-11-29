import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import requests
from werkzeug.utils import secure_filename
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_login import login_required


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
    reviews = db.relationship('Review', back_populates='user')


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    star_rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500), nullable=True)

    hotel = db.relationship('Hotel', back_populates='reviews')
    user = db.relationship('User', back_populates='reviews')


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
    contact_number = db.Column(db.String(15), nullable=True)  # New contact number field
    reviews = db.relationship('Review', back_populates='hotel')
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_weather_data(place_name):
    api_key = 'bbbf3b5b760d084583c22305dbc2e142e'  # Replace with your actual API key
    url = f"http://api.openweathermap.org/data/2.5/weather?q={place_name}&appid={api_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        # Get the temperature and weather conditions (rain, clouds, etc.)
        temperature = data['main']['temp']
        weather_conditions = [condition['main'] for condition in data['weather']]
        is_raining = 'Rain' in weather_conditions
        return temperature, is_raining
    return None, False


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


@app.route('/add_hotel', methods=['GET', 'POST'])
def add_hotel():
    # Fetch all places to display in the dropdown
    places = Place.query.all()

    if request.method == 'POST':
        # Get form data
        place_id = request.form['place_id']
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        contact_number = request.form['contact_number']

        # Handle the image upload
        image = request.files['image']
        image_filename = None
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Create a new hotel instance
        hotel = Hotel(
            place_id=place_id,
            name=name,
            price_per_night=price,
            description=description,
            contact_number=contact_number,
            image=image_filename
        )

        # Add to database and commit
        db.session.add(hotel)
        db.session.commit()

        return redirect(url_for('admin_dashboard', place_id=place_id))

    return render_template('add_hotel.html', places=places)



@app.route('/view_hotels/<int:place_id>', methods=['GET', 'POST'])
def view_hotels(place_id):
    place = Place.query.get_or_404(place_id)
    hotels = Hotel.query.filter_by(place_id=place_id).all()
    current_temperature, is_raining = get_weather_data(place.name)

    if request.method == 'POST':
        hotel_id = request.form.get('hotel_id')  # Get the selected hotel_id from the form
        if hotel_id:
            hotel = Hotel.query.get_or_404(hotel_id)
            return redirect(url_for('book_place', hotel_id=hotel.id))

    return render_template(
        'view_hotels.html', 
        place=place, 
        hotels=hotels, 
        current_temperature=current_temperature, 
        is_raining=is_raining
    )



@app.route('/hotel_details/<int:hotel_id>', methods=['GET', 'POST'])
def view_hotel_details(hotel_id):
    # Your combined function logic
    hotel = Hotel.query.get_or_404(hotel_id)
    hotel_images = ['image1.jpg', 'image2.jpg', 'image3.jpg', 'image4.jpg', 'image5.jpg']
    place = hotel.place

    current_temperature, is_raining = get_weather_data(place.name) if place else (None, False)

    return render_template(
        'hotel_details.html',
        hotel=hotel,
        hotel_images=hotel_images,
        is_raining=is_raining,
        current_temperature=current_temperature,
        place=place
    )


@app.route('/submit_review/<int:hotel_id>', methods=['GET', 'POST'])
def submit_review(hotel_id):
    hotel = Hotel.query.get_or_404(hotel_id)
    
    if request.method == 'POST':
        name = request.form['name']
        star_rating = request.form['star_rating']
        comment = request.form['comment']
        
        # You can add a user_id if the user is logged in
        user_id = session.get('user_id')

        # Save the review to the database
        new_review = Review(
            hotel_id=hotel.id,
            user_id=user_id,  # Optional if you're tracking logged-in users
            name=name,
            star_rating=int(star_rating),
            comment=comment
        )
        db.session.add(new_review)
        db.session.commit()

        flash('Your review has been submitted successfully!', 'success')
        return redirect(url_for('view_hotel_details', hotel_id=hotel.id))

    return render_template('submit_review.html', hotel=hotel)



@app.route('/add_review/<int:hotel_id>', methods=['POST'])
@login_required  # Ensure the user is logged in before they can add a review
def add_review(hotel_id):
    if current_user.is_authenticated:  # Check if the user is logged in
        name = request.form['name']
        star_rating = request.form['star_rating']
        comment = request.form['comment']
        
        review = Review(
            hotel_id=hotel_id,
            user_id=current_user.id,  # Use the logged-in user's ID
            name=name,
            star_rating=star_rating,
            comment=comment
        )
        
        db.session.add(review)
        db.session.commit()
        
        return redirect(url_for('view_hotel', hotel_id=hotel_id))  # Redirect after review is added
    else:
        return redirect(url_for('login'))


@app.route('/book_place/<int:place_id>', methods=['GET', 'POST'])
def book_place(place_id):
    # Ensure the user is logged in before proceeding
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('login'))

    # Fetch place and hotels associated with the given place_id
    place = Place.query.get_or_404(place_id)
    hotels = Hotel.query.filter_by(place_id=place_id).all()

    # Handle form submission for booking a hotel
    if request.method == 'POST':
        if 'hotel_id' not in request.form:
            flash('Please select a hotel!', 'warning')
            return redirect(url_for('book_place', place_id=place_id))

        # Get the selected hotel ID and retrieve the hotel details
        selected_hotel_id = request.form['hotel_id']
        hotel = Hotel.query.get_or_404(selected_hotel_id)

        # Ensure the user exists in the session
        user = User.query.get(session.get('user_id'))

        if not user:
            flash('User not found!', 'danger')
            return redirect(url_for('login'))

        # Create a new booking record
        new_booking = Booking(user_id=user.id, place_id=place.id, hotel_id=hotel.id, booking_date=datetime.utcnow())
        db.session.add(new_booking)
        db.session.commit()

        # After successful booking, check weather for the place and send an alert email if rain is expected
        if get_weather_data(place.name):  # Assuming this function returns weather data (true/false for rain)
            registered_users = User.query.with_entities(User.email).all()
            email_list = [user.email for user in registered_users]

            send_email(
                " Your Booking Alert ",
                f"The location '{place.name}' you booked Successfully. We are Keep Monitering you Location.",
                email_list
            )

            

        flash('Booking Successful! Weather alert email has been sent.')
        return redirect(url_for('user_dashboard'))

    # If it's a GET request, render the booking page
    return render_template('book_place.html', place=place, hotels=hotels)



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
