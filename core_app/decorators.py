from django.shortcuts import redirect
from functools import wraps

def login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.session.get("uid"):
            return redirect("accounts_app:login")
        return view(request, *args, **kwargs)
    return wrapper

def role_required(roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.session.get("role") not in roles:
                return redirect("core_app:dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
