from django.http import HttpRequest, HttpResponse
from statsd.defaults.django import statsd


class ViewStatsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):

        timer = statsd.timer(stat=None)
        timer.start()
        response: HttpResponse = self.get_response(request)
        timer.stop(send=False)
        # resolver_match is only populated after get_response
        view_name = request.resolver_match.view_name
        timer.stat = f"view-timing.{view_name}.{request.method}"
        timer.send()

        statsd.incr(f"view-frequency.{view_name}.{request.method}")
        statsd.incr(f"view-status.{view_name}.{request.method}.{response.status_code}")

        return response
