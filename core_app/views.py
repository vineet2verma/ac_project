from django.shortcuts import render
from accounts_app.views import mongo_login_required, mongo_role_required

@mongo_login_required
@mongo_role_required(["ADMIN", "MANAGER"])
def dashboard(request):
    return render(request, "core_app/dashboard.html")


