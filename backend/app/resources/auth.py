import datetime
import logging
from typing import Optional
from dateutil.relativedelta import relativedelta
from flask_restx import Namespace, Resource, fields, reqparse
from flask import request, abort
import jwt
from app.connector import db, rollback_commit
from app.models.user import User, Partner
from app.models.session import Session
from app import config, api
from app.resources import ResponseMessages
from app.tools import client_public_ip, token_expiration_date, generate_secret_string
from app.utils import login_required

auth_ns: Namespace = api.namespace(name='Authentication', path='/auth', description='Authentication operations')
header_parser = reqparse.RequestParser()
header_parser.add_argument(
    'User-Agent',
    location='headers',
    required=False,
    help='Identifies the client software (browser, app, etc.) making the request'
)
header_parser.add_argument(
    'X-Real-IP',
    location='headers',
    required=False,
    help='Contains the real IP address of the client as determined by the proxy or load balancer'
)
header_parser.add_argument(
    'X-Forwarded-For',
    location='headers',
    required=False,
    help='Contains the originating IP address of the client connecting through a proxy or load balancer'
)
login_request = auth_ns.model(name='LoginRequest', model={
    'username': fields.String(required=True, description='Username/Email of the user'),
    'password': fields.String(required=True, description='Password of the user'),
    'remember_me': fields.Boolean(description='Remember user'),
}, strict=True)
login_response = auth_ns.model(name='LoginResponse', model={
    'message': fields.String(description='Login status message'),
    'token': fields.String(description='JWT token for authentication'),
    'expires_at': fields.String(description='Token expiration date in ISO 8601 format')
})
_logger = logging.getLogger(__name__)


@auth_ns.route('/login')
class LoginResource(Resource):
    @auth_ns.expect(login_request, header_parser)
    @auth_ns.response(code=200, description='Login successful', model=login_response)
    @auth_ns.response(code=401, description=ResponseMessages.LOGIN_ERROR.value)
    @rollback_commit
    def post(self):
        """Authenticate user and generate a token"""
        username = str(auth_ns.payload['username']).strip()
        password = str(auth_ns.payload['password']).strip()
        # Fetch the user
        user: Optional[User] = User.query.filter_by(username=username, active=True).first()
        if not user:
            partner = Partner.query.filter_by(email=username).first()
            user = partner and partner.user or None
        if not user or user.password != generate_secret_string(password):
            abort(401, ResponseMessages.INVALID_CREDENTIALS.value)
        logged_in_at, expires_at = token_expiration_date()
        if user.suspend_until and user.suspend_until >= logged_in_at:
            abort(401, ResponseMessages.ACCOUNT_SUSPENDED.value)
        user.suspend_until = None
        if auth_ns.payload['remember_me']:
            expires_at = logged_in_at + relativedelta(years=1)
        # Extract the client's IP address
        ip_address = client_public_ip()
        # Generate JWT token
        token = jwt.encode({
            'user_id': user.id,
            'ip': ip_address,
            'exp': expires_at,
        }, config.JWT_SECRET_KEY, algorithm='HS256')
        user_agent = request.headers.get('User-Agent') or 'Undefined'
        # Manage session
        user_session: Optional[Session] = Session.query.filter_by(user_id=user.id, ip_address=ip_address).first()
        if user_session:
            if user.single_session_mode:
                # If there are multiple sessions for the same user, invalidate all except the selected one
                for other_session in user.sessions:
                    if other_session != user_session:
                        other_session.active = False
            user_session.active = True
            user_session.token = token
            user_session.logged_in_at = logged_in_at
            user_session.expires_at = expires_at
            user_session.user_agent = user_agent
        else:
            request.user = user
            # Create a new session
            user_session = Session(
                user_id=user.id,
                user_agent=user_agent,
                token=token,
                ip_address=ip_address,
                logged_in_at=logged_in_at,
                expires_at=expires_at)
            db.session.add(user_session)
        # Return the token
        return {
            'message': 'Login successful',
            'token': token,
            'expires_at': expires_at.isoformat(),
        }, 200


@auth_ns.route('/logout')
class LogoutResource(Resource):
    @auth_ns.response(200, 'Logout successful')
    @login_required(auth_ns)
    @rollback_commit
    def post(self):
        """Logout user and invalidate session"""
        ip_address = client_public_ip()
        Session.query.filter_by(user_id=user.id, ip_address=ip_address, active=True).update({
            'logged_out_at': datetime.datetime.utcnow(),
            'token': None,
        })
        return {'message': 'Logout successful'}, 200
