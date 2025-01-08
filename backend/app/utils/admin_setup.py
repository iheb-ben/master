from typing import Optional
from app.connector import db
from app.models.user import User, AccessRightCategory
from app.tools import generate_secret_string

SUPER_USER_ID = 1
PUBLIC_USER_ID = 2
DEFAULT_CATEGORY_ID = 1


def ensure_admin_user():
    global SUPER_USER_ID, PUBLIC_USER_ID, DEFAULT_CATEGORY_ID
    admin_username = 'admin'
    admin: Optional[User] = User.query.filter_by(username=admin_username).first()
    if not admin:
        hashed_password = generate_secret_string('admin')
        admin = User(username=admin_username, password=hashed_password, role='user', single_session_mode=True)
        db.session.add(admin)
        db.session.commit()
    SUPER_USER_ID = admin.id
    public_username = 'public'
    public: Optional[User] = User.query.filter_by(username=public_username).first()
    if not public:
        hashed_password = generate_secret_string('public')
        public = User(username=public_username, password=hashed_password, role='public')
        db.session.add(public)
        db.session.commit()
    PUBLIC_USER_ID = public.id
    default_category = 'Other'
    category: Optional[AccessRightCategory] = AccessRightCategory.query.filter_by(name=default_category).first()
    if not category:
        category = AccessRightCategory(
            create_uid=SUPER_USER_ID,
            name=default_category,
        )
        db.session.add(category)
        db.session.commit()
    DEFAULT_CATEGORY_ID = category.id
