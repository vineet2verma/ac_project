from datetime import timedelta

def set_cookie(response, key, value, days=7):
    response.set_cookie(
        key=key,
        value=value,
        max_age=days * 24 * 60 * 60,
        httponly=True,
        secure=False,  # True in production (HTTPS)
        samesite='Lax'
    )
    return response


def delete_cookie(response, key):
    response.delete_cookie(key)
    return response
