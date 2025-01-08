from flask_restx import Namespace, Resource, fields
from app.connector import db
from app.models.user import User
from werkzeug.security import generate_password_hash
from app.utils import login_required
from app import api

user_ns: Namespace = api.namespace(name='Users', path='/users', description='User management operations')
user_model = user_ns.model(name='User', model={
    'username': fields.String(required=True, description='Username of the user'),
    'password': fields.String(required=True, description='Password for the user'),
    'role': fields.String(default='user', description='Role of the user')
})


@user_ns.route('/')
class UserList(Resource):
    @user_ns.marshal_with(user_model, as_list=True, mask=False)
    @login_required(user_ns)
    def get(self):
        """Retrieve all users"""
        return User.query.all()

    @user_ns.expect(user_model)
    @login_required(user_ns)
    def post(self):
        """Create a new user"""
        hashed_password = generate_password_hash(user_ns.payload['password'].strip())
        new_user = User(
            username=user_ns.payload['username'].strip(),
            password=hashed_password,
            role=user_ns.payload.get('role', 'user').strip(),
        )
        db.session.add(new_user)
        db.session.commit()
        return {"id": new_user.id, "username": new_user.username, "role": new_user.role}, 201


# noinspection PyMethodMayBeStatic
@user_ns.route('/<int:user_id>')
class UserDetail(Resource):
    @user_ns.marshal_with(user_model, mask=False)
    @login_required(user_ns)
    def get(self, user_id):
        """Retrieve a user by ID"""
        return User.query.get_or_404(user_id)

    @user_ns.expect(user_model)
    @login_required(user_ns)
    def put(self, user_id):
        """Update a user"""
        data = user_ns.payload
        user = User.query.get_or_404(user_id)
        user.username = data['username']
        user.password = generate_password_hash(data['password'])
        user.role = data.get('role', user.role)
        db.session.commit()
        return {"id": user.id, "username": user.username, "role": user.role}, 200

    @login_required(user_ns)
    def delete(self, user_id):
        """Delete a user"""
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted successfully"}, 200
