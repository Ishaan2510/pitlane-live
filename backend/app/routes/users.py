from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint('users', __name__, url_prefix='/api')


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _secret():
    return os.getenv('SECRET_KEY', 'dev-secret-key')

def create_token(user_id: int) -> str:
    payload = {
        'sub': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=30)
    }
    return jwt.encode(payload, _secret(), algorithm='HS256')

def decode_token(token: str):
    return jwt.decode(token, _secret(), algorithms=['HS256'])

def token_required(f):
    """Decorator — injects current_user into the route."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        try:
            payload = decode_token(auth.split(' ')[1])
            user    = User.query.get(payload['sub'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception:
            return jsonify({'error': 'Invalid token'}), 401
        return f(current_user=user, *args, **kwargs)
    return decorated

def optional_token(f):
    """Decorator — injects current_user or None (no 401 if missing)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = None
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            try:
                payload = decode_token(auth.split(' ')[1])
                user    = User.query.get(payload['sub'])
            except Exception:
                pass
        return f(current_user=user, *args, **kwargs)
    return decorated


# ── Routes ────────────────────────────────────────────────────────────────────

@bp.route('/auth/register', methods=['POST'])
def register():
    data = request.json or {}

    username = (data.get('username') or '').strip()
    email    = (data.get('email')    or '').strip().lower()
    password = (data.get('password') or '').strip()

    if not username or not email or not password:
        return jsonify({'error': 'username, email and password are required'}), 400

    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already taken'}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(
        username      = username,
        email         = email,
        password_hash = generate_password_hash(password)
    )
    db.session.add(user)
    db.session.commit()

    token = create_token(user.id)
    return jsonify({
        'token': token,
        'user':  user.to_dict()
    }), 201


@bp.route('/auth/login', methods=['POST'])
def login():
    data = request.json or {}

    identifier = (data.get('identifier') or '').strip()   # username OR email
    password   = (data.get('password')   or '').strip()

    if not identifier or not password:
        return jsonify({'error': 'identifier and password are required'}), 400

    # Accept username or email
    user = (
        User.query.filter_by(username=identifier).first() or
        User.query.filter_by(email=identifier.lower()).first()
    )

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    token = create_token(user.id)
    return jsonify({
        'token': token,
        'user':  user.to_dict()
    })


@bp.route('/auth/me', methods=['GET'])
@token_required
def me(current_user):
    """Return the currently authenticated user."""
    return jsonify(current_user.to_dict())


# Legacy endpoint kept for compatibility
@bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())