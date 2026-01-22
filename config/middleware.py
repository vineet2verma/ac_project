class GlobalCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.COOKIES.get("site_visited"):
            response.set_cookie("site_visited", "yes", max_age=86400)

        return response
