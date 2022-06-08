from django.conf import settings

from aws_requests_auth.aws_auth import AWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection
from elasticsearch_dsl import connections


def _elasticsearch_connect():
    """
    Connect to configured Elasticsearch domain.

    :return: An Elasticsearch connection object.
    """
    auth = AWSRequestsAuth(
        aws_access_key=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_host=settings.ELASTICSEARCH_URL,
        aws_region=settings.ELASTICSEARCH_AWS_REGION,
        aws_service="es",
    )
    auth.encode = lambda x: bytes(x.encode("utf-8"))
    _es = Elasticsearch(
        host=settings.ELASTICSEARCH_URL,
        port=settings.ELASTICSEARCH_PORT,
        connection_class=RequestsHttpConnection,
        timeout=10,
        max_retries=1,
        retry_on_timeout=True,
        http_auth=auth,
        wait_for_status="yellow",
    )
    _es.info()
    return _es


es = _elasticsearch_connect()
connections.add_connection("default", es)
