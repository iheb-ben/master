from typing import Optional
from app.connector import db
from app.models.user import User, AccessRight, AccessRightCategory
from app.tools import generate_secret_string

SUPER_USER_ID = 1
PUBLIC_USER_ID = 2


def initialize_database():
    default_category = 'base.other'
    category: Optional[AccessRightCategory] = AccessRightCategory.query.filter_by(name=default_category).first()
    if not category:
        category = AccessRightCategory(name=default_category)
        db.session.add(category)
        db.session.commit()
    admin_role_name = 'base.admin'
    admin_role: Optional[AccessRight] = AccessRight.query.filter_by(name=admin_role_name).first()
    if not admin_role:
        admin_role = AccessRight(name=admin_role_name, category_id=category.id)
        db.session.add(admin_role)
        db.session.commit()
    public_role_name = 'base.public'
    public_role: Optional[AccessRight] = AccessRight.query.filter_by(name=public_role_name).first()
    if not public_role:
        public_role = AccessRight(name=public_role_name, category_id=category.id)
        db.session.add(public_role)
        db.session.commit()
    admin: Optional[User] = User.query.filter_by(id=SUPER_USER_ID).first()
    if not admin:
        hashed_password = generate_secret_string('admin')
        admin = User(username='admin', password=hashed_password, role='user', single_session_mode=True)
        admin.access_rights.append(admin_role)
        db.session.add(admin)
        db.session.commit()
    public: Optional[User] = User.query.filter_by(id=PUBLIC_USER_ID).first()
    if not public:
        hashed_password = generate_secret_string('public')
        public = User(username='public', password=hashed_password, role='public')
        public.access_rights.append(public_role)
        db.session.add(public)
        db.session.commit()
