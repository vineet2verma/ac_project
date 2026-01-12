from django.shortcuts import render
from django.utils import timezone
from datetime import timezone as dt_timezone
from cnc_work_app.mongo import get_login_activity_collection


def make_aware(dt):
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, dt_timezone.utc)
    return dt


def login_activity_view(request):
    login_col = get_login_activity_collection()
    activities = list(login_col.find().sort("login_time", -1))

    for act in activities:
        login_time = make_aware(act.get("login_time"))
        if login_time:
            act["login_time_fmt"] = timezone.localtime(
                login_time
            ).strftime("%d-%b-%Y %I:%M %p")

        logout_time = make_aware(act.get("logout_time"))
        if logout_time:
            act["logout_time_fmt"] = timezone.localtime(
                logout_time
            ).strftime("%d-%b-%Y %I:%M %p")

            duration = logout_time - login_time
            act["session_minutes"] = round(duration.total_seconds() / 60, 2)
        else:
            act["logout_time_fmt"] = "Active"
            act["session_minutes"] = "—"

    return render(request, "user_log_app/login_activity.html", {
        "activities": activities
    })
