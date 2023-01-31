from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class ElasticsearchHealthcheckException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class HealthCheck(APIView):
    """
    Return a "200 OK" response if the server is running normally, 503 otherwise.

    This endpoint is used in production to ensure that the server should receive
    traffic. If no response is provided, the server is deregistered from the
    load balancer and destroyed.
    """

    swagger_schema = None

    @staticmethod
    def _check_db() -> None:
        """
        Check that the database is available.
        Returns nothing if everything is OK, throws error otherwise.
        """
        connection.ensure_connection()

    @staticmethod
    def _check_es() -> None:
        """
        Checks Elasticsearch cluster health. Raises an exception if ES is not healthy.
        """
        es_health = settings.ES.cluster.health(timeout="5s")

        if es_health["timed_out"]:
            raise ElasticsearchHealthcheckException("es_timed_out")

        if (status := es_health["status"]) != "green":
            raise ElasticsearchHealthcheckException(f"es_status_{status}")

    def get(self, request: Request):
        if "check_es" in request.query_params:
            self._check_es()
        self._check_db()

        return Response({"status": "200 OK"}, status=200)
