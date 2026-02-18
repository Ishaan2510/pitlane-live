from flask import Blueprint, jsonify, request
from app.models import db, User

bp = Blueprint('users', __name__, url_prefix='/api')

@bp.route('/users/register', methods=['POST'])
def register_user():
    """Register a new user"""
    data = request.json
    
    # Check if username or email already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    user = User(
        username=data['username'],
        email=data['email']
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': user.to_dict()
    }), 201

@bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user profile"""
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())
