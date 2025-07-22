from flask import abort
from flask_login import current_user
from functools import wraps

def require_abonnement(theme):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            abonnements = [ab.theme for ab in current_user.abonnements]
            if theme not in abonnements:
                abort(403)
            return func(*args, **kwargs)
        return wrapper
    return decorator
