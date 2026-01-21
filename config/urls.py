
from django.contrib import admin
from django.urls import path, include
from core_app.views import custom_404_view


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('cnc_work_app.urls')),
    path('', include("accounts_app.urls")),
    path('',include("core_app.urls")),
    path('',include("inv_app.urls")),
    path('',include("todo_app.urls")),
    path('',include("design_app.urls")),
    path('',include("machine_app.urls")),
    path('',include("order_costing_app.urls")),
    path('',include("user_log_app.urls")),
]

# 🔥 Custom 404 handler
handler404 = custom_404_view