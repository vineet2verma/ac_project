# utils/permissions.py

ROLE_PERMISSIONS = {
    "ADMIN": {
        "sales": True,
        "designer": True,
        "inventory": True,
        "production": True,
        "qc": True,
        "dispatch": True,
        "override": True,
    },
    "DESIGNER": {
        "designer": True,
    },
    "INVENTORY": {
        "inventory": True,
    },
    "SALES": {
        "sales": True,
    },
    "PRODUCTION": {
        "production": True,
    },
    "DISPATCH": {
        "dispatch": True,
        "qc": True,
    },
}

def get_user_permissions(request):
    roles = request.session.get("mongo_roles", [])
    roles = [r.upper() for r in roles]

    permissions = {
        "sales": False,
        "designer": False,
        "production": False,
        "inventory": False,
        "qc": False,
        "dispatch": False,
        "override": False,
    }

    for role in roles:
        role_perms = ROLE_PERMISSIONS.get(role, {})
        for perm, allowed in role_perms.items():
            if allowed:
                permissions[perm] = True

    return permissions