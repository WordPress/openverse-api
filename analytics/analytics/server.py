import logging
import sys
from uuid import UUID

import falcon
from falcon_cors import CORS

from analytics import settings
from analytics.event_controller import EventController
from analytics.models import DetailPageEvents


class HealthResource:
    @staticmethod
    def on_get(_, resp):
        resp.media = {"status": "200 OK"}
        resp.status = falcon.HTTP_200


class RedocResource:
    @staticmethod
    def on_get(_, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = "text/html"
        with open("docs/redoc.html", "r") as f:
            resp.text = f.read()


class OpenAPISpecResource:
    @staticmethod
    def on_get(req, resp):
        resp.status = falcon.HTTP_200
        resp.content_type = (
            "application/vnd.yml" if "download" in req.query_string else "text/vnd.yml"
        )
        with open("docs/swagger.yaml", "r") as f:
            resp.text = f.read()


class BaseEventResource:
    """Base class for all resource that need access to an event controller"""

    @staticmethod
    def _validate_uuid(field, uuid):
        try:
            return UUID(uuid, version=4).hex
        except ValueError:
            raise falcon.HTTPBadRequest(description=f"{field} must be a v4 UUID")

    def __init__(self, event_controller: EventController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_controller = event_controller


class SearchEventResource(BaseEventResource):
    def on_post(self, req, resp):
        j = req.media
        session_uuid = self._validate_uuid("Session", j["session_uuid"])

        try:
            self.event_controller.create_search(
                query=j["query"],
                session_uuid=session_uuid,
            )
            resp.media = {"status": "201 Created"}
            resp.status = falcon.HTTP_201
        except Exception:
            raise falcon.HTTPBadRequest()


class SearchRatingEventResource(BaseEventResource):
    def on_post(self, req, resp):
        j = req.media
        if not type(relevant := j["relevant"]) == bool:
            raise falcon.HTTPBadRequest(description="Rating must be `true` or `false`")

        try:
            self.event_controller.create_search_rating(
                query=j["query"], relevant=relevant
            )
            resp.media = {"status": "201 Created"}
            resp.status = falcon.HTTP_201
        except Exception:
            raise falcon.HTTPBadRequest()


class ResultClickEventResource(BaseEventResource):
    def on_post(self, req, resp):
        j = req.media
        session_uuid = self._validate_uuid("Session", j["session_uuid"])
        result_uuid = self._validate_uuid("Result", j["result_uuid"])
        if not type(rank := j["result_rank"]) == int:
            raise falcon.HTTPBadRequest(description="Result rank must be an integer")

        try:
            self.event_controller.create_result_click(
                query=j["query"],
                session_uuid=session_uuid,
                result_uuid=result_uuid,
                rank=rank,
            )
            resp.media = {"status": "201 Created"}
            resp.status = falcon.HTTP_201
        except Exception:
            raise falcon.HTTPBadRequest()


class DetailEventResource(BaseEventResource):
    def on_post(self, req, resp):
        j = req.media
        result_uuid = self._validate_uuid("Result", j["result_uuid"])
        if not hasattr(DetailPageEvents, event := j["event_type"]):
            items = ", ".join([f"'{item.name}'" for item in DetailPageEvents])
            raise falcon.HTTPBadRequest(
                description=f"Event type must be one of {items}"
            )

        try:
            self.event_controller.create_detail_event(
                event=event,
                result_uuid=result_uuid,
            )
            resp.media = {"status": "201 Created"}
            resp.status = falcon.HTTP_201
        except Exception:
            raise falcon.HTTPBadRequest()


def create_api(log=True):
    """Create an instance of the Falcon API server."""

    if log:
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(filename)s:%(lineno)d - %(message)s"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    cors = CORS(
        allow_origins_list=settings.ORIGINS,
        allow_all_methods=True,
        allow_all_headers=True,
    )
    _api = falcon.App(middleware=[cors.middleware])

    event_controller = EventController()

    _api.add_route("/", HealthResource())
    _api.add_route("/doc", RedocResource())
    _api.add_route("/swagger.yaml", OpenAPISpecResource())
    _api.add_route("/search_event", SearchEventResource(event_controller))
    _api.add_route("/search_rating_event", SearchRatingEventResource(event_controller))
    _api.add_route("/result_click_event", ResultClickEventResource(event_controller))
    _api.add_route("/detail_page_event", DetailEventResource(event_controller))

    return _api


api = create_api()
