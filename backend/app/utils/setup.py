import logging
import secrets
from typing import Optional, Dict
from app.connector import db, check_db_session
from app.models.user import User, Partner, AccessRight, AccessRightCategory
from app.models.system import ApiKey, Parameter
from app.tools import generate_secret_string

SUPER_USER_ID = 1
PUBLIC_USER_ID = 2
BOT_USER_ID = 3
parameter_name = 'db_initialized'
default_category = 'base.other'
admin_role_name = 'base.admin'
public_role_name = 'base.public'
_logger = logging.getLogger(__name__)


def setup_categories() -> Dict[str, AccessRightCategory]:
    category: Optional[AccessRightCategory] = AccessRightCategory.query.filter_by(name=default_category).first()
    if not category:
        category = AccessRightCategory(name=default_category)
        db.session.add(category)
        db.session.commit()
    return {
        default_category: category,
    }


def setup_roles() -> Dict[str, AccessRight]:
    category = setup_categories()[default_category]
    admin_role: Optional[AccessRight] = AccessRight.query.filter_by(name=admin_role_name).first()
    if not admin_role:
        admin_role = AccessRight(name=admin_role_name, category_id=category.id)
        db.session.add(admin_role)
    public_role: Optional[AccessRight] = AccessRight.query.filter_by(name=public_role_name).first()
    if not public_role:
        public_role = AccessRight(name=public_role_name, category_id=category.id)
        db.session.add(public_role)
    if check_db_session():
        db.session.commit()
    return {
        admin_role_name: admin_role,
        public_role_name: public_role,
    }


def setup_users() -> Dict[int, User]:
    roles = setup_roles()
    admin_role, public_role = roles[admin_role_name], roles[public_role_name]
    admin: Optional[User] = User.query.filter_by(id=SUPER_USER_ID).first()
    if not admin:
        hashed_password = generate_secret_string('admin')
        admin = User(username='admin', password=hashed_password, single_session_mode=True)
        admin.access_rights.append(admin_role)
        db.session.add(admin)
    public: Optional[User] = User.query.filter_by(id=PUBLIC_USER_ID).first()
    hashed_password = generate_secret_string('public')
    if not public:
        public = User(username='public', password=hashed_password)
        public.access_rights.append(public_role)
        db.session.add(public)
    bot: Optional[User] = User.query.filter_by(id=BOT_USER_ID).first()
    if not bot:
        bot = User(username='Bot', password=hashed_password, role='bot')
        bot.access_rights.append(admin_role)
        db.session.add(bot)
    if check_db_session():
        db.session.commit()
    return {
        SUPER_USER_ID: admin,
        PUBLIC_USER_ID: public,
        BOT_USER_ID: bot,
    }


def setup_partners() -> Dict[int, Partner]:
    result = {}
    for user_id, account in setup_users().items():
        if user_id not in (SUPER_USER_ID, PUBLIC_USER_ID, BOT_USER_ID):
            continue
        partner: Optional[Partner] = Partner.query.filter_by(user_id=user_id).first()
        if not partner:
            partner = Partner(
                firstname=account.username,
                lastname='Account',
                email=f'{account.username}@exemple.com',
                user_id=user_id,
            )
            db.session.add(partner)
        result[user_id] = partner
    return result


def setup_default_key() -> ApiKey:
    api_key: Optional[ApiKey] = ApiKey.query.filter_by(domain=None).first()
    if not api_key:
        api_key = ApiKey(key=secrets.token_hex(32))
        db.session.add(api_key)
    return api_key


def db_initialized() -> Parameter:
    parameter: Optional[Parameter] = Parameter.query.filter_by(name=parameter_name).first()
    if not parameter:
        parameter = Parameter(name=parameter_name, value='')
        db.session.add(parameter)
    return parameter


def initialize_database():
    logging.getLogger('app.utils.setup').disabled = False
    parameter = db_initialized()
    if parameter.value != '1':
        setup_partners()
        parameter.value = '1'
    _logger.info(f'secret: {setup_default_key().key}')
