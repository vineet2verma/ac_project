import requests
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from datetime import timezone as dt_timezone
from utils.mongo import get_login_activity_collection




def get_area(lat, lng):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lng,
        "format": "json"
    }
    res = requests.get(url, params=params).json()
    return res.get("address", {})

def get_location(ip):
    response = requests.get(f"https://ipapi.co/{ip}/json/")
    data = response.json()
    return {
        "city": data.get("city"),
        "region": data.get("region"),
        "country": data.get("country_name"),
        "org": data.get("org"),
    }


def make_aware(dt):
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, dt_timezone.utc)
    return dt

def login_activity_view(request):
    login_col = get_login_activity_collection()

    # ----------------------------
    # GET PARAMETERS
    # ----------------------------
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "")   # active / logged_out
    page_number = request.GET.get("page", 1)

    # ----------------------------
    # BUILD MONGO QUERY
    # ----------------------------
    query = {}

    if search:
        query["$or"] = [
            {"username": {"$regex": search, "$options": "i"}},
            {"ip_address": {"$regex": search, "$options": "i"}},
        ]

    if status == "active":
        query["logout_time"] = None
    elif status == "logged_out":
        query["logout_time"] = {"$ne": None}

    # ----------------------------
    # FETCH DATA
    # ----------------------------
    activities = list(
        login_col.find(query).sort("login_time", -1)
    )

    # ----------------------------
    # FORMAT DATA
    # ----------------------------
    for act in activities:
        login_time = act.get("login_time")
        logout_time = act.get("logout_time")

        if login_time:
            login_time = make_aware(login_time)
            act["login_time_fmt"] = timezone.localtime(
                login_time
            ).strftime("%d-%b-%Y %I:%M %p")

        if logout_time:
            logout_time = make_aware(logout_time)
            act["logout_time_fmt"] = timezone.localtime(
                logout_time
            ).strftime("%d-%b-%Y %I:%M %p")

            duration = logout_time - login_time
            act["session_minutes"] = round(duration.total_seconds() / 60, 2)
        else:
            act["logout_time_fmt"] = "Active"
            act["session_minutes"] = "—"

    # ----------------------------
    # PAGINATION
    # ----------------------------
    # paginator = Paginator(activities, 10)  # 10 records per page
    page_size = int(request.GET.get("page_size", 10))

    paginator = Paginator(activities, page_size)

    page_obj = paginator.get_page(page_number)


    return render(
        request,
        "user_log_app/login_activity.html",
        {
            "activities": page_obj,
            "search": search,
            "status": status,
            "page_obj": page_obj,
            "page_size": page_size,
        }
    )