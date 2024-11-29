# models.py

from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Place(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    interest = db.Column(db.String(100), nullable=False)

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('place.id'), nullable=False)

    place = db.relationship('Place', backref=db.backref('hotels', lazy=True))
