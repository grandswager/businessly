from flask import session, abort
from services.DatabaseService import db

def get_current_user():
    if "user_id" in session:
        return db.get_user_by_id(session["user_id"])
    return None

def require_business_user():
    user = get_current_user()
    if not user or user["role"] != "business":
        return abort(403)
    return user
