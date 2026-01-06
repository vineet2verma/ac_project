
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cnc_work_app.urls')),
    path('', include("accounts_app.urls")),
    path('',include("core_app.urls")),
    path('',include("inv_app.urls")),
    path('',include("todo_app.urls")),
    path('',include("design_app.urls")),
    path('',include("machine_app.urls")),



]
