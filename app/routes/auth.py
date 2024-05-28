from flask import Blueprint, request
from ..models.User import User
from .. import bcrypt
from .. import db
from app import Config
from auth_middleware import token_required

import re
import jwt
import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(pattern, email):
        return True
    else:
        return False
    
def validate_email_and_password(email, password):
    user = User.query.filter_by(email=email).first()
    if user is None or user.password is None:
        return None
    if bcrypt.check_password_hash(user.password, password) is False:
        return None
    return user

@auth_bp.route('/user_info', methods=['POST'])
@token_required
def user_info(current_user):
    return {
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'email': current_user.email,
        'superuser': current_user.superuser
    }

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    first_name = data['first_name']
    last_name = data['last_name']
    email = data['email']
    password = data['password']
    if not email or not password or not first_name or not last_name:
        return {'message': 'Fill all fields'}, 400
    if len(password) < 6:
        return {'message' : 'Password length must be at least 6!'}, 400
    
    user = User.query.filter_by(email=email).first()
    if user != None:
        return {'message' : 'Same email already exists'}, 400
    if not is_valid_email(email):
        return {'message' : 'Not valid email'}, 400
    # Here you would normally hash the password before saving
    user = User(
        email = email,
        password = bcrypt.generate_password_hash(password, 10).decode('utf-8'),
        first_name = first_name,
        last_name = last_name,
        superuser = 0
    )
    db.session.add(user)
    db.session.commit()
    return {}

@auth_bp.route('/login', methods = ['POST'])
def login():
    data = request.json
    if not data:
        return {"message": "Please provide user details!",}, 400
    validated_user = validate_email_and_password(data['email'], data['password'])
    if validated_user is None:
        return {'message' : 'Credentials not correct!'}, 401
    
    token = jwt.encode({
        'user_id' : validated_user.id,
        'exp': datetime.datetime.now() + datetime.timedelta(hours=24)
        }, Config.SECRET_KEY)
    
    return {'token' : token, 'user': {
        'id': validated_user.id,
        'email': validated_user.email,
        'first_name': validated_user.first_name,
        'last_name': validated_user.last_name,
        'superuser': validated_user.superuser
    }}
