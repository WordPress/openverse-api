import datetime as dt
import logging

from oauth2_provider.models import AccessToken

from catalog.api import models


parent_logger = logging.getLogger(__name__)


def _valid(application: models.ThrottledApplication, token: AccessToken) -> bool:
    return application.rate_limit_model == "exempt" or token.expires >= dt.datetime.now(
        token.expires.tzinfo
    )


def get_token_info(token: str):
    """
    Recover an OAuth2 application client ID and rate limit model from an access
    token.

    :param token: An OAuth2 access token.
    :return: If the token is valid, return the client ID associated with the
    token, rate limit model, and email verification status as a tuple; else
    return (None, None, None).
    """
    logger = parent_logger.getChild("get_token_info")
    try:
        token = AccessToken.objects.get(token=token)
    except AccessToken.DoesNotExist:
        return None, None, None

    try:
        application = models.ThrottledApplication.objects.get(accesstoken=token)
    except models.ThrottledApplication.DoesNotExist:
        logger.warning("Failed to find application associated with access token.")

    if not _valid(application, token):
        logger.info(
            "rejected expired access token "
            f"application.name={application.name} "
            f"application.client_id={application.client_id} "
        )
        return None, None, None

    client_id = str(application.client_id)
    rate_limit_model = application.rate_limit_model
    verified = application.verified
    return client_id, rate_limit_model, verified
